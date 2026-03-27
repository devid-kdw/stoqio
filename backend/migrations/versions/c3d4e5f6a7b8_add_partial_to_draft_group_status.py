"""add PARTIAL to draft_group_status and backfill mixed-resolved groups

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-26 21:00:00.000000

DEC-APP-001 / Wave 2 Phase 1:
  PARTIAL is promoted from a computed-only display escape hatch to a real
  persisted DraftGroup.status value.

Backfill logic
--------------
Any draft_group row that satisfies ALL of:
  - status = 'PENDING'            (was left unmodified by the old service)
  - has NO Draft rows with status = 'DRAFT'   (fully resolved)
  - has at least one 'APPROVED' and at least one 'REJECTED' Draft row
is updated to status = 'PARTIAL'.

SQLite notes
------------
SQLite has no native ALTER TYPE.  The column is stored as TEXT so we only need
to update the CHECK constraint.  Because SQLite does not support dropping/adding
CHECK constraints in-place, we use batch_alter_table to rebuild the table with
the new constraint definition.

PostgreSQL notes
----------------
- ALTER TYPE ... ADD VALUE is used to extend the existing enum type.
- No backfill of the type itself is needed because existing rows contain only
  'PENDING', 'APPROVED', 'REJECTED' which remain valid.
- The column is then left in-place; only the stored string values of affected
  rows change (PENDING -> PARTIAL).
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

_ENUM_NAME = "draft_group_status"
_OLD_VALUES = ("PENDING", "APPROVED", "REJECTED")
_NEW_VALUES = ("PENDING", "APPROVED", "REJECTED", "PARTIAL")

# ---------------------------------------------------------------------------
# Backfill helper
# ---------------------------------------------------------------------------

_BACKFILL_SQL = """
UPDATE draft_group
SET status = 'PARTIAL'
WHERE status = 'PENDING'
  AND id IN (
      SELECT draft_group_id
      FROM draft
      GROUP BY draft_group_id
      HAVING
          SUM(CASE WHEN status = 'DRAFT'    THEN 1 ELSE 0 END) = 0
          AND SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) > 0
          AND SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) > 0
  )
"""


# ---------------------------------------------------------------------------
# upgrade / downgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # Extend the existing PostgreSQL enum type with the new value.
        # IF NOT EXISTS guards against re-runs on an already-migrated DB.
        bind.execute(
            sa.text("ALTER TYPE draft_group_status ADD VALUE IF NOT EXISTS 'PARTIAL'")
        )
    else:
        # SQLite: the column is plain TEXT, so the only thing we need to change
        # is the CHECK constraint stored in the table definition.  We use
        # batch_alter_table to rebuild the table transparently.
        with op.batch_alter_table("draft_group", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
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
                existing_nullable=False,
            )

    # Backfill: correct mixed-resolved groups that are still stored as PENDING.
    bind.execute(sa.text(_BACKFILL_SQL))


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Revert any PARTIAL rows back to PENDING before removing the value so the
    # constraint / enum change does not violate existing data.
    bind.execute(
        sa.text("UPDATE draft_group SET status = 'PENDING' WHERE status = 'PARTIAL'")
    )

    if dialect == "postgresql":
        # PostgreSQL does not support DROP VALUE from an enum type.
        # The safest approach is to recreate the column using the old type.
        # 1. Create the old 3-value type under a temporary name.
        bind.execute(
            sa.text(
                "CREATE TYPE draft_group_status_old AS ENUM ('PENDING', 'APPROVED', 'REJECTED')"
            )
        )
        # 2. Swap the column to the old type.
        bind.execute(
            sa.text(
                "ALTER TABLE draft_group "
                "ALTER COLUMN status TYPE draft_group_status_old "
                "USING status::text::draft_group_status_old"
            )
        )
        # 3. Drop the new (4-value) type and rename the old one back.
        bind.execute(sa.text("DROP TYPE draft_group_status"))
        bind.execute(
            sa.text("ALTER TYPE draft_group_status_old RENAME TO draft_group_status")
        )
    else:
        # SQLite: rebuild table with old 3-value CHECK constraint.
        with op.batch_alter_table("draft_group", schema=None) as batch_op:
            batch_op.alter_column(
                "status",
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
                existing_nullable=False,
            )
