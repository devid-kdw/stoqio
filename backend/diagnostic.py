"""Safe operator diagnostic helper for STOQIO backend.

WARNING — LOCAL SUPPORT TOOL ONLY
  - Run this script only on a local development or staging instance.
  - Do NOT run this on a production instance.
  - Do NOT commit this file with real credentials or a real DATABASE_URL in the
    environment.  Always verify your .env is gitignored before running.

This script is intentionally limited to non-sensitive operational checks.
It reports only high-level environment and bootstrap status, never secrets,
password hashes, or password verification results.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url

# Ensure backend/ is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.user import User

load_dotenv()


def _redacted_database_uri(uri: str | None) -> str:
    if not uri:
        return "not configured"

    try:
        return make_url(uri).render_as_string(hide_password=True)
    except Exception:
        return "configured (redacted)"


def diagnostic():
    app = create_app()
    with app.app_context():
        print("Diagnostic helper: safe operator status only.")
        print(
            "DATABASE_URI:",
            _redacted_database_uri(app.config.get("SQLALCHEMY_DATABASE_URI")),
        )
        try:
            admin_user = User.query.filter_by(username="admin").first()
            total_users = User.query.count()
        except OperationalError:
            print("Database check: unavailable (could not connect to the configured database).")
            return

        if not admin_user:
            print("Bootstrap admin user: missing")
            print(f"Total users: {total_users}")
            print("Safe action: run the standard bootstrap seed if this is a fresh install.")
            return

        print("Bootstrap admin user: present")
        print(f"Admin active: {admin_user.is_active}")
        print(f"Admin role: {admin_user.role.value}")
        print(f"Total users: {total_users}")
        print(
            "Safe action: inspect bootstrap and environment configuration if this looks unexpected."
        )

if __name__ == "__main__":
    diagnostic()
