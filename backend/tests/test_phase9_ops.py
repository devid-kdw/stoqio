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
