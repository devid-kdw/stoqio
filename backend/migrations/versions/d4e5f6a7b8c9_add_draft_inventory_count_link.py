"""add explicit inventory_count link on draft

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-27 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None

_FK_NAME = "fk_draft_inventory_count_id_inventory_count"


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.add_column(
            "draft",
            sa.Column("inventory_count_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            _FK_NAME,
            "draft",
            "inventory_count",
            ["inventory_count_id"],
            ["id"],
            ondelete="SET NULL",
        )
    else:
        with op.batch_alter_table("draft") as batch_op:
            batch_op.add_column(
                sa.Column("inventory_count_id", sa.Integer(), nullable=True)
            )
            batch_op.create_foreign_key(
                _FK_NAME,
                "inventory_count",
                ["inventory_count_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_constraint(_FK_NAME, "draft", type_="foreignkey")
        op.drop_column("draft", "inventory_count_id")
    else:
        with op.batch_alter_table("draft") as batch_op:
            batch_op.drop_constraint(_FK_NAME, type_="foreignkey")
            batch_op.drop_column("inventory_count_id")
