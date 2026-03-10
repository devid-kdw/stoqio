"""SystemConfig model — key-value settings store."""

from datetime import datetime, timezone

from app.extensions import db


class SystemConfig(db.Model):
    __tablename__ = "system_config"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
