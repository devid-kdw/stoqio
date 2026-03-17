"""DraftGroup model — daily outbound grouping."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum, text

from app.extensions import db
from app.models.enums import DraftGroupStatus, DraftGroupType


class DraftGroup(db.Model):
    __tablename__ = "draft_group"
    __table_args__ = (
        db.Index(
            "uq_draft_group_pending_daily_outbound_date",
            "operational_date",
            unique=True,
            sqlite_where=text(
                "status = 'PENDING' AND group_type = 'DAILY_OUTBOUND'"
            ),
            postgresql_where=text(
                "status = 'PENDING' AND group_type = 'DAILY_OUTBOUND'"
            ),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    group_number = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        SAEnum(DraftGroupStatus, name="draft_group_status", create_constraint=True),
        nullable=False,
        default=DraftGroupStatus.PENDING,
    )
    group_type = db.Column(
        SAEnum(DraftGroupType, name="draft_group_type", create_constraint=True),
        nullable=False,
        default=DraftGroupType.DAILY_OUTBOUND,
    )
    operational_date = db.Column(db.Date, nullable=False)
    created_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    creator = db.relationship("User", backref="draft_groups", lazy="select")
    drafts = db.relationship("Draft", backref="draft_group", lazy="dynamic")
