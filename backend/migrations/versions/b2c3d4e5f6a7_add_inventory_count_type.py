"""add inventory_count_type column to inventory_count

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None

# Enum values
_ENUM_NAME = "inventory_count_type"
_ENUM_VALUES = ("REGULAR", "OPENING")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # Explicitly create the enum type before the column is added.
        pg_enum = postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False)
        pg_enum.create(bind, checkfirst=True)
        op.add_column(
            "inventory_count",
            sa.Column(
                "type",
                postgresql.ENUM(*_ENUM_VALUES, name=_ENUM_NAME, create_type=False),
                nullable=False,
                server_default="REGULAR",
            ),
        )
    else:
        # SQLite — use batch mode to avoid ALTER TABLE limitations.
        with op.batch_alter_table("inventory_count") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "type",
                    sa.Enum(*_ENUM_VALUES, name=_ENUM_NAME),
                    nullable=False,
                    server_default="REGULAR",
                )
            )

    # Remove server_default after backfill so future rows must be explicit.
    if dialect == "postgresql":
        op.alter_column("inventory_count", "type", server_default=None)
    else:
        with op.batch_alter_table("inventory_count") as batch_op:
            batch_op.alter_column("type", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.drop_column("inventory_count", "type")
        bind.execute(sa.text(f"DROP TYPE IF EXISTS {_ENUM_NAME}"))
    else:
        with op.batch_alter_table("inventory_count") as batch_op:
            batch_op.drop_column("type")
