"""Location model."""

from app.extensions import db


class Location(db.Model):
    __tablename__ = "location"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    timezone = db.Column(db.String, nullable=False, server_default="Europe/Berlin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
