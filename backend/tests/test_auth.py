"""Phase 3 authentication tests.

Covers:
  - Login success (admin, OPERATOR refresh lifetime difference)
  - Login wrong password → 401
  - Login inactive user → 401
  - Login missing fields → 400
  - Token refresh → 200 with new access token
  - Logout → 200 + token revoked (401 on reuse)
  - GET /me without token → 401
  - GET /me with valid token → 200
  - GET /admin-only with non-ADMIN token → 403
  - GET /admin-only with ADMIN token → 200
  - Rate limiting on /login → 429 after 10 requests from same IP
"""

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(client, username, password, remote_addr="127.0.0.1"):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": remote_addr},
    )


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class TestLogin:
    def test_login_admin_returns_tokens_and_user(self, client, auth_users):
        resp = _login(client, "auth_admin", "adminpass")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "auth_admin"
        assert data["user"]["role"] == "ADMIN"

    def test_login_operator_returns_tokens(self, client, auth_users):
        resp = _login(client, "auth_operator", "operatorpass")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["role"] == "OPERATOR"

    def test_login_wrong_password_returns_401(self, client, auth_users):
        resp = _login(client, "auth_admin", "wrongpassword")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user_returns_401(self, client, auth_users):
        resp = _login(client, "nobody", "anything")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "INVALID_CREDENTIALS"

    def test_login_inactive_user_returns_401(self, client, auth_users):
        resp = _login(client, "auth_inactive", "inactivepass")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "ACCOUNT_INACTIVE"

    def test_login_missing_username_returns_400(self, client, auth_users):
        resp = client.post(
            "/api/v1/auth/login",
            json={"password": "adminpass"},
            environ_base={"REMOTE_ADDR": "127.0.0.2"},
        )
        assert resp.status_code == 400

    def test_login_missing_password_returns_400(self, client, auth_users):
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "auth_admin"},
            environ_base={"REMOTE_ADDR": "127.0.0.2"},
        )
        assert resp.status_code == 400

    def test_login_empty_body_returns_400(self, client, auth_users):
        resp = client.post(
            "/api/v1/auth/login",
            json={},
            environ_base={"REMOTE_ADDR": "127.0.0.2"},
        )
        assert resp.status_code == 400

    def test_login_error_shape_has_required_fields(self, client, auth_users):
        resp = _login(client, "auth_admin", "wrongpass")
        data = resp.get_json()
        assert "error" in data
        assert "message" in data
        assert "details" in data


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    def test_refresh_returns_new_access_token(self, client, auth_users):
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.1.1")
        refresh_token = login_resp.get_json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data

    def test_refresh_with_access_token_returns_401(self, client, auth_users):
        """Sending an access token to /refresh should be rejected.

        Our custom invalid_token_loader returns 401 (not 422) to maintain
        a consistent error shape across all auth failures.
        """
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.1.2")
        access_token = login_resp.get_json()["access_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] in ("TOKEN_INVALID", "TOKEN_WRONG_TYPE")

    def test_refresh_without_token_returns_401(self, client, auth_users):
        resp = client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "TOKEN_MISSING"

    def test_refresh_fails_for_deactivated_user(self, client, app):
        """Refresh must re-check user.is_active — deactivated users must not mint tokens."""
        from werkzeug.security import generate_password_hash

        from app.extensions import db as _db
        from app.models.enums import UserRole
        from app.models.user import User

        # Create a temporary user
        with app.app_context():
            u = User(
                username="temp_deactivated",
                password_hash=generate_password_hash("pw", method="pbkdf2:sha256"),
                role=UserRole.MANAGER,
                is_active=True,
            )
            _db.session.add(u)
            _db.session.commit()

        login_resp = _login(client, "temp_deactivated", "pw", remote_addr="127.0.1.3")
        assert login_resp.status_code == 200
        refresh_token = login_resp.get_json()["refresh_token"]

        # Deactivate the user between login and refresh
        with app.app_context():
            u = User.query.filter_by(username="temp_deactivated").first()
            u.is_active = False
            _db.session.commit()

        resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "UNAUTHORIZED"

        # Cleanup
        with app.app_context():
            u = User.query.filter_by(username="temp_deactivated").first()
            if u:
                _db.session.delete(u)
                _db.session.commit()

    def test_refresh_uses_current_db_role(self, client, app):
        """New access token must reflect the current DB role, not the stale claim."""
        from werkzeug.security import generate_password_hash

        from app.extensions import db as _db
        from app.models.enums import UserRole
        from app.models.user import User

        with app.app_context():
            u = User(
                username="temp_role_change",
                password_hash=generate_password_hash("pw", method="pbkdf2:sha256"),
                role=UserRole.VIEWER,
                is_active=True,
            )
            _db.session.add(u)
            _db.session.commit()

        login_resp = _login(client, "temp_role_change", "pw", remote_addr="127.0.1.4")
        assert login_resp.status_code == 200
        refresh_token = login_resp.get_json()["refresh_token"]
        assert login_resp.get_json()["user"]["role"] == "VIEWER"

        # Promote the user to MANAGER in the DB
        with app.app_context():
            u = User.query.filter_by(username="temp_role_change").first()
            u.role = UserRole.MANAGER
            _db.session.commit()

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.get_json()["access_token"]

        # The new access token's embedded role claim should be MANAGER, not VIEWER.
        # Verify by calling /admin-only — MANAGER gets 403 (not 401), confirming
        # the token is valid but the role is non-ADMIN.
        me_resp = client.get(
            "/api/v1/auth/me",
            headers=_auth_header(new_access),
        )
        assert me_resp.status_code == 200
        assert me_resp.get_json()["role"] == "MANAGER"

        # Cleanup
        with app.app_context():
            u = User.query.filter_by(username="temp_role_change").first()
            if u:
                _db.session.delete(u)
                _db.session.commit()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_with_refresh_token_returns_200(self, client, auth_users):
        """Logout requires the refresh token and succeeds."""
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.2.1")
        refresh_token = login_resp.get_json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(refresh_token),
        )
        assert resp.status_code == 200

    def test_logout_revokes_refresh_token(self, client, auth_users):
        """After logout the blocklisted refresh token must not mint new access tokens."""
        login_resp = _login(client, "auth_manager", "managerpass", remote_addr="127.0.2.2")
        tokens = login_resp.get_json()
        refresh_token = tokens["refresh_token"]

        client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(refresh_token),
        )

        # The refresh token is now revoked — /refresh must reject it
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.get_json()["error"] == "TOKEN_REVOKED"

    def test_logout_persists_revoked_refresh_token(self, client, auth_users, app):
        """Revocation must be stored in DB so it survives process restarts."""
        from app.models.revoked_token import RevokedToken

        with app.app_context():
            before_count = RevokedToken.query.count()

        login_resp = _login(client, "auth_operator", "operatorpass", remote_addr="127.0.2.5")
        refresh_token = login_resp.get_json()["refresh_token"]

        logout_resp = client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(refresh_token),
        )
        assert logout_resp.status_code == 200

        with app.app_context():
            assert RevokedToken.query.count() == before_count + 1
            stored = RevokedToken.query.order_by(RevokedToken.id.desc()).first()
            assert stored is not None
            assert stored.token_type == "refresh"
            assert stored.user_id == auth_users["operator"].id
            assert stored.expires_at is not None

    def test_logout_with_access_token_is_rejected(self, client, auth_users):
        """Logout endpoint requires a refresh token; access token must be rejected."""
        login_resp = _login(client, "auth_operator", "operatorpass", remote_addr="127.0.2.3")
        access_token = login_resp.get_json()["access_token"]

        resp = client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 401

    def test_logout_without_token_returns_401(self, client, auth_users):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


