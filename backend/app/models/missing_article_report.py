"""MissingArticleReport model."""

from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum, text

from app.extensions import db
from app.models.enums import MissingArticleReportStatus


class MissingArticleReport(db.Model):
    __tablename__ = "missing_article_report"
    __table_args__ = (
        db.Index(
            "uq_missing_article_report_open_normalized_term",
            "normalized_term",
            unique=True,
            sqlite_where=text("status = 'OPEN'"),
            postgresql_where=text("status = 'OPEN'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    reported_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    search_term = db.Column(db.String, nullable=False)
    normalized_term = db.Column(db.String, nullable=False)
    report_count = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    status = db.Column(
        SAEnum(
            MissingArticleReportStatus,
            name="missing_article_report_status",
            create_constraint=True,
        ),
        nullable=False,
        default=MissingArticleReportStatus.OPEN,
    )
    resolution_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    reporter = db.relationship("User", backref="missing_article_reports", lazy="select")
