import sys
import os

from dotenv import load_dotenv

# Ensure backend/ is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.user import User
from werkzeug.security import check_password_hash

load_dotenv()

def diagnostic():
    app = create_app()
    with app.app_context():
        print(f"DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        u = User.query.filter_by(username='admin').first()
        if not u:
            print("User 'admin' not found in database.")
            users = User.query.all()
            print(f"Total users in DB: {len(users)}")
            for usr in users:
                print(f" - {usr.username} (active: {usr.is_active}, role: {usr.role})")
            return

        print(f"User found: {u.username}")
        print(f"Is active: {u.is_active}")
        print(f"Role: {u.role}")
        print(f"Password hash: {u.password_hash}")
        
        match = check_password_hash(u.password_hash, "admin123")
        print(f"Password 'admin123' match: {match}")

if __name__ == "__main__":
    diagnostic()
