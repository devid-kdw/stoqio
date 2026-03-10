"""JWT helpers, RBAC decorators, rate limiter, and token blocklist.

All reusable auth primitives live here so routes stay thin.
"""

from collections import defaultdict, deque
from functools import wraps
from threading import Lock
from time import time

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

# ---------------------------------------------------------------------------
# In-memory token blocklist
# ---------------------------------------------------------------------------

_revoked_jtis: set[str] = set()


def add_to_blocklist(jti: str) -> None:
    """Add a JWT ID to the in-memory revocation set."""
    _revoked_jtis.add(jti)


def is_token_revoked(_jwt_header: dict, jwt_payload: dict) -> bool:
    """Return True if the token's JTI has been revoked."""
    return jwt_payload.get("jti", "") in _revoked_jtis


# ---------------------------------------------------------------------------
# Sliding-window rate limiter (no external dependency)
# ---------------------------------------------------------------------------

_rate_store: dict[str, deque] = defaultdict(deque)
_rate_lock = Lock()


def check_rate_limit(
    ip: str, max_requests: int = 10, window_seconds: int = 60
) -> bool:
    """Return True if the request should be allowed, False if rate-limited.

    Uses a sliding window: timestamps older than *window_seconds* are pruned
    on each call, then the current timestamp is appended.
    """
    now = time()
    with _rate_lock:
        timestamps = _rate_store[ip]
        # Prune entries outside the window
        while timestamps and timestamps[0] < now - window_seconds:
            timestamps.popleft()
        if len(timestamps) >= max_requests:
            return False
        timestamps.append(now)
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
            return (
                jsonify(
                    {
                        "error": "UNAUTHORIZED",
                        "message": "User not found or account is inactive.",
                        "details": {},
                    }
                ),
                401,
            )

        if user.role.value not in allowed_roles:
            return (
                jsonify(
                    {
                        "error": "FORBIDDEN",
                        "message": (
                            f"Role '{user.role.value}' is not permitted "
                            "for this endpoint."
                        ),
                        "details": {},
                    }
                ),
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
