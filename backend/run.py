"""Development entry point.

Usage:
    python run.py
    # or
    flask run          (uses FLASK_APP=app if .flaskenv or env var is set)
"""

from dotenv import load_dotenv

from app import create_app

load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
