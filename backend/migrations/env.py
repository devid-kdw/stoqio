"""Alembic env.py — reads DB URL from Flask app config."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import create_app
from app.extensions import db

# Alembic Config
config = context.config
import os
if config.config_file_name is not None and os.path.isfile(config.config_file_name):
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

# Create app to populate metadata and get DB URI
app = create_app()
with app.app_context():
    config.set_main_option(
        "sqlalchemy.url",
        app.config["SQLALCHEMY_DATABASE_URI"],
    )

target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to the database."""
    with app.app_context():
        connectable = db.engine
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
