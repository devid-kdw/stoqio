"""add approval override

Revision ID: e692013166e4
Revises: 733fdf937291
Create Date: 2026-03-11 21:03:52.306903
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e692013166e4'
down_revision = '733fdf937291'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_override",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draft_group_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("batch_key", sa.String(), nullable=False),
        sa.Column("override_quantity", sa.Numeric(14, 3), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["article.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["batch.id"]),
        sa.ForeignKeyConstraint(["draft_group_id"], ["draft_group.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_group_id",
            "article_id",
            "batch_key",
            name="uq_approval_override_group_article_batch_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("approval_override")
