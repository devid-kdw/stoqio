"""UomCatalog model."""

from app.extensions import db


class UomCatalog(db.Model):
    __tablename__ = "uom_catalog"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True, nullable=False)
    label_hr = db.Column(db.String, nullable=False)
    label_en = db.Column(db.String, nullable=True)
    decimal_display = db.Column(db.Boolean, nullable=False, default=False)
