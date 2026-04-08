"""Wave 7 closeout — enforce a single active inventory count.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-08 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # H-3 closeout: service-level FOR UPDATE cannot lock an absent active row.
    # This partial unique index lets the database reject a second IN_PROGRESS
    # count even when two start_count() requests race before either commits.
    #
    # Production note: if multiple IN_PROGRESS rows already exist, this migration
    # will fail. Complete/cancel duplicates before running it.
    op.create_index(
        "uq_inventory_count_in_progress",
        "inventory_count",
        ["status"],
        unique=True,
        sqlite_where=sa.text("status = 'IN_PROGRESS'"),
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
    )


def downgrade() -> None:
    op.drop_index("uq_inventory_count_in_progress", table_name="inventory_count")
