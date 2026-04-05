"""Application entry point.

Usage:
    FLASK_ENV=development python run.py
    # or
    flask run          (uses FLASK_APP=app if .flaskenv or env var is set)

Debug mode is enabled only when FLASK_ENV is explicitly set to
'development'.  Without that variable the app runs in production mode
and debug is always off.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    _debug = os.getenv("FLASK_ENV", "production").lower() == "development"
    app.run(debug=_debug, port=5000)
