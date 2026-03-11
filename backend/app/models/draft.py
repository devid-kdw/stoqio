"""Draft model — outbound staging record."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import DraftStatus, DraftType, DraftSource


class Draft(db.Model):
    __tablename__ = "draft"

    id = db.Column(db.Integer, primary_key=True)
    draft_group_id = db.Column(
        db.Integer, db.ForeignKey("draft_group.id"), nullable=False
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
    status = db.Column(
        SAEnum(DraftStatus, name="draft_status", create_constraint=True),
        nullable=False,
        default=DraftStatus.DRAFT,
    )
    draft_type = db.Column(
        SAEnum(DraftType, name="draft_type", create_constraint=True),
        nullable=False,
    )
    source = db.Column(
        SAEnum(DraftSource, name="draft_source", create_constraint=True),
        nullable=False,
    )
    scale_id = db.Column(db.String, nullable=True)
    scanner_id = db.Column(db.String, nullable=True)
    station_id = db.Column(db.String, nullable=True)
    source_label = db.Column(db.String, nullable=True)
    source_meta = db.Column(db.JSON, nullable=True)
    client_event_id = db.Column(db.String, unique=True, nullable=False)
    employee_id_ref = db.Column(db.String, nullable=True)
    # Legacy line-level note kept for schema compatibility; v1 Draft Entry uses DraftGroup.description.
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    location = db.relationship("Location", backref="drafts", lazy="select")
    article = db.relationship("Article", backref="drafts", lazy="select")
    batch = db.relationship("Batch", backref="drafts", lazy="select")
    creator = db.relationship("User", backref="drafts", lazy="select")
