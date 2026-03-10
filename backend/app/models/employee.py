"""Employee model."""

from datetime import datetime, timezone

from app.extensions import db


class Employee(db.Model):
    __tablename__ = "employee"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String, unique=True, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    department = db.Column(db.String, nullable=True)
    job_title = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
