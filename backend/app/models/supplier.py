"""Supplier model."""

from datetime import datetime, timezone

from app.extensions import db


class Supplier(db.Model):
    __tablename__ = "supplier"

    id = db.Column(db.Integer, primary_key=True)
    internal_code = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    contact_person = db.Column(db.String, nullable=True)
    phone = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    address = db.Column(db.String, nullable=True)
    iban = db.Column(db.String, nullable=True)
    note = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
