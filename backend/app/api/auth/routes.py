"""Authentication routes.

Provides:
  POST /api/v1/auth/login       — exchange credentials for JWT pair
  POST /api/v1/auth/refresh     — exchange refresh token for new access token
  POST /api/v1/auth/logout      — revoke current token (persisted server-side registry)
  GET  /api/v1/auth/me          — current user info (any authenticated role)
  GET  /api/v1/auth/admin-only  — admin-only probe (401 / 403 test coverage)
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from app.extensions import db, jwt
from app.models.enums import UserRole
from app.models.user import User
from app.utils.auth import (
    _USERNAME_MAX_REQUESTS,
    _USERNAME_WINDOW_SECONDS,
    add_to_blocklist,
    check_rate_limit,
    get_current_user,
    get_dummy_hash,
    is_token_revoked,
    require_role,
    token_expiry_from_jwt,
)
from app.utils.errors import api_error as _error

auth_bp = Blueprint("auth", __name__)

_ACCESS_EXPIRES = timedelta(minutes=15)
_REFRESH_EXPIRES_OPERATOR = timedelta(days=30)
_REFRESH_EXPIRES_DEFAULT = timedelta(hours=8)
_PASSWORD_CHANGED_AT_CLAIM = "pwd_changed_at"


def _normalize_utc(dt: datetime | None) -> datetime | None:
    """Return a UTC-aware datetime for mixed SQLite/PostgreSQL values."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _serialize_password_changed_at(dt: datetime | None) -> str | None:
    """Serialize password_changed_at deterministically for JWT refresh claims."""
    normalized = _normalize_utc(dt)
    if normalized is None:
        return None
    return normalized.isoformat(timespec="microseconds")


# ---------------------------------------------------------------------------
# JWT error handlers — enforce standard error shape for all auth failures
# ---------------------------------------------------------------------------


@jwt.expired_token_loader
def _expired_token_handler(jwt_header, jwt_payload):
    return _error("TOKEN_EXPIRED", "Token has expired.", 401)


@jwt.invalid_token_loader
def _invalid_token_handler(error_string):
    return _error("TOKEN_INVALID", "Token signature or format is invalid.", 401)


@jwt.unauthorized_loader
def _missing_token_handler(error_string):
    return _error("TOKEN_MISSING", "Authorization token is required.", 401)


@jwt.revoked_token_loader
def _revoked_token_handler(jwt_header, jwt_payload):
    return _error("TOKEN_REVOKED", "Token has been revoked.", 401)


