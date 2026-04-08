"""Surplus model."""

from datetime import datetime, timezone

from app.extensions import db


class Surplus(db.Model):
    __tablename__ = "surplus"
    __table_args__ = (
        # M-1 surplus uniqueness — dual-constraint design (mirrors stock pattern):
        # uq_surplus_location_article_batch covers rows where batch_id IS NOT NULL.
        # A partial unique index (created in the Wave 7 Phase 2 migration) covers NULL:
        #   CREATE UNIQUE INDEX uq_surplus_no_batch ON surplus (location_id, article_id)
        #   WHERE batch_id IS NULL;
        # Both are required for full uniqueness across the nullable batch_id.
        db.UniqueConstraint(
            "location_id", "article_id", "batch_id",
            name="uq_surplus_location_article_batch",
        ),
    )

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
