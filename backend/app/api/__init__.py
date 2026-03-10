"""API blueprint registration.

Each sub-package (auth, articles, …) exposes a blueprint that is
registered here under the /api/v1 prefix.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all API v1 blueprints on *app*."""
    from .health import health_bp
    from .auth.routes import auth_bp

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
