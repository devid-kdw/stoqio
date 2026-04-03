"""Order model."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import OrderStatus


class Order(db.Model):
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String, unique=True, nullable=False)
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=False
    )
    supplier_confirmation_number = db.Column(db.String, nullable=True)
    status = db.Column(
        SAEnum(OrderStatus, name="order_status", create_constraint=True),
        nullable=False,
        default=OrderStatus.OPEN,
    )
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    supplier = db.relationship("Supplier", backref="orders", lazy="select")
    creator = db.relationship("User", backref="orders", lazy="select")
    lines = db.relationship(
        "OrderLine", backref="order", lazy="select", cascade="all, delete-orphan"
    )
