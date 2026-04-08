"""Stock model."""

from datetime import datetime, timezone

from app.extensions import db


class Stock(db.Model):
    __tablename__ = "stock"
    __table_args__ = (
        # M-1 dual-constraint design:
        # uq_stock_location_article_batch covers rows where batch_id IS NOT NULL.
        # In PostgreSQL, UNIQUE constraints treat each NULL as distinct, so multiple
        # no-batch rows for the same (location_id, article_id) would be permitted by
        # this constraint alone.  A partial unique index (created in the Wave 7 Phase 2
        # migration) covers the NULL case:
        #   CREATE UNIQUE INDEX uq_stock_no_batch ON stock (location_id, article_id)
        #   WHERE batch_id IS NULL;
        # Both constraints are required for full uniqueness across the nullable batch_id.
        db.UniqueConstraint(
            "location_id", "article_id", "batch_id",
            name="uq_stock_location_article_batch",
        ),
        db.CheckConstraint("quantity >= 0", name="ck_stock_quantity_gte_zero"),
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
    quantity = db.Column(db.Numeric(14, 3), nullable=False, server_default="0")
    uom = db.Column(db.String, nullable=False)
    average_price = db.Column(
        db.Numeric(14, 4), nullable=False, server_default="0"
    )
    last_updated = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    location = db.relationship("Location", backref="stocks", lazy="select")
    article = db.relationship("Article", backref="stocks", lazy="select")
    batch = db.relationship("Batch", backref="stocks", lazy="select")
