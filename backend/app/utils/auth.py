"""JWT helpers, RBAC decorators, rate limiter, and token revocation.

All reusable auth primitives live here so routes stay thin.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps

from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import generate_password_hash

from app.utils.errors import api_error

# ---------------------------------------------------------------------------
# Timing-safe dummy hash for nonexistent-user login path
# ---------------------------------------------------------------------------

# Generated once at module load so the route pays no per-request cost.
# Using pbkdf2:sha256 keeps this aligned with the app's supported hash policy.
# If the app ever migrates to a different algorithm, update this line and the
# associated test so the dummy hash stays policy-consistent.
_DUMMY_HASH: str = generate_password_hash("dummy-placeholder", method="pbkdf2:sha256")


def get_dummy_hash() -> str:
    """Return a valid password hash for timing-safe nonexistent-user login checks."""
    return _DUMMY_HASH

# ---------------------------------------------------------------------------
# Persisted token revocation
# ---------------------------------------------------------------------------

def add_to_blocklist(
    jti: str,
    *,
    token_type: str,
    user_id: int | None = None,
    expires_at: datetime | None = None,
) -> None:
    """Persist a revoked JWT ID so logout survives process restarts."""
    from app.extensions import db  # noqa: PLC0415
    from app.models.revoked_token import RevokedToken  # noqa: PLC0415

    existing = db.session.query(RevokedToken.id).filter_by(jti=jti).first()
    if existing is not None:
        return

    db.session.add(
        RevokedToken(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
        )
    )


def token_expiry_from_jwt(jwt_payload: dict) -> datetime | None:
    """Convert a JWT ``exp`` claim into a UTC datetime when available."""
    exp = jwt_payload.get("exp")
    if exp is None:
        return None

    try:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except (OSError, OverflowError, TypeError, ValueError):
        return None


def is_token_revoked(_jwt_header: dict, jwt_payload: dict) -> bool:
    """Return True if the token's JTI has been revoked."""
    jti = jwt_payload.get("jti")
    if not jti:
        return False

    from app.extensions import db  # noqa: PLC0415
    from app.models.revoked_token import RevokedToken  # noqa: PLC0415

    return (
        db.session.query(RevokedToken.id)
        .filter_by(jti=jti)
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# DB-backed sliding-window rate limiter
# ---------------------------------------------------------------------------

# Per-IP throttle — same limit as the previous in-memory design so existing
# product behaviour and test contracts are preserved.
_IP_MAX_REQUESTS: int = 10
_IP_WINDOW_SECONDS: int = 60

# Per-account throttle — wider window to catch distributed/IP-rotating attacks
# that target a single username from many source addresses.
_USERNAME_MAX_REQUESTS: int = 10
_USERNAME_WINDOW_SECONDS: int = 300  # 5-minute window


def check_rate_limit(
    bucket_key: str,
    max_requests: int = _IP_MAX_REQUESTS,
    window_seconds: int = _IP_WINDOW_SECONDS,
) -> bool:
    """DB-backed sliding-window rate limiter.

    Returns True if the request should be allowed, False if rate-limited.
    Uses the shared database as backing store so throttle state survives
    process restarts and is consistent across multiple worker processes.

    Fails open (returns True) if the database is temporarily unavailable so
    that a DB issue does not take down the login endpoint entirely.

    Call once per throttle bucket per login attempt:
    - IP bucket:       ``check_rate_limit("ip:" + ip)``
    - Account bucket:  ``check_rate_limit("user:" + username.lower(),
                           _USERNAME_MAX_REQUESTS, _USERNAME_WINDOW_SECONDS)``
    """
    from app.extensions import db  # noqa: PLC0415
    from app.models.login_attempt import LoginAttempt  # noqa: PLC0415

    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(seconds=window_seconds)

    try:
        # Prune stale entries for this bucket to prevent unbounded table growth.
        db.session.query(LoginAttempt).filter(
            LoginAttempt.bucket_key == bucket_key,
            LoginAttempt.attempted_at < window_start,
        ).delete(synchronize_session=False)

        count = (
            db.session.query(LoginAttempt)
            .filter(
                LoginAttempt.bucket_key == bucket_key,
                LoginAttempt.attempted_at >= window_start,
            )
            .count()
        )

        if count >= max_requests:
            db.session.commit()  # Persist the pruned deletes.
            return False

        db.session.add(LoginAttempt(bucket_key=bucket_key, attempted_at=now))
        db.session.commit()
        return True
    except Exception:  # pragma: no cover — DB failure path
        try:
            db.session.rollback()
        except Exception:
            pass
        # Fail open: a transient DB error must not block legitimate logins.
        return True


# ---------------------------------------------------------------------------
# RBAC decorators
# ---------------------------------------------------------------------------


def _build_role_wrapper(fn, allowed_roles: frozenset[str]):
    """Shared wrapper logic for require_role / require_any_role."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # verify_jwt_in_request() raises on missing/invalid token;
        # Flask-JWT-Extended's registered error handlers produce the
        # standard error shape for those cases.
        verify_jwt_in_request()

        user_id = get_jwt_identity()

        # Deferred import to avoid circular dependency at module load time.
        from app.extensions import db  # noqa: PLC0415
        from app.models.user import User  # noqa: PLC0415

        user = db.session.get(User, int(user_id))

        if not user or not user.is_active:
            return api_error(
                "UNAUTHORIZED",
                "User not found or account is inactive.",
                401,
            )

        if user.role.value not in allowed_roles:
            return api_error(
                "FORBIDDEN",
                f"Role '{user.role.value}' is not permitted for this endpoint.",
                403,
            )

        return fn(*args, **kwargs)

    return wrapper


def require_role(*roles: str):
    """Decorator: require a valid JWT **and** one of the listed roles.

    Usage::

        @require_role("ADMIN")
        def admin_view(): ...

        @require_role("ADMIN", "MANAGER")
        def multi_role_view(): ...
    """
    allowed = frozenset(roles)

    def decorator(fn):
        return _build_role_wrapper(fn, allowed)

    return decorator


def require_any_role(*roles: str):
    """Alias for :func:`require_role` with a more expressive name."""
    return require_role(*roles)


# ---------------------------------------------------------------------------
# Current-user helpers
# ---------------------------------------------------------------------------


def get_current_user():
    """Return the :class:`~app.models.user.User` for the active JWT.

    Must be called inside a request context where a valid JWT is present
    (i.e., after ``@jwt_required()`` or ``verify_jwt_in_request()`` has run).
    """
    from app.models.user import User  # noqa: PLC0415

    from app.extensions import db  # noqa: PLC0415

    return db.session.get(User, int(get_jwt_identity()))
