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
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("article_alias") as batch_op:
            batch_op.create_unique_constraint(
                "uq_article_alias_article_normalized",
                ["article_id", "normalized"],
            )
    else:
        op.create_unique_constraint(
            "uq_article_alias_article_normalized",
            "article_alias",
            ["article_id", "normalized"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("article_alias") as batch_op:
            batch_op.drop_constraint(
                "uq_article_alias_article_normalized",
                type_="unique",
            )
    else:
        op.drop_constraint(
            "uq_article_alias_article_normalized",
            "article_alias",
            type_="unique",
        )
