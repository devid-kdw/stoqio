"""Batch model."""

from datetime import datetime, timezone

from app.extensions import db


class Batch(db.Model):
    __tablename__ = "batch"
    __table_args__ = (
        # M-2: Prevents duplicate batch rows for the same article/code pair.
        # Concurrent receiving could create two Batch rows with identical
        # (article_id, batch_code), making later .first() queries nondeterministic.
        db.UniqueConstraint(
            "article_id", "batch_code",
            name="uq_batch_article_code",
        ),
    )

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
