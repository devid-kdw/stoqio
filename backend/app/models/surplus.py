"""Surplus model."""

from datetime import datetime, timezone

from app.extensions import db


class Surplus(db.Model):
    __tablename__ = "surplus"

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(
        db.Integer, db.ForeignKey("location.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_id = db.Column(
        db.Integer, db.ForeignKey("batch.id"), nullable=True
    )
    quantity = db.Column(db.Numeric(14, 3), nullable=False)
    uom = db.Column(db.String, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    location = db.relationship("Location", backref="surpluses", lazy="select")
    article = db.relationship("Article", backref="surpluses", lazy="select")
    batch = db.relationship("Batch", backref="surpluses", lazy="select")
