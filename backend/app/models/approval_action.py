"""ApprovalAction model — admin approval/rejection record."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import ApprovalActionType


class ApprovalAction(db.Model):
    __tablename__ = "approval_action"

    id = db.Column(db.Integer, primary_key=True)
    draft_id = db.Column(
        db.Integer, db.ForeignKey("draft.id"), nullable=False
    )
    actor_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    action = db.Column(
        SAEnum(ApprovalActionType, name="approval_action_type", create_constraint=True),
        nullable=False,
    )
    note = db.Column(db.Text, nullable=True)
    acted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    draft = db.relationship("Draft", backref="approval_actions", lazy="select")
    actor = db.relationship("User", backref="approval_actions", lazy="select")
