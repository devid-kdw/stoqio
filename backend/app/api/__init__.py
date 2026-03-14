"""API blueprint registration.

Each sub-package (auth, articles, …) exposes a blueprint that is
registered here under the /api/v1 prefix.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all API v1 blueprints on *app*."""
    from .health import health_bp
    from .auth.routes import auth_bp
    from .setup.routes import setup_bp
    from .articles.routes import articles_bp
    from .drafts.routes import drafts_bp
    from .approvals.routes import approvals_bp
    from .receiving.routes import receiving_bp
    from .orders.routes import orders_bp
    from .employees.routes import employees_bp
    from .inventory_count.routes import inventory_bp
    from .reports.routes import reports_bp

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(setup_bp, url_prefix="/api/v1")
    app.register_blueprint(articles_bp, url_prefix="/api/v1")
    app.register_blueprint(drafts_bp, url_prefix="/api/v1")
    app.register_blueprint(approvals_bp, url_prefix="/api/v1")
    app.register_blueprint(receiving_bp, url_prefix="/api/v1")
    app.register_blueprint(orders_bp, url_prefix="/api/v1")
    app.register_blueprint(employees_bp, url_prefix="/api/v1")
    app.register_blueprint(inventory_bp, url_prefix="/api/v1")
    app.register_blueprint(reports_bp, url_prefix="/api/v1")
