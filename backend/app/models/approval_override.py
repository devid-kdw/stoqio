"""ApprovalOverride model — stores ADMIN quantity overrides for aggregated draft rows."""

from app.extensions import db


class ApprovalOverride(db.Model):
    __tablename__ = "approval_override"
    __table_args__ = (
        db.UniqueConstraint(
            "draft_group_id",
            "article_id",
            "batch_key",
            name="uq_approval_override_group_article_batch_key",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    draft_group_id = db.Column(
        db.Integer, db.ForeignKey("draft_group.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_id = db.Column(
        db.Integer, db.ForeignKey("batch.id"), nullable=True
    )
    # Stable unique key for NULL and non-NULL batch buckets alike.
    batch_key = db.Column(db.String, nullable=False)
    override_quantity = db.Column(db.Numeric(14, 3), nullable=False)

    # Relationships
    draft_group = db.relationship("DraftGroup", backref="approval_overrides", lazy="select")
    article = db.relationship("Article", backref="approval_overrides", lazy="select")
    batch = db.relationship("Batch", backref="approval_overrides", lazy="select")
