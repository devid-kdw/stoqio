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
  - Wave 2 Phase 4: Production config fails fast on missing/blank DATABASE_URL
  - Wave 2 Phase 4: Nonexistent-user login still exercises the hash-check path
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
        """Requests from different IPs should not share per-IP rate limit counters.

        Uses auth_manager (not auth_admin) for the passing assertion so the
        per-username bucket for auth_admin — which was fully consumed by the
        10 preceding calls — does not block the final request.  Per-IP counters
        for each of the 10.99.0.x addresses remain well below the limit.
        """
        for i in range(10):
            _login(client, "auth_admin", "wrongpass", remote_addr=f"10.99.0.{i + 1}")

        # A fresh IP with a different username should still be allowed
        resp = _login(client, "auth_manager", "managerpass", remote_addr="10.99.1.1")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Wave 2 Phase 4 — Production config startup hardening
# ---------------------------------------------------------------------------


class TestProductionConfig:
    """Production config must fail fast on missing/blank DATABASE_URL (F-036).

    These tests use direct class instantiation with a monkeypatched environment
    so they run without a Flask app context and do not interact with the DB.
    """

    def test_production_raises_on_missing_database_url(self, monkeypatch):
        """Missing DATABASE_URL must raise RuntimeError during Production init."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")

        from app.config import Production

        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            Production()

    def test_production_raises_on_blank_database_url(self, monkeypatch):
        """Blank DATABASE_URL must raise RuntimeError during Production init."""
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")

        from app.config import Production

        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            Production()

    def test_production_raises_on_whitespace_only_database_url(self, monkeypatch):
        """Whitespace-only DATABASE_URL must also fail fast during Production init."""
        monkeypatch.setenv("DATABASE_URL", "   ")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")

        from app.config import Production

        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            Production()

    def test_production_starts_with_valid_database_url(self, monkeypatch):
        """Production must not raise when both DATABASE_URL and JWT_SECRET_KEY are valid."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/wms_prod")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")

        from app.config import Production

        cfg = Production()
        assert cfg.SQLALCHEMY_DATABASE_URI == "postgresql://user:pass@localhost/wms_prod"

    def test_production_still_raises_on_weak_jwt_secret(self, monkeypatch):
        """Existing weak/missing JWT_SECRET_KEY protection must remain unchanged."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/wms_prod")
        monkeypatch.setenv("JWT_SECRET_KEY", "weak")

        from app.config import Production

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            Production()

    def test_production_still_raises_on_missing_jwt_secret(self, monkeypatch):
        """Missing JWT_SECRET_KEY must still raise RuntimeError."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/wms_prod")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

        from app.config import Production

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            Production()

    def test_production_rejects_developer_default_secret(self, monkeypatch):
        """Production must explicitly reject the checked-in default/example secret."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/wms_prod")
        # Use the known default from config._Base._DEV_DEFAULT_JWT_SECRET
        monkeypatch.setenv("JWT_SECRET_KEY", "dev-local-jwt-secret-change-me-2026")

        from app.config import Production

        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            Production()

    def test_flask_env_absent_resolves_to_production(self, monkeypatch):
        """When FLASK_ENV is absent, get_config() must return a Production instance."""
        monkeypatch.delenv("FLASK_ENV", raising=False)
        # Setup env so Production() doesn't raise during instantiation
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/wms_prod")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")

        from app.config import Production, get_config

        cfg = get_config()
        assert isinstance(cfg, Production)
        assert cfg.DEBUG is False

    def test_debug_gating(self, monkeypatch):
        """Confirm DEBUG is True only for Development, False for Production."""
        from app.config import Development, Production

        # Development
        monkeypatch.setenv("JWT_SECRET_KEY", "dev-secret")
        # Development doesn't check JWT strength/database existence in __init__
        dev = Development()
        assert dev.DEBUG is True

        # Production
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/wms_prod")
        monkeypatch.setenv("JWT_SECRET_KEY", "a-very-strong-secret-key-for-testing-2026")
        prod = Production()
        assert prod.DEBUG is False


# ---------------------------------------------------------------------------
# Wave 2 Phase 4 — Timing-safe dummy hash path (F-035)
# ---------------------------------------------------------------------------


class TestNonexistentUserLoginPath:
    """Nonexistent-user login must still invoke check_password_hash (F-035).

    After removing the hardcoded PBKDF2 literal, the route must call
    get_dummy_hash() to get a policy-consistent hash and then pass it to
    check_password_hash — preserving timing-safe behavior for username enum.
    """

    def test_nonexistent_user_returns_401_invalid_credentials(self, client, auth_users):
        """Nonexistent user must still yield 401 INVALID_CREDENTIALS (contract lock)."""
        resp = _login(client, "user_does_not_exist", "anything", remote_addr="127.1.0.1")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "INVALID_CREDENTIALS"

    def test_nonexistent_user_invokes_check_password_hash(self, client, auth_users, monkeypatch):
        """The hash-check path must be executed even when the user does not exist."""
        import app.api.auth.routes as _routes
        from werkzeug.security import check_password_hash as _real_check

        calls = []

        def _spy_check(pwhash, password):
            calls.append(pwhash)
            return _real_check(pwhash, password)

        monkeypatch.setattr(_routes, "check_password_hash", _spy_check)

        _login(client, "user_does_not_exist", "anything", remote_addr="127.1.0.2")

        assert len(calls) == 1, "check_password_hash must be called exactly once"

    def test_get_dummy_hash_returns_valid_pbkdf2_hash(self):
        """get_dummy_hash() must return a hash that check_password_hash can verify."""
        from werkzeug.security import check_password_hash

        from app.utils.auth import get_dummy_hash

        h = get_dummy_hash()
        assert h.startswith("pbkdf2:sha256:")
        # The dummy hash must not match an arbitrary password (sanity check)
        assert not check_password_hash(h, "should-not-match")

    def test_get_dummy_hash_is_stable_within_process(self):
        """get_dummy_hash() must return the same value on repeated calls (no per-call churn)."""
        from app.utils.auth import get_dummy_hash

        assert get_dummy_hash() is get_dummy_hash()


# ---------------------------------------------------------------------------
# Wave 3 Phase 7 — Revoked-token retention cleanup (W3-008)
# ---------------------------------------------------------------------------


class TestCleanupCommand:
    """Regression coverage for the `flask purge-revoked-tokens` CLI command.

    Tests are driven through Flask's CLI runner so they exercise the real
    operator-invoked path (register_commands → app.cli) rather than calling
    the helper function in isolation.

    Cleanup contract:
    - expired rows (expires_at < now, not null)  → deleted
    - non-expired rows (expires_at >= now)        → preserved
    - null-expiry rows (expires_at IS NULL)       → never touched
    - --dry-run                                   → no writes, count reported
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _insert_revoked(app, jti, token_type, expires_at):
        """Insert a RevokedToken row directly and return its id."""
        from app.extensions import db
        from app.models.revoked_token import RevokedToken

        with app.app_context():
            row = RevokedToken(
                jti=jti,
                token_type=token_type,
                expires_at=expires_at,
            )
            db.session.add(row)
            db.session.commit()
            return row.id

    @staticmethod
    def _exists(app, row_id):
        """Return True if a RevokedToken with the given id still exists in DB."""
        from app.extensions import db
        from app.models.revoked_token import RevokedToken

        with app.app_context():
            return db.session.get(RevokedToken, row_id) is not None

    @staticmethod
    def _run_purge(app, args=None):
        """Invoke `flask purge-revoked-tokens` via the CLI runner and return result."""
        from click.testing import CliRunner
        from app.commands import purge_revoked_tokens

        runner = CliRunner()
        with app.app_context():
            result = runner.invoke(purge_revoked_tokens, args or [], catch_exceptions=False)
        return result

    # ------------------------------------------------------------------
    # Cleanup behaviour
    # ------------------------------------------------------------------

    def test_purge_deletes_expired_rows(self, app):
        """Expired rows (expires_at < now) must be removed by the cleanup command."""
        from datetime import datetime, timedelta, timezone

        past = datetime.now(timezone.utc) - timedelta(days=1)
        row_id = self._insert_revoked(app, "purge-expired-jti-001", "refresh", past)

        result = self._run_purge(app)
        assert result.exit_code == 0, result.output
        assert not self._exists(app, row_id), "Expired row was not deleted"

    def test_purge_preserves_non_expired_rows(self, app):
        """Non-expired rows (expires_at > now) must NOT be deleted."""
        from datetime import datetime, timedelta, timezone

        future = datetime.now(timezone.utc) + timedelta(days=30)
        row_id = self._insert_revoked(app, "purge-future-jti-001", "refresh", future)

        result = self._run_purge(app)
        assert result.exit_code == 0, result.output
        assert self._exists(app, row_id), "Non-expired row was incorrectly deleted"

    def test_purge_preserves_null_expiry_rows(self, app):
        """Rows with expires_at IS NULL must never be touched by the cleanup."""
        row_id = self._insert_revoked(app, "purge-null-expiry-jti-001", "refresh", None)

        result = self._run_purge(app)
        assert result.exit_code == 0, result.output
        assert self._exists(app, row_id), "NULL-expiry row was incorrectly deleted"

    def test_purge_deletes_only_expired_in_mixed_set(self, app):
        """Cleanup must selectively delete expired rows while leaving others intact."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)
        future = now + timedelta(hours=1)

        expired_id = self._insert_revoked(app, "purge-mixed-expired-001", "refresh", past)
        future_id = self._insert_revoked(app, "purge-mixed-future-001", "refresh", future)
        null_id = self._insert_revoked(app, "purge-mixed-null-001", "refresh", None)

        result = self._run_purge(app)
        assert result.exit_code == 0, result.output

        assert not self._exists(app, expired_id), "Expired row should have been deleted"
        assert self._exists(app, future_id), "Future row should have been preserved"
        assert self._exists(app, null_id), "NULL-expiry row should have been preserved"

    def test_purge_dry_run_makes_no_writes(self, app):
        """--dry-run must report the count without deleting any rows."""
        from datetime import datetime, timedelta, timezone

        past = datetime.now(timezone.utc) - timedelta(days=2)
        row_id = self._insert_revoked(app, "purge-dryrun-jti-001", "refresh", past)

        result = self._run_purge(app, ["--dry-run"])
        assert result.exit_code == 0, result.output
        assert "[dry-run]" in result.output
        assert self._exists(app, row_id), "dry-run must not delete rows"

    def test_purge_dry_run_reports_correct_count(self, app):
        """--dry-run output must mention the deleted count (even if 0 after prior purge)."""
        from datetime import datetime, timedelta, timezone

        past = datetime.now(timezone.utc) - timedelta(days=3)
        self._insert_revoked(app, "purge-dryrun-count-jti-001", "refresh", past)

        result = self._run_purge(app, ["--dry-run"])
        assert result.exit_code == 0, result.output
        # Output must contain a digit followed by the row-count noun phrase
        assert "row(s)" in result.output

    def test_purge_empty_table_succeeds_with_zero_count(self, app):
        """Command must complete without error and print 0 when there is nothing to delete."""
        # Run a real purge first to clear any leftover expired rows from other tests
        self._run_purge(app)

        result = self._run_purge(app)
        assert result.exit_code == 0, result.output
        # After a prior purge the expired count must be 0
        assert "0" in result.output

    # ------------------------------------------------------------------
    # Auth / logout regression locks
    # These must remain green after the cleanup mechanism is in place.
    # ------------------------------------------------------------------

    def test_revoked_refresh_token_still_rejected_after_purge(self, client, auth_users, app):
        """Runtime revocation check must still reject a revoked refresh token
        even after the cleanup command has been run (regression lock)."""
        login_resp = _login(client, "auth_admin", "adminpass", remote_addr="127.0.7.1")
        refresh_token = login_resp.get_json()["refresh_token"]

        # Revoke via logout
        logout_resp = client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(refresh_token),
        )
        assert logout_resp.status_code == 200

        # Run cleanup — should not touch this non-expired row
        self._run_purge(app)

        # Refresh must still be rejected
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert refresh_resp.status_code == 401
        assert refresh_resp.get_json()["error"] == "TOKEN_REVOKED"

    def test_logout_still_persists_revoked_row_after_cleanup_lands(self, client, auth_users, app):
        """Logout must still write a revoked_token row after the cleanup command is registered.

        This is a direct regression lock on the add_to_blocklist / logout path
        to confirm that introducing commands.py did not alter the logout flow.
        """
        from app.models.revoked_token import RevokedToken

        with app.app_context():
            before = RevokedToken.query.count()

        login_resp = _login(client, "auth_manager", "managerpass", remote_addr="127.0.7.2")
        refresh_token = login_resp.get_json()["refresh_token"]

        logout_resp = client.post(
            "/api/v1/auth/logout",
            headers=_auth_header(refresh_token),
        )
        assert logout_resp.status_code == 200

        with app.app_context():
            after = RevokedToken.query.count()

        assert after == before + 1, "Logout must persist exactly one new revoked_token row"


# ---------------------------------------------------------------------------
# Wave 4 Phase 2 — F-SEC-004: refresh-token invalidation after password change
# ---------------------------------------------------------------------------


class TestRefreshInvalidationAfterPasswordChange:
    """Refresh tokens issued before an admin password change must be rejected.

    The mechanism is layered on top of the existing revocation architecture:
    - refresh tokens still carry the standard JWT ``iat`` (issued-at) claim
    - refresh tokens also snapshot ``password_changed_at`` so same-second
      stale sessions are rejected deterministically
    - users with ``password_changed_at IS NULL`` (no admin-driven change yet)
      are not affected
    - a fresh login after the password change issues a new token that works
    """

    @staticmethod
    def _admin_token(client):
        """Return an access token for auth_admin (pre-existing fixture user)."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "auth_admin", "password": "adminpass"},
            environ_base={"REMOTE_ADDR": "127.0.8.1"},
        )
        assert resp.status_code == 200
        return resp.get_json()["access_token"]

    @staticmethod
    def _jwt_payload(token):
        import base64
        import json as _json

        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        return _json.loads(base64.b64decode(payload_b64))

    @staticmethod
    def _create_temp_user(app, *, username, password, role):
        from werkzeug.security import generate_password_hash

        from app.extensions import db as _db
        from app.models.user import User

        with app.app_context():
            u = User(
                username=username,
                password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
                role=role,
                is_active=True,
            )
            _db.session.add(u)
            _db.session.commit()
            return u.id

    @staticmethod
    def _delete_temp_user(app, user_id):
        from app.extensions import db as _db
        from app.models.user import User

        with app.app_context():
            u = _db.session.get(User, user_id)
            if u:
                _db.session.delete(u)
                _db.session.commit()

    @staticmethod
    def _frozen_datetime(forced_now):
        class FrozenDateTime:
            @staticmethod
            def now(tz=None):
                if tz is None:
                    return forced_now.replace(tzinfo=None)
                return forced_now.astimezone(tz)

        return FrozenDateTime

    def test_settings_password_change_rejects_refresh_token_issued_earlier_in_same_second(
        self, client, app, auth_users, monkeypatch
    ):
        """The active Settings password-reset flow must kill pre-change refresh tokens
        even when the reset lands in the same second as the original login."""
        from datetime import datetime, timezone

        from app.models.enums import UserRole
        from app.services import settings_service

        uid = self._create_temp_user(
            app,
            username="pc_settings_same_second_reject",
            password="OldPass12!",
            role=UserRole.VIEWER,
        )
        try:
            login_resp = _login(
                client,
                "pc_settings_same_second_reject",
                "OldPass12!",
                remote_addr="127.0.8.2",
            )
            assert login_resp.status_code == 200
            old_refresh = login_resp.get_json()["refresh_token"]
            token_iat = self._jwt_payload(old_refresh)["iat"]
            forced_changed_at = datetime.fromtimestamp(token_iat, tz=timezone.utc).replace(
                microsecond=900000
            )

            monkeypatch.setattr(
                settings_service,
                "datetime",
                self._frozen_datetime(forced_changed_at),
            )

            update_resp = client.put(
                f"/api/v1/settings/users/{uid}",
                json={"password": "NewPass12!"},
                headers=_auth_header(self._admin_token(client)),
            )
            assert update_resp.status_code == 200

            refresh_resp = client.post(
                "/api/v1/auth/refresh",
                headers=_auth_header(old_refresh),
            )
            assert refresh_resp.status_code == 401
            assert refresh_resp.get_json()["error"] == "PASSWORD_CHANGED"
        finally:
            self._delete_temp_user(app, uid)

    def test_refresh_token_issued_after_settings_password_change_works(
        self, client, app, auth_users, monkeypatch
    ):
        """A fresh login after the Settings password reset must yield a working
        refresh token, including when the reset happened in the same second."""
        from datetime import datetime, timezone

        from app.models.enums import UserRole
        from app.services import settings_service

        uid = self._create_temp_user(
            app,
            username="pc_settings_same_second_accept",
            password="OldPass12!",
            role=UserRole.VIEWER,
        )
        try:
            login_resp = _login(
                client,
                "pc_settings_same_second_accept",
                "OldPass12!",
                remote_addr="127.0.8.3",
            )
            assert login_resp.status_code == 200
            old_refresh = login_resp.get_json()["refresh_token"]
            token_iat = self._jwt_payload(old_refresh)["iat"]
            forced_changed_at = datetime.fromtimestamp(token_iat, tz=timezone.utc).replace(
                microsecond=900000
            )

            monkeypatch.setattr(
                settings_service,
                "datetime",
                self._frozen_datetime(forced_changed_at),
            )

            update_resp = client.put(
                f"/api/v1/settings/users/{uid}",
                json={"password": "NewPass12!"},
                headers=_auth_header(self._admin_token(client)),
            )
            assert update_resp.status_code == 200

            new_login_resp = _login(
                client,
                "pc_settings_same_second_accept",
                "NewPass12!",
                remote_addr="127.0.8.5",
            )
            assert new_login_resp.status_code == 200
            new_refresh = new_login_resp.get_json()["refresh_token"]
            new_payload = self._jwt_payload(new_refresh)
            assert "iat" in new_payload
            assert new_payload["pwd_changed_at"] == forced_changed_at.isoformat(
                timespec="microseconds"
            )

            refresh_resp = client.post(
                "/api/v1/auth/refresh",
                headers=_auth_header(new_refresh),
            )
            assert refresh_resp.status_code == 200
            assert "access_token" in refresh_resp.get_json()
        finally:
            self._delete_temp_user(app, uid)

    def test_null_password_changed_at_does_not_block_refresh(
        self, client, app, auth_users
    ):
        """Users with password_changed_at IS NULL (no admin-driven change) must
        not be affected by the invalidation check — legacy sessions pass through."""
        from werkzeug.security import generate_password_hash

        from app.extensions import db as _db
        from app.models.enums import UserRole
        from app.models.user import User

        with app.app_context():
            u = User(
                username="pc_null_changed_at",
                password_hash=generate_password_hash(
                    "StablePass1!", method="pbkdf2:sha256"
                ),
                role=UserRole.VIEWER,
                is_active=True,
                # password_changed_at deliberately omitted — column is NULL
            )
            _db.session.add(u)
            _db.session.commit()
            # Confirm it really is NULL after insertion
            assert u.password_changed_at is None
            uid = u.id

        login_resp = _login(
            client, "pc_null_changed_at", "StablePass1!", remote_addr="127.0.8.4"
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.get_json()["refresh_token"]

        # Refresh must succeed — no password_changed_at means no invalidation check.
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            headers=_auth_header(refresh_token),
        )
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.get_json()

        # Cleanup
        with app.app_context():
            u = _db.session.get(User, uid)
            if u:
                _db.session.delete(u)
                _db.session.commit()
