"""Application configuration classes.

Reads DATABASE_URL and JWT_SECRET_KEY from environment variables.
Production refuses to start if JWT_SECRET_KEY is missing, default, or weak.
"""

import os


class _Base:
    """Shared settings across all environments."""

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://localhost/wms_dev"
    )


class Development(_Base):
    """Local development — debug mode on, permissive defaults."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql://localhost/wms_dev"
    )


class Production(_Base):
    """Pi / production — strict secret validation."""

    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")

    _WEAK_SECRETS = frozenset(
        {"", "dev-secret-change-me", "change-me", "secret", "password"}
    )

    def __init__(self) -> None:
        super().__init__()
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
    """Return the config class matching FLASK_ENV (default: development)."""
    env = os.getenv("FLASK_ENV", "development").lower()
    cfg_cls = _configs.get(env, Development)
    # Production is a class that validates on instantiation
    if env == "production":
        return cfg_cls()
    return cfg_cls
