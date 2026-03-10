"""Pytest fixtures for WMS backend tests.

Provides an application instance and test client wired to a dedicated
test database.  Each test runs inside a rolled-back transaction so the
DB is clean between runs.
"""

import pytest

from app import create_app
from app.extensions import db as _db


class _TestConfig:
    """In-memory SQLite config for fast, isolated tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret"


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
