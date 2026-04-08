"""Wave 5 ops/deploy regression tests."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPLOY_SCRIPT = REPO_ROOT / "scripts" / "deploy.sh"
ALEMBIC_ENV = REPO_ROOT / "backend" / "migrations" / "env.py"


def test_deploy_runs_npm_audit_before_frontend_build():
    """The high-severity npm audit gate must run before build promotion."""
    deploy_text = DEPLOY_SCRIPT.read_text()
    lines = deploy_text.splitlines()

    audit_line = next(
        index for index, line in enumerate(lines) if "npm audit --audit-level=high" in line
    )
    build_line = next(
        index
        for index, line in enumerate(lines)
        if '"$ROOT_DIR/scripts/build.sh"' in line
    )

    assert audit_line < build_line


def test_alembic_env_loads_backend_dotenv_before_create_app():
    """Alembic env.py should load backend/.env before resolving app config."""
    env_text = ALEMBIC_ENV.read_text()
    lines = env_text.splitlines()

    load_dotenv_line = next(
        index for index, line in enumerate(lines) if "load_dotenv(_ENV_FILE, override=False)" in line
    )
    create_app_line = next(index for index, line in enumerate(lines) if "from app import create_app" in line)

    assert 'from dotenv import load_dotenv' in env_text
    assert '_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")' in env_text
    assert 'load_dotenv(_ENV_FILE, override=False)' in env_text
    assert load_dotenv_line < create_app_line
