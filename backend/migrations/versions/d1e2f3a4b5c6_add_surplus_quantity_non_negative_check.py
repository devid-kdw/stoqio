"""Add CHECK (quantity >= 0) constraint to surplus.quantity.

Mirrors the ck_stock_quantity_gte_zero constraint already present on the
stock table (see models/stock.py).  Prevents the approval service or any
direct DB write from storing a negative surplus quantity.

Finding: V-7 / Wave 6 Phase 1 security review (2026-04-08).

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-04-08 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None

_CONSTRAINT_NAME = "ck_surplus_quantity_gte_zero"
_TABLE_NAME = "surplus"


def upgrade() -> None:
    # SQLite does not support ALTER TABLE ADD CONSTRAINT directly.
    # Use batch mode (copy-and-move) for SQLite; PostgreSQL uses the standard path.
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(_TABLE_NAME) as batch_op:
            batch_op.create_check_constraint(_CONSTRAINT_NAME, sa.text("quantity >= 0"))
    else:
        op.create_check_constraint(_CONSTRAINT_NAME, _TABLE_NAME, "quantity >= 0")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(_TABLE_NAME) as batch_op:
            batch_op.drop_constraint(_CONSTRAINT_NAME, type_="check")
    else:
        op.drop_constraint(_CONSTRAINT_NAME, _TABLE_NAME, type_="check")
