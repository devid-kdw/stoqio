"""Receiving model — goods receipt record."""

from datetime import datetime, timezone

from app.extensions import db


class Receiving(db.Model):
    __tablename__ = "receiving"

    id = db.Column(db.Integer, primary_key=True)
    order_line_id = db.Column(
        db.Integer, db.ForeignKey("order_line.id"), nullable=True
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_id = db.Column(
        db.Integer, db.ForeignKey("batch.id"), nullable=True
    )
    location_id = db.Column(
        db.Integer, db.ForeignKey("location.id"), nullable=False
    )
    quantity = db.Column(db.Numeric(14, 3), nullable=False)
    uom = db.Column(db.String, nullable=False)
    unit_price = db.Column(db.Numeric(14, 4), nullable=True)
    delivery_note_number = db.Column(db.String, nullable=False)
    note = db.Column(db.Text, nullable=True)
    barcodes_printed = db.Column(db.Integer, nullable=False, server_default="0")
    received_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    received_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    order_line = db.relationship("OrderLine", backref="receivings", lazy="select")
    article = db.relationship("Article", backref="receivings", lazy="select")
    batch = db.relationship("Batch", backref="receivings", lazy="select")
    location = db.relationship("Location", backref="receivings", lazy="select")
    receiver = db.relationship("User", backref="receivings", lazy="select")
