"""Article model."""

from datetime import datetime, timezone

from sqlalchemy.orm import validates

from app.extensions import db


class Article(db.Model):
    __tablename__ = "article"

    id = db.Column(db.Integer, primary_key=True)
    article_no = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("category.id"), nullable=False
    )
    base_uom = db.Column(
        db.Integer, db.ForeignKey("uom_catalog.id"), nullable=False
    )
    pack_size = db.Column(db.Numeric(14, 3), nullable=True)
    pack_uom = db.Column(
        db.Integer, db.ForeignKey("uom_catalog.id"), nullable=True
    )
    barcode = db.Column(db.String, nullable=True)
    manufacturer = db.Column(db.String, nullable=True)
    manufacturer_art_number = db.Column(db.String, nullable=True)
    has_batch = db.Column(db.Boolean, nullable=False, default=False)
    initial_average_price = db.Column(db.Numeric(14, 4), nullable=True)
    reorder_threshold = db.Column(db.Numeric(14, 3), nullable=True)
    reorder_coverage_days = db.Column(db.Integer, nullable=True)
    density = db.Column(db.Numeric(14, 3), nullable=False, server_default="1.0")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    category = db.relationship("Category", backref="articles", lazy="select")
    base_uom_ref = db.relationship(
        "UomCatalog", foreign_keys=[base_uom], lazy="select"
    )
    pack_uom_ref = db.relationship(
        "UomCatalog", foreign_keys=[pack_uom], lazy="select"
    )
    batches = db.relationship("Batch", backref="article", lazy="select")
    aliases = db.relationship(
        "ArticleAlias", backref="article", lazy="select", cascade="all, delete-orphan"
    )
    suppliers = db.relationship(
        "ArticleSupplier", backref="article", lazy="select", cascade="all, delete-orphan"
    )

    @validates("article_no")
    def _normalize_article_no(self, _key, value):
        """Store article numbers normalized to uppercase."""
        if value is None:
            return value
        return value.upper()
