"""Application configuration classes.

Reads DATABASE_URL and JWT_SECRET_KEY from environment variables.
Production (the default when FLASK_ENV is unset) refuses to start if
JWT_SECRET_KEY is missing, weak, or equals the checked-in example value.
"""

import os


class _Base:
    """Shared settings across all environments."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Kept as a constant so Production._WEAK_SECRETS can reject it explicitly.
    # Not used as a runtime fallback.
    _DEV_DEFAULT_JWT_SECRET = "dev-local-jwt-secret-change-me-2026"

    def __init__(self) -> None:
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
        self.SQLALCHEMY_DATABASE_URI = os.getenv(
            "DATABASE_URL", "postgresql://localhost/wms_dev"
        )


class Development(_Base):
    """Local development — debug mode on, permissive defaults."""

    DEBUG = True
    JWT_ALGORITHM = "HS256"


class Production(_Base):
    """Pi / production — strict secret validation."""

    DEBUG = False
    JWT_ALGORITHM = "HS256"

    _WEAK_SECRETS = frozenset(
        {
            "",
            _Base._DEV_DEFAULT_JWT_SECRET,
            "dev-secret-change-me",
            "change-me",
            "secret",
            "password",
        }
    )

    def __init__(self) -> None:
        super().__init__()
        db_url = (os.getenv("DATABASE_URL") or "").strip()
        if not db_url:
            raise RuntimeError(
                "Production requires DATABASE_URL to be set. "
                "Set it in your .env file."
            )
        self.SQLALCHEMY_DATABASE_URI = db_url
        secret = os.getenv("JWT_SECRET_KEY", "")
        if not secret or secret in self._WEAK_SECRETS or len(secret) < 32:
            raise RuntimeError(
                "Production requires a strong JWT_SECRET_KEY "
                "(at least 32 characters, not a well-known default). "
                "Set it in your .env file."
            )
        self.JWT_SECRET_KEY = secret


# Map FLASK_ENV values to config classes
_configs = {
    "development": Development,
    "production": Production,
}


def get_config():
    """Return the config object matching FLASK_ENV (default: production).

    When FLASK_ENV is not set the app starts in production mode, which
    requires both DATABASE_URL and a strong JWT_SECRET_KEY.  Set
    FLASK_ENV=development explicitly for local development runs.
    """
    env = os.getenv("FLASK_ENV", "production").lower()
    cfg_cls = _configs.get(env, Production)
    return cfg_cls()
