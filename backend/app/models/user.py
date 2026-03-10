"""User model."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import UserRole


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(
        SAEnum(UserRole, name="user_role", create_constraint=True),
        nullable=False,
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    employee = db.relationship("Employee", backref="user_account", lazy="select")
