"""Category model."""

from app.extensions import db


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False)
    label_hr = db.Column(db.String, nullable=False)
    label_en = db.Column(db.String, nullable=True)
    label_de = db.Column(db.String, nullable=True)
    label_hu = db.Column(db.String, nullable=True)
    is_personal_issue = db.Column(db.Boolean, nullable=False, default=False)
    default_annual_quota = db.Column(db.Numeric(14, 3), nullable=True)
    quota_uom = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
