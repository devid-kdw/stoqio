"""Wave 4 Phase 5 security hardening regression tests."""

from pathlib import Path

from app.models.login_attempt import LoginAttempt

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy.sh"
GITIGNORE = REPO_ROOT / ".gitignore"
REQUIREMENTS_LOCK = REPO_ROOT / "backend" / "requirements.lock"


def _login(client, username, password, remote_addr):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
        environ_base={"REMOTE_ADDR": remote_addr},
    )


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_throttles_same_username_across_different_ips(client, auth_users):
    """F-SEC-010: username/account throttle catches IP-rotating attempts."""
    for i in range(10):
        response = _login(
            client,
            "auth_admin",
            "wrongpass",
            remote_addr=f"10.45.0.{i + 1}",
        )
        assert response.status_code == 401

    response = _login(
        client,
        "auth_admin",
        "adminpass",
        remote_addr="10.45.1.1",
    )

    assert response.status_code == 429
    assert response.get_json()["error"] == "RATE_LIMITED"


def test_login_throttle_state_is_persisted_in_database(client, auth_users, app):
    """F-SEC-010: login attempts are stored in the shared DB-backed table."""
    response = _login(
        client,
        "auth_manager",
        "wrongpass",
        remote_addr="10.46.0.1",
    )
    assert response.status_code == 401

    with app.app_context():
        assert LoginAttempt.query.filter_by(bucket_key="ip:10.46.0.1").count() == 1
        assert LoginAttempt.query.filter_by(bucket_key="user:auth_manager").count() == 1


def test_api_responses_include_browser_security_headers(client):
    """F-SEC-011: all API responses receive the browser hardening headers."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_requirements_lock_exists_is_pinned_and_deploy_references_it():
    """F-SEC-012: backend deploy artifact exists and deploy script uses it."""
    assert REQUIREMENTS_LOCK.exists()

    locked_requirements = [
        line.strip()
        for line in REQUIREMENTS_LOCK.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert locked_requirements
    assert all("==" in requirement for requirement in locked_requirements)

    deploy_script = DEPLOY_SCRIPT.read_text()
    assert "requirements.lock" in deploy_script
    assert "-r requirements.lock" in deploy_script
    assert "-r requirements.txt" not in deploy_script
    assert "falling back" not in deploy_script.lower()
    assert "refusing non-reproducible deploy" in deploy_script


def test_gitignore_covers_secret_and_diagnostic_artifact_patterns():
    """F-SEC-013: repository ignore rules cover common secret-bearing artifacts."""
    ignored_patterns = {
        line.strip()
        for line in GITIGNORE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }

    assert ".env.*" in ignored_patterns
    assert "*.key" in ignored_patterns
    assert "*.pem" in ignored_patterns
    assert "*.p12" in ignored_patterns
    assert "*.pfx" in ignored_patterns
    assert "*.log" in ignored_patterns
    assert "diagnostic_output*.txt" in ignored_patterns
    assert "secrets.json" in ignored_patterns
    assert "credentials.json" in ignored_patterns


def test_setup_status_rejects_unauthenticated_and_allows_active_user(client, auth_users):
    """F-SEC-014: setup status is no longer public but remains usable post-auth."""
    unauthenticated = client.get("/api/v1/setup/status")
    assert unauthenticated.status_code == 401

    login_response = _login(
        client,
        "auth_operator",
        "operatorpass",
        remote_addr="10.47.0.1",
    )
    assert login_response.status_code == 200

    token = login_response.get_json()["access_token"]
    authenticated = client.get("/api/v1/setup/status", headers=_auth_header(token))

    assert authenticated.status_code == 200
    payload = authenticated.get_json()
    assert isinstance(payload["setup_required"], bool)


def test_deploy_runs_npm_audit_high_gate():
    """F-SEC-015: deploy script includes the high/critical npm audit gate."""
    deploy_script = DEPLOY_SCRIPT.read_text()

    assert "npm audit --audit-level=moderate" in deploy_script
