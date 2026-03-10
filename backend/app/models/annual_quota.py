"""AnnualQuota model — yearly issuance limits."""

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import QuotaEnforcement


class AnnualQuota(db.Model):
    __tablename__ = "annual_quota"

    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String, nullable=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("category.id"), nullable=True
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=True
    )
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=True
    )
    quantity = db.Column(db.Numeric(14, 3), nullable=False)
    uom = db.Column(db.String, nullable=False)
    reset_month = db.Column(db.Integer, nullable=False, server_default="1")
    enforcement = db.Column(
        SAEnum(QuotaEnforcement, name="quota_enforcement", create_constraint=True),
        nullable=False,
        default=QuotaEnforcement.WARN,
    )

    # Relationships
    category = db.relationship("Category", backref="annual_quotas", lazy="select")
    article = db.relationship("Article", backref="annual_quotas", lazy="select")
    employee = db.relationship("Employee", backref="annual_quotas", lazy="select")
