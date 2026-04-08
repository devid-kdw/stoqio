"""InventoryCount and InventoryCountLine models."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import InventoryCountStatus, InventoryCountLineResolution, InventoryCountType


class InventoryCount(db.Model):
    __tablename__ = "inventory_count"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(
        SAEnum(
            InventoryCountStatus,
            name="inventory_count_status",
            create_constraint=True,
        ),
        nullable=False,
        default=InventoryCountStatus.IN_PROGRESS,
    )
    type = db.Column(
        SAEnum(
            InventoryCountType,
            name="inventory_count_type",
            create_constraint=True,
        ),
        nullable=False,
        default=InventoryCountType.REGULAR,
    )
    note = db.Column(db.Text, nullable=True)
    started_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    starter = db.relationship("User", backref="inventory_counts", lazy="select")
    lines = db.relationship(
        "InventoryCountLine",
        backref="inventory_count",
        lazy="select",
        cascade="all, delete-orphan",
    )
    shortage_drafts = db.relationship(
        "Draft",
        back_populates="inventory_count",
        lazy="select",
    )


class InventoryCountLine(db.Model):
    __tablename__ = "inventory_count_line"
    __table_args__ = (
        # N-5 defensive uniqueness — dual-constraint design:
        # uq_count_line_count_article_batch covers rows where batch_id IS NOT NULL.
        # A partial unique index (created in the Wave 7 Phase 2 migration) covers NULL:
        #   CREATE UNIQUE INDEX uq_count_line_no_batch
        #   ON inventory_count_line (inventory_count_id, article_id)
        #   WHERE batch_id IS NULL;
        # NOTE: This is defensive hardening. The H-3 race (Phase 1) creates two separate
        # active InventoryCount records, NOT duplicate lines within one count.  This
        # constraint prevents any future code path from creating such intra-count
        # duplicates.
        db.UniqueConstraint(
            "inventory_count_id", "article_id", "batch_id",
            name="uq_count_line_count_article_batch",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    inventory_count_id = db.Column(
        db.Integer, db.ForeignKey("inventory_count.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_id = db.Column(
        db.Integer, db.ForeignKey("batch.id"), nullable=True
    )
    system_quantity = db.Column(db.Numeric(14, 3), nullable=False)
    counted_quantity = db.Column(db.Numeric(14, 3), nullable=True)
    uom = db.Column(db.String, nullable=False)
    difference = db.Column(db.Numeric(14, 3), nullable=True)
    resolution = db.Column(
        SAEnum(
            InventoryCountLineResolution,
            name="inventory_count_line_resolution",
            create_constraint=True,
        ),
        nullable=True,
    )

    # Relationships
    article = db.relationship("Article", backref="inventory_count_lines", lazy="select")
    batch = db.relationship("Batch", backref="inventory_count_lines", lazy="select")
