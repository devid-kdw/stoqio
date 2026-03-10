"""Batch model."""

from datetime import datetime, timezone

from app.extensions import db


class Batch(db.Model):
    __tablename__ = "batch"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_code = db.Column(db.String, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    barcode = db.Column(db.String, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
