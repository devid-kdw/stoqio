"""Authentication routes.

Provides:
  POST /api/v1/auth/login       — exchange credentials for JWT pair
  POST /api/v1/auth/refresh     — exchange refresh token for new access token
  POST /api/v1/auth/logout      — revoke current token (persisted server-side registry)
  GET  /api/v1/auth/me          — current user info (any authenticated role)
  GET  /api/v1/auth/admin-only  — admin-only probe (401 / 403 test coverage)
"""

from datetime import timedelta

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
    add_to_blocklist,
    check_rate_limit,
    get_current_user,
    is_token_revoked,
    require_role,
    token_expiry_from_jwt,
)

auth_bp = Blueprint("auth", __name__)

_ACCESS_EXPIRES = timedelta(minutes=15)
_REFRESH_EXPIRES_OPERATOR = timedelta(days=30)
_REFRESH_EXPIRES_DEFAULT = timedelta(hours=8)


# ---------------------------------------------------------------------------
# JWT error handlers — enforce standard error shape for all auth failures
# ---------------------------------------------------------------------------


@jwt.expired_token_loader
def _expired_token_handler(jwt_header, jwt_payload):
    return (
        jsonify(
            {
                "error": "TOKEN_EXPIRED",
                "message": "Token has expired.",
                "details": {},
            }
        ),
        401,
    )


@jwt.invalid_token_loader
def _invalid_token_handler(error_string):
    return (
        jsonify(
            {
                "error": "TOKEN_INVALID",
                "message": "Token signature or format is invalid.",
                "details": {},
            }
        ),
        401,
    )


@jwt.unauthorized_loader
def _missing_token_handler(error_string):
    return (
        jsonify(
            {
                "error": "TOKEN_MISSING",
                "message": "Authorization token is required.",
                "details": {},
            }
        ),
        401,
    )


@jwt.revoked_token_loader
def _revoked_token_handler(jwt_header, jwt_payload):
    return (
        jsonify(
            {
                "error": "TOKEN_REVOKED",
                "message": "Token has been revoked.",
                "details": {},
            }
        ),
        401,
    )


@jwt.token_in_blocklist_loader
def _blocklist_check(jwt_header, jwt_payload):
    return is_token_revoked(jwt_header, jwt_payload)


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["POST"])
def login():
    """Exchange username + password for an access / refresh token pair.

    Rate limited to 10 requests per minute per IP.
    Inactive users are rejected with 401 after password verification
    to avoid leaking account existence via timing.
    """
    ip = request.remote_addr or "unknown"
    if not check_rate_limit(ip):
        return (
            jsonify(
                {
                    "error": "RATE_LIMITED",
                    "message": (
                        "Too many login attempts. "
                        "Please wait a moment before trying again."
                    ),
                    "details": {},
                }
            ),
            429,
        )

    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return (
            jsonify(
                {
                    "error": "MISSING_CREDENTIALS",
                    "message": "username and password are required.",
                    "details": {},
                }
            ),
            400,
        )

    user = User.query.filter_by(username=username).first()

    # Always run check_password_hash even when user is None to mitigate
    # timing-based username enumeration.
    _dummy_hash = (
        "pbkdf2:sha256:600000$dummy$0000000000000000000000000000000000000000"
        "00000000000000000000"
    )
    candidate_hash = user.password_hash if user is not None else _dummy_hash
    password_valid = check_password_hash(candidate_hash, password)

    if user is None or not password_valid:
        return (
            jsonify(
                {
                    "error": "INVALID_CREDENTIALS",
                    "message": "Invalid username or password.",
                    "details": {},
                }
            ),
            401,
        )

    if not user.is_active:
        return (
            jsonify(
                {
                    "error": "ACCOUNT_INACTIVE",
                    "message": "Account is inactive.",
                    "details": {},
                }
            ),
            401,
        )

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
    refresh_token = create_refresh_token(
        identity=identity,
        additional_claims=extra,
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

    Re-verifies the user record from the database on every call so that
    deactivated users cannot keep minting access tokens, and so that the
    new access token always reflects the current role and username.
    """
    identity = get_jwt_identity()

    user = db.session.get(User, int(identity))
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
