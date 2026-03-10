"""OrderLine model."""

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import OrderLineStatus


class OrderLine(db.Model):
    __tablename__ = "order_line"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer, db.ForeignKey("order.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    supplier_article_code = db.Column(db.String, nullable=True)
    ordered_qty = db.Column(db.Numeric(14, 3), nullable=False)
    received_qty = db.Column(
        db.Numeric(14, 3), nullable=False, server_default="0"
    )
    uom = db.Column(db.String, nullable=False)
    unit_price = db.Column(db.Numeric(14, 4), nullable=True)
    delivery_date = db.Column(db.Date, nullable=True)
    status = db.Column(
        SAEnum(OrderLineStatus, name="order_line_status", create_constraint=True),
        nullable=False,
        default=OrderLineStatus.OPEN,
    )
    note = db.Column(db.Text, nullable=True)

    # Relationships
    article = db.relationship("Article", backref="order_lines", lazy="select")
