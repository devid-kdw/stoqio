"""RoleDisplayName model — configurable role labels per installation."""

from sqlalchemy import Enum as SAEnum

from app.extensions import db
from app.models.enums import UserRole


class RoleDisplayName(db.Model):
    __tablename__ = "role_display_name"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(
        SAEnum(UserRole, name="user_role", create_constraint=True, create_type=False),
        unique=True,
        nullable=False,
    )
    display_name = db.Column(db.String(50), nullable=False)
