"""WMS application factory."""

import os
from datetime import datetime, timezone, timedelta

from flask import Flask, send_from_directory

from .config import get_config
from .extensions import db, jwt, migrate

# ---------------------------------------------------------------------------
# Automatic revoked-token cleanup state (S-1 / Wave 6 Phase 1)
# Tracks when cleanup last ran so it fires at most once per hour.
# ---------------------------------------------------------------------------
_last_token_cleanup: datetime | None = None

# ---------------------------------------------------------------------------
# Browser security header constants (F-SEC-011)
# ---------------------------------------------------------------------------

# Content-Security-Policy baseline for the Vite/React/Mantine SPA.
# 'unsafe-inline' is required in style-src because Mantine's Emotion-based
# CSS-in-JS injects runtime <style> blocks that cannot be hashed at build time.
# Removing 'unsafe-inline' from style-src breaks Mantine component rendering.
#
# NOTE — refresh-token storage tradeoff (DEC-FE-006 / F-SEC-011):
# The frontend deliberately persists the refresh token in window.localStorage
# (see frontend/src/store/authStore.ts). This is an accepted design baseline
# for STOQIO's current operator-oriented deployment model. The headers below
# are the compensating browser hardening control for that tradeoff. They
# reduce XSS blast radius by restricting script sources, blocking framing, and
# preventing MIME sniffing. Do not treat this file as permission to start
# storing additional sensitive values in localStorage.
_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


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

    # Register maintenance CLI commands
    from .commands import register_commands

    register_commands(app)

    # -----------------------------------------------------------------------
    # Response-hardening headers (F-SEC-011, K-4 / Wave 6 Phase 1)
    # -----------------------------------------------------------------------
    @app.after_request
    def _add_security_headers(response):
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response

    # -----------------------------------------------------------------------
    # Automatic revoked-token cleanup (S-1 / Wave 6 Phase 1)
    # Runs at most once per hour to purge expired revoked_token rows.
    # -----------------------------------------------------------------------
    @app.before_request
    def _auto_purge_revoked_tokens():
        global _last_token_cleanup
        now = datetime.now(timezone.utc)
        if _last_token_cleanup is None or (now - _last_token_cleanup) > timedelta(hours=1):
            try:
                from app.models.revoked_token import RevokedToken
                RevokedToken.query.filter(
                    RevokedToken.expires_at.isnot(None),
                    RevokedToken.expires_at < now
                ).delete(synchronize_session=False)
                db.session.commit()
                _last_token_cleanup = now
            except Exception:
                db.session.rollback()

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
