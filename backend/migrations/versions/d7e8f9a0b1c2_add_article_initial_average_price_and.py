"""add article initial_average_price and opening inventory resolution

Revision ID: d7e8f9a0b1c2
Revises: b8c9d0e1f2a3
Create Date: 2026-04-08 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d7e8f9a0b1c2"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None

_ENUM_NAME = "inventory_count_line_resolution"
_OLD_VALUES = ("SURPLUS_ADDED", "SHORTAGE_DRAFT_CREATED", "NO_CHANGE")
_NEW_VALUES = (
    "SURPLUS_ADDED",
    "SHORTAGE_DRAFT_CREATED",
    "NO_CHANGE",
    "OPENING_STOCK_SET",
)


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        with op.get_context().autocommit_block():
            bind.execute(
                sa.text(
                    "ALTER TYPE inventory_count_line_resolution "
                    "ADD VALUE IF NOT EXISTS 'OPENING_STOCK_SET'"
                )
            )
        op.add_column(
            "article",
            sa.Column("initial_average_price", sa.Numeric(14, 4), nullable=True),
        )
    else:
        with op.batch_alter_table("inventory_count_line", schema=None) as batch_op:
            batch_op.alter_column(
                "resolution",
                existing_type=sa.Enum(
                    *_OLD_VALUES,
                    name=_ENUM_NAME,
                    create_constraint=True,
                ),
                type_=sa.Enum(
                    *_NEW_VALUES,
                    name=_ENUM_NAME,
                    create_constraint=True,
                ),
                existing_nullable=True,
            )

        with op.batch_alter_table("article", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("initial_average_price", sa.Numeric(14, 4), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    bind.execute(
        sa.text(
            "UPDATE inventory_count_line "
            "SET resolution = 'NO_CHANGE' "
            "WHERE resolution = 'OPENING_STOCK_SET'"
        )
    )

    if dialect == "postgresql":
        op.drop_column("article", "initial_average_price")

        bind.execute(
            sa.text(
                "CREATE TYPE inventory_count_line_resolution_old AS ENUM "
                "('SURPLUS_ADDED', 'SHORTAGE_DRAFT_CREATED', 'NO_CHANGE')"
            )
        )
        bind.execute(
            sa.text(
                "ALTER TABLE inventory_count_line "
                "ALTER COLUMN resolution TYPE inventory_count_line_resolution_old "
                "USING resolution::text::inventory_count_line_resolution_old"
            )
        )
        bind.execute(sa.text("DROP TYPE inventory_count_line_resolution"))
        bind.execute(
            sa.text(
                "ALTER TYPE inventory_count_line_resolution_old "
                "RENAME TO inventory_count_line_resolution"
            )
        )
    else:
        with op.batch_alter_table("inventory_count_line", schema=None) as batch_op:
            batch_op.alter_column(
                "resolution",
                existing_type=sa.Enum(
                    *_NEW_VALUES,
                    name=_ENUM_NAME,
                    create_constraint=True,
                ),
                type_=sa.Enum(
                    *_OLD_VALUES,
                    name=_ENUM_NAME,
                    create_constraint=True,
                ),
                existing_nullable=True,
            )

        with op.batch_alter_table("article", schema=None) as batch_op:
            batch_op.drop_column("initial_average_price")