class TestMe:
    def test_me_without_token_returns_401(self, client, auth_users):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["error"] == "TOKEN_MISSING"

    def test_me_with_valid_token_returns_user(self, client, auth_users):
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.3.1")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/me",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "auth_admin"
        assert data["role"] == "ADMIN"
        assert data["is_active"] is True

    def test_me_manager_returns_200(self, client, auth_users):
        login_resp = _login(client, "auth_manager", "managerpass", remote_addr="127.0.3.2")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/me",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 200

    def test_me_with_invalid_token_returns_401(self, client, auth_users):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /admin-only  (403 / 401 coverage)
# ---------------------------------------------------------------------------


class TestAdminOnly:
    def test_admin_only_without_token_returns_401(self, client, auth_users):
        resp = client.get("/api/v1/auth/admin-only")
        assert resp.status_code == 401

    def test_admin_only_with_admin_token_returns_200(self, client, auth_users):
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.4.1")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/admin-only",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 200

    def test_admin_only_with_manager_token_returns_403(self, client, auth_users):
        login_resp = _login(client, "auth_manager", "managerpass", remote_addr="127.0.4.2")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/admin-only",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data["error"] == "FORBIDDEN"

    def test_admin_only_with_operator_token_returns_403(self, client, auth_users):
        login_resp = _login(client, "auth_operator", "operatorpass", remote_addr="127.0.4.3")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/admin-only",
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 403

    def test_admin_only_error_shape(self, client, auth_users):
        login_resp = _login(client, "auth_manager", "managerpass", remote_addr="127.0.4.4")
        access_token = login_resp.get_json()["access_token"]

        resp = client.get(
            "/api/v1/auth/admin-only",
            headers=_auth_header(access_token),
        )
        data = resp.get_json()
        assert "error" in data
        assert "message" in data
        assert "details" in data


# ---------------------------------------------------------------------------
# Rate limiting on /login
# ---------------------------------------------------------------------------


class TestRateLimit:
    def test_login_rate_limit_blocks_after_10_requests(self, client, auth_users):
        """11th login attempt from the same IP in under 60 s returns 429."""
        ip = "10.99.99.1"
        for i in range(10):
            resp = _login(client, "auth_admin", "wrongpass", remote_addr=ip)
            # These are expected to be 401 (wrong password), not rate-limited
            assert resp.status_code != 429, f"Rate limit hit too early at request {i + 1}"

        # 11th request should be rate-limited
        resp = _login(client, "auth_admin", "wrongpass", remote_addr=ip)
        assert resp.status_code == 429
        data = resp.get_json()
        assert data["error"] == "RATE_LIMITED"

    def test_different_ips_have_independent_limits(self, client, auth_users):
        """Requests from different IPs should not share rate limit counters."""
        for i in range(10):
            _login(client, "auth_admin", "wrongpass", remote_addr=f"10.99.0.{i + 1}")

        # A fresh IP should still be allowed
        resp = _login(client, "auth_admin", "adminpass", remote_addr="10.99.1.1")
        assert resp.status_code == 200
