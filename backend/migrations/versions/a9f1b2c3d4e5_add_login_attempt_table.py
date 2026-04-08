"""Add login_attempt table for DB-backed rate limiting (F-SEC-010).

Revision ID: a9f1b2c3d4e5
Revises: f3a590393799
Create Date: 2026-04-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a9f1b2c3d4e5"
down_revision = "f3a590393799"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_attempt",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bucket_key", sa.String(length=255), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_login_attempt_bucket_key"),
        "login_attempt",
        ["bucket_key"],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f("ix_login_attempt_bucket_key"), table_name="login_attempt")
    op.drop_table("login_attempt")
