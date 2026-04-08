"""Persisted login attempt records for the DB-backed rate limiter."""

from datetime import datetime, timezone

from app.extensions import db


class LoginAttempt(db.Model):
    __tablename__ = "login_attempt"

    id = db.Column(db.Integer, primary_key=True)
    bucket_key = db.Column(db.String(255), nullable=False, index=True)
    attempted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
