"""Pytest fixtures for WMS backend tests.

Provides an application instance and test client wired to a dedicated
test database.  Each test runs inside a rolled-back transaction so the
DB is clean between runs.
"""

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db as _db


class _TestConfig:
    """In-memory SQLite config for fast, isolated tests.

    StaticPool ensures all connections (including those opened by Flask test
    client requests) share the same in-memory SQLite database, so rows
    committed in fixture setup are visible to HTTP handler code.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # Keep test JWTs deterministic while satisfying PyJWT's 32-byte HS256 recommendation.
    JWT_SECRET_KEY = "test-jwt-secret-key-suite-2026-0001"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }


@pytest.fixture(scope="session")
def app():
    """Create and configure a test application instance."""
    _app = create_app(config_override=_TestConfig)
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.drop_all()


@pytest.fixture()
def client(app):
    """Flask test client — sends requests without a real server."""
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """Provide a transactional database session for a single test."""
    with app.app_context():
        yield _db.session
        _db.session.rollback()


@pytest.fixture(autouse=True)
def clear_rate_limit_state(app):
    """Clear login_attempt rows before every test (F-SEC-010).

    The DB-backed rate limiter commits attempts to the session-scoped SQLite
    database.  Without this cleanup, login attempts from earlier tests
    accumulate and trigger the per-IP or per-username limit unexpectedly in
    later tests.  This is a backend-infrastructure change required to keep the
    existing rate-limit tests working after the process-local in-memory store
    was replaced with a shared DB-backed store.
    """
    with app.app_context():
        from app.models.login_attempt import LoginAttempt

        _db.session.query(LoginAttempt).delete()
        _db.session.commit()
    yield


@pytest.fixture(scope="session")
def auth_users(app):
    """Create fixed test users for auth tests (once per test session).

    Returns a dict keyed by role/purpose so individual auth tests can
    reference users without recreating them.
    """
    from werkzeug.security import generate_password_hash

    from app.models.enums import UserRole
    from app.models.user import User

    with app.app_context():
        admin = User(
            username="auth_admin",
            password_hash=generate_password_hash(
                "adminpass", method="pbkdf2:sha256"
            ),
            role=UserRole.ADMIN,
            is_active=True,
        )
        manager = User(
            username="auth_manager",
            password_hash=generate_password_hash(
                "managerpass", method="pbkdf2:sha256"
            ),
            role=UserRole.MANAGER,
            is_active=True,
        )
        operator = User(
            username="auth_operator",
            password_hash=generate_password_hash(
                "operatorpass", method="pbkdf2:sha256"
            ),
            role=UserRole.OPERATOR,
            is_active=True,
        )
        inactive = User(
            username="auth_inactive",
            password_hash=generate_password_hash(
                "inactivepass", method="pbkdf2:sha256"
            ),
            role=UserRole.VIEWER,
            is_active=False,
        )
        _db.session.add_all([admin, manager, operator, inactive])
        _db.session.commit()
        yield {
            "admin": admin,
            "manager": manager,
            "operator": operator,
            "inactive": inactive,
        }
