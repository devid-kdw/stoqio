"""Phase 9 smoke tests for operator-facing tooling.

Covers:
  - `backend/diagnostic.py` stays free of credential-sensitive output
  - `scripts/build.sh` and `scripts/deploy.sh` remain shell-syntax valid
"""

from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path

import pytest
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db as _db
from app.models.enums import UserRole
from app.models.user import User

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIAGNOSTIC = REPO_ROOT / "backend" / "diagnostic.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build.sh"
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy.sh"


class _DiagnosticTestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "diagnostic-test-jwt-secret-key-2026-0001"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }


def _run_bash_check(script_path: Path) -> None:
    subprocess.run(["bash", "-n", str(script_path)], check=True, cwd=REPO_ROOT)


def _build_test_app():
    app = create_app(config_override=_DiagnosticTestConfig)
    with app.app_context():
        _db.create_all()
        _db.session.add_all(
            [
                User(
                    username="admin",
                    password_hash=generate_password_hash(
                        "diag-admin-pass", method="pbkdf2:sha256"
                    ),
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
                User(
                    username="diag_extra",
                    password_hash=generate_password_hash(
                        "diag-extra-pass", method="pbkdf2:sha256"
                    ),
                    role=UserRole.VIEWER,
                    is_active=True,
                ),
            ]
        )
        _db.session.commit()
    return app


def test_diagnostic_output_stays_safe(monkeypatch, capsys):
    import diagnostic as diagnostic_module

    app = _build_test_app()
    monkeypatch.setattr(diagnostic_module, "create_app", lambda: app)

    diagnostic_module.diagnostic()

    output = capsys.readouterr().out

    assert "Password hash" not in output
    assert "admin123" not in output
    assert "check_password_hash" not in output
    assert "diag_extra" not in output
    assert "Bootstrap admin user: present" in output
    assert "Diagnostic helper: safe operator status only." in output


def test_diagnostic_handles_unavailable_database_without_sensitive_output(tmp_path):
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": f"sqlite:///{tmp_path / 'missing.db'}",
            "JWT_SECRET_KEY": "diagnostic-test-jwt-secret-key-2026-0001",
            "FLASK_ENV": "development",
            "PYTHONPATH": f"{REPO_ROOT / 'backend'}",
        }
    )

    result = subprocess.run(
        [sys.executable, str(BACKEND_DIAGNOSTIC)],
        cwd=REPO_ROOT / "backend",
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    assert "Database check: unavailable" in output
    assert "Password hash" not in output
    assert "admin123" not in output
    assert "check_password_hash" not in output


@pytest.mark.parametrize("script_path", [BUILD_SCRIPT, DEPLOY_SCRIPT])
def test_shell_scripts_are_syntax_valid(script_path):
    _run_bash_check(script_path)


# ---------------------------------------------------------------------------
# F-SEC-008 contract locks (Wave 4 Phase 4)
# ---------------------------------------------------------------------------
# The tests below lock the exact guarantees introduced / confirmed in Wave 4
# Phase 4 and are intentionally kept separate from the broader operator-output
# test above so the security contract is obvious to future reviewers.
#
#  1. _redacted_database_uri() strips the password component from any URI that
#     carries credentials — the helper is the single enforcement point.
#  2. _redacted_database_uri() still returns operationally useful text when a
#     URI is configured without a password, and "not configured" when absent.
#  3. diagnostic.py carries a visible LOCAL SUPPORT TOOL ONLY warning so that
#     anyone reading the file understands the intended use boundary before
#     running or committing it.
# ---------------------------------------------------------------------------


def test_diagnostic_uri_redactor_hides_password_component():
    """_redacted_database_uri must not expose the password in the returned string.

    This is the core F-SEC-008 redaction contract: no matter what credentials
    the DATABASE_URL contains, the helper must strip the password before the
    diagnostic can print it.
    """
    import diagnostic as diagnostic_module

    uri_with_password = "postgresql://dbuser:SuperSecret123@db.internal:5432/stoqio"
    result = diagnostic_module._redacted_database_uri(uri_with_password)

    assert "SuperSecret123" not in result, (
        f"Plaintext password must not appear in redacted URI output; got: {result!r}"
    )


def test_diagnostic_uri_redactor_remains_operationally_useful():
    """Redacted output must still indicate that a URI is configured.

    Hiding the password is not useful if it also hides the fact that a database
    is configured at all.  The redacted string must retain enough context
    (driver, host, database name, or similar) to be actionable in support.
    """
    import diagnostic as diagnostic_module

    uri_with_password = "postgresql://dbuser:SuperSecret123@db.internal:5432/stoqio"
    result = diagnostic_module._redacted_database_uri(uri_with_password)

    # At minimum the result must not be "not configured"
    assert result != "not configured", "Configured URI must not appear as 'not configured'"
    # And it must not be completely empty
    assert result.strip(), "Redacted URI output must not be empty"


def test_diagnostic_uri_redactor_handles_uri_without_password():
    """A URI without a password component must pass through without mangling."""
    import diagnostic as diagnostic_module

    uri_no_password = "sqlite:////srv/app/wms_dev.db"
    result = diagnostic_module._redacted_database_uri(uri_no_password)

    assert result != "not configured"
    assert "SuperSecret123" not in result  # sanity: nothing injected


def test_diagnostic_uri_redactor_handles_none():
    """None DATABASE_URI must return 'not configured', not raise."""
    import diagnostic as diagnostic_module

    result = diagnostic_module._redacted_database_uri(None)
    assert result == "not configured"


def test_diagnostic_script_has_local_support_only_warning():
    """F-SEC-008: diagnostic.py must carry a visible production-use warning.

    The warning must state three things explicitly:
      - this is a local/support-only tool
      - it must not be run on production instances
      - it must not be committed with real credentials

    A source-level assertion is used here because the warning lives in the
    module docstring and is not printed to stdout at runtime.  The assertion
    is narrow — it checks for specific keyword phrases, not exact formatting —
    so it will survive minor wording edits while still locking the intent.
    """
    source = BACKEND_DIAGNOSTIC.read_text()

    assert "LOCAL SUPPORT TOOL ONLY" in source, (
        "diagnostic.py must contain the literal text 'LOCAL SUPPORT TOOL ONLY'"
    )
    assert "production" in source.lower(), (
        "diagnostic.py must explicitly mention production in its warning"
    )
    assert "credentials" in source.lower(), (
        "diagnostic.py must warn against committing real credentials"
    )