@jwt.token_in_blocklist_loader
def _blocklist_check(jwt_header, jwt_payload):
    return is_token_revoked(jwt_header, jwt_payload)


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["POST"])
def login():
    """Exchange username + password for an access / refresh token pair.

    Rate limited per source IP (10 req / 60 s) and per normalised username
    (10 req / 300 s) so distributed brute-force attacks that rotate IPs but
    target a single account are also throttled.
    Inactive users are rejected with 401 after password verification
    to avoid leaking account existence via timing.
    """
    ip = request.remote_addr or "unknown"

    # Parse body before rate-limit checks so both IP and username buckets
    # can be evaluated in a single pass without re-reading the body.
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    # Per-IP throttle — always enforced.
    if not check_rate_limit("ip:" + ip):
        return _error(
            "RATE_LIMITED",
            "Too many login attempts. Please wait a moment before trying again.",
            429,
        )

    # Per-account throttle — enforced when a username is present.
    if username and not check_rate_limit(
        "user:" + username.lower(),
        _USERNAME_MAX_REQUESTS,
        _USERNAME_WINDOW_SECONDS,
    ):
        return _error(
            "RATE_LIMITED",
            "Too many login attempts. Please wait a moment before trying again.",
            429,
        )

    if not username or not password:
        return _error("MISSING_CREDENTIALS", "username and password are required.", 400)

    user = User.query.filter_by(username=username).first()

    # Always run check_password_hash even when user is None to mitigate
    # timing-based username enumeration.
    candidate_hash = user.password_hash if user is not None else get_dummy_hash()
    password_valid = check_password_hash(candidate_hash, password)

    if user is None or not password_valid:
        return _error("INVALID_CREDENTIALS", "Invalid username or password.", 401)

    if not user.is_active:
        return _error("ACCOUNT_INACTIVE", "Account is inactive.", 401)

    identity = str(user.id)
    extra = {"role": user.role.value, "username": user.username}

    access_token = create_access_token(
        identity=identity,
        additional_claims=extra,
        expires_delta=_ACCESS_EXPIRES,
    )

    refresh_delta = (
        _REFRESH_EXPIRES_OPERATOR
        if user.role == UserRole.OPERATOR
        else _REFRESH_EXPIRES_DEFAULT
    )
    refresh_claims = {
        **extra,
        _PASSWORD_CHANGED_AT_CLAIM: _serialize_password_changed_at(user.password_changed_at),
    }

    refresh_token = create_refresh_token(
        identity=identity,
        additional_claims=refresh_claims,
        expires_delta=refresh_delta,
    )

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value,
                },
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Exchange a valid refresh token for a new access token.

    Re-verifies the user record from the database on every call so that:
    - deactivated users cannot keep minting access tokens
    - the new access token always reflects the current role and username
    - refresh tokens issued before the user's last password change are
      rejected, ensuring that a credential reset terminates old sessions

    Refresh tokens still carry the standard JWT ``iat`` (issued-at) claim,
    and they also snapshot the user's current ``password_changed_at`` value.
    That repo-level snapshot closes the same-second gap that ``iat`` alone
    cannot distinguish. Legacy users whose ``password_changed_at`` is NULL
    are not affected by this check.
    """
    identity = get_jwt_identity()

    user = db.session.get(User, int(identity))
    if not user or not user.is_active:
        return _error("UNAUTHORIZED", "User not found or account is inactive.", 401)

    # Reject sessions that predate a password change/reset.
    # Flask-JWT-Extended still carries the standard second-granularity iat
    # claim on every refresh token, but the repo also snapshots the user's
    # password_changed_at value into the refresh token so tokens minted
    # before a same-second password change are still rejected deterministically.
    if user.password_changed_at is not None:
        claims = get_jwt()
        current_password_changed_at = _serialize_password_changed_at(user.password_changed_at)
        token_password_changed_at = claims.get(_PASSWORD_CHANGED_AT_CLAIM)
        if token_password_changed_at != current_password_changed_at:
            return _error(
                "PASSWORD_CHANGED",
                "Credentials have changed. Please log in again.",
                401,
            )

    extra = {"role": user.role.value, "username": user.username}

    access_token = create_access_token(
        identity=identity,
        additional_claims=extra,
        expires_delta=_ACCESS_EXPIRES,
    )

    return jsonify({"access_token": access_token}), 200


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(refresh=True)
def logout():
    """Revoke the refresh token via the persisted revocation registry.

    Requires the refresh token in the Authorization header.  The short-lived
    access token (15 min) is not explicitly revoked here — the client should
    discard it locally. Revoking the refresh token prevents any further token
    refreshes for this session.
    """
    claims = get_jwt()
    identity = get_jwt_identity()
    try:
        add_to_blocklist(
            claims["jti"],
            token_type=claims.get("type", "refresh"),
            user_id=int(identity) if identity is not None else None,
            expires_at=token_expiry_from_jwt(claims),
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    return jsonify({"message": "Successfully logged out."}), 200


# ---------------------------------------------------------------------------
# GET /me  — any authenticated user
# ---------------------------------------------------------------------------


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the current user's profile.

    Requires any valid access token. Returns 401 if no/invalid token.
    """
    user = get_current_user()
    if not user or not user.is_active:
        return _error("UNAUTHORIZED", "User not found or account is inactive.", 401)
    return (
        jsonify(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role.value,
                "is_active": user.is_active,
            }
        ),
        200,
    )


# ---------------------------------------------------------------------------
# GET /admin-only  — ADMIN role probe (403 test coverage)
# ---------------------------------------------------------------------------


@auth_bp.route("/admin-only", methods=["GET"])
@require_role("ADMIN")
def admin_only():
    """Admin-only endpoint. Returns 401 without token, 403 for wrong role."""
    return jsonify({"message": "Admin access confirmed."}), 200
