"""WMS application factory."""

from flask import Flask

from .config import get_config
from .extensions import db, jwt, migrate


def create_app(config_override=None):
    """Create and configure the Flask application.

    Args:
        config_override: Optional config object/class used in tests.
    """
    app = Flask(__name__)

    # Load configuration
    if config_override is not None:
        app.config.from_object(config_override)
    else:
        app.config.from_object(get_config())

    # Initialise extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from .api import register_blueprints

    register_blueprints(app)

    return app
