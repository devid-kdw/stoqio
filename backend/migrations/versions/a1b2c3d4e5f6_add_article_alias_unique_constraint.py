"""add unique constraint on article_alias (article_id, normalized)

Revision ID: a1b2c3d4e5f6
Revises: 7c2d2c6d0f4a
Create Date: 2026-03-23 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "7c2d2c6d0f4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_article_alias_article_normalized",
        "article_alias",
        ["article_id", "normalized"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_article_alias_article_normalized",
        "article_alias",
        type_="unique",
    )
