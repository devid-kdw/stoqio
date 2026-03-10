"""ArticleSupplier model — many-to-many link between Article and Supplier."""

from app.extensions import db


class ArticleSupplier(db.Model):
    __tablename__ = "article_supplier"

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    supplier_id = db.Column(
        db.Integer, db.ForeignKey("supplier.id"), nullable=False
    )
    supplier_article_code = db.Column(db.String, nullable=True)
    last_price = db.Column(db.Numeric(14, 4), nullable=True)
    last_ordered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    is_preferred = db.Column(db.Boolean, nullable=False, default=False)

    # Relationships
    supplier = db.relationship("Supplier", backref="article_links", lazy="select")
