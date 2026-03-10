"""Transaction model — immutable audit trail for all inventory operations."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import TxType


class Transaction(db.Model):
    __tablename__ = "transaction"

    id = db.Column(db.Integer, primary_key=True)
    tx_type = db.Column(
        SAEnum(TxType, name="tx_type", create_constraint=True),
        nullable=False,
    )
    occurred_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
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
    unit_price = db.Column(db.Numeric(14, 4), nullable=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    reference_type = db.Column(db.String, nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    order_number = db.Column(db.String, nullable=True)
    delivery_note_number = db.Column(db.String, nullable=True)
    meta = db.Column(db.JSON, nullable=True)

    # Relationships
    location = db.relationship("Location", backref="transactions", lazy="select")
    article = db.relationship("Article", backref="transactions", lazy="select")
    batch = db.relationship("Batch", backref="transactions", lazy="select")
    user = db.relationship("User", backref="transactions", lazy="select")
