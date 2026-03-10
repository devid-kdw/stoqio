import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models.location import Location

load_dotenv()

def seed_location():
    app = create_app()
    with app.app_context():
        # Check if already seeded as well
        if Location.query.filter_by(name='Main Warehouse').first():
            print("Location already seeded")
            return
        loc = Location(name='Main Warehouse', is_active=True)
        db.session.add(loc)
        db.session.commit()
        print("Location seeded")

if __name__ == "__main__":
    seed_location()
