"""PersonalIssuance model — personal equipment issuance to employees."""

from datetime import datetime, timezone

from app.extensions import db


class PersonalIssuance(db.Model):
    __tablename__ = "personal_issuance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(
        db.Integer, db.ForeignKey("employee.id"), nullable=False
    )
    article_id = db.Column(
        db.Integer, db.ForeignKey("article.id"), nullable=False
    )
    batch_id = db.Column(
        db.Integer, db.ForeignKey("batch.id"), nullable=True
    )
    quantity = db.Column(db.Numeric(14, 3), nullable=False)
    uom = db.Column(db.String, nullable=False)
    issued_by = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False
    )
    issued_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    note = db.Column(db.Text, nullable=True)

    # Relationships
    employee = db.relationship("Employee", backref="issuances", lazy="select")
    article = db.relationship("Article", backref="personal_issuances", lazy="select")
    batch = db.relationship("Batch", backref="personal_issuances", lazy="select")
    issuer = db.relationship("User", backref="personal_issuances", lazy="select")
