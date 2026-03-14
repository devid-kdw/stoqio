"""WMS application factory."""

import os

from flask import Flask, send_from_directory

from .config import get_config
from .extensions import db, jwt, migrate


def create_app(config_override=None):
    """Create and configure the Flask application.

    Args:
        config_override: Optional config object/class used in tests.
    """
    # Resolve the backend/static directory (one level above this package).
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    _static_dir = os.path.join(_pkg_dir, "..", "static")
    _resolved_static_dir = os.path.abspath(_static_dir)

    # Serve frontend assets through the explicit catch-all below so SPA routes
    # like /warehouse/articles/1 do not get shadowed by Flask's static handler.
    app = Flask(__name__, static_folder=None)

    # Load configuration
    if config_override is not None:
        app.config.from_object(config_override)
    else:
        app.config.from_object(get_config())

    # Initialise extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # Import models so metadata is populated for Alembic
    from . import models  # noqa: F401

    # Register blueprints
    from .api import register_blueprints

    register_blueprints(app)

    # Catch-all: serve React's index.html for any non-API GET request so
    # that React Router can handle client-side routes (/drafts, /login …).
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path):
        target = os.path.join(_resolved_static_dir, path)
        if path and os.path.isfile(target):
            return send_from_directory(_resolved_static_dir, path)
        index = os.path.join(_resolved_static_dir, "index.html")
        if os.path.isfile(index):
            return send_from_directory(_resolved_static_dir, "index.html")
        return "Frontend not built yet. Run scripts/build.sh first.", 404

    return app
