"""Wave 7 Phase 2 — Schema integrity constraints (M-1, M-2, N-5).

Remediates three schema/data-integrity findings from the 2026-04-08 review:

  M-1 (stock): Adds partial unique index for NULL batch_id rows.
       The existing uq_stock_location_article_batch constraint covers non-NULL
       batch_id correctly, but PostgreSQL UNIQUE constraints treat each NULL as
       distinct, so multiple no-batch rows for the same (location_id, article_id)
       can coexist.  A partial index enforces uniqueness for the NULL case.

  M-1 (surplus): Adds full uniqueness for surplus rows (previously unconstrained).
       Same NULL-safe dual-constraint design as stock:
       - UniqueConstraint for non-NULL batch_id rows.
       - Partial unique index for NULL batch_id rows.
       PRODUCTION NOTE: If duplicate no-batch surplus rows exist before this
       migration runs, the index creation will fail.  Run a deduplication step
       first (see backend.md — Open Issues / Risks).

  M-2 (batch): Adds unique constraint on (article_id, batch_code).
       Concurrent receiving could produce duplicate Batch rows for the same
       article/code, making subsequent .first() queries nondeterministic.
       PRODUCTION NOTE: If duplicate (article_id, batch_code) rows exist, the
       constraint creation will fail.  Deduplicate first (see backend.md).

  N-5 (inventory_count_line): Defensive unique constraint on
       (inventory_count_id, article_id, batch_id).
       The H-3 race (Phase 1) creates two separate InventoryCount records, NOT
       duplicate lines within one count.  This constraint is defensive — it
       prevents any future code path from creating intra-count duplicate lines.

Revision ID: a7b8c9d0e1f2
Revises: fcb524a92fa4
Create Date: 2026-04-08 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "fcb524a92fa4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ------------------------------------------------------------------
    # M-1: Stock — partial unique index for NULL batch_id rows.
    # The existing uq_stock_location_article_batch covers non-NULL batch_id.
    # ------------------------------------------------------------------
    op.create_index(
        "uq_stock_no_batch",
        "stock",
        ["location_id", "article_id"],
        unique=True,
        sqlite_where=sa.text("batch_id IS NULL"),
        postgresql_where=sa.text("batch_id IS NULL"),
    )

    # ------------------------------------------------------------------
    # M-1: Surplus — UniqueConstraint for non-NULL batch_id rows.
    # PRODUCTION NOTE: Existing duplicate rows with non-NULL batch_id will
    # cause this step to fail.  Deduplicate before running this migration.
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.create_unique_constraint(
                "uq_surplus_location_article_batch",
                ["location_id", "article_id", "batch_id"],
            )
    else:
        op.create_unique_constraint(
            "uq_surplus_location_article_batch",
            "surplus",
            ["location_id", "article_id", "batch_id"],
        )

    # M-1: Surplus — partial unique index for NULL batch_id rows.
    # PRODUCTION NOTE: Existing duplicate surplus rows with batch_id IS NULL
    # will cause this step to fail.  Deduplicate before running this migration.
    # Example deduplication (keep lowest id per group):
    #   DELETE FROM surplus WHERE id NOT IN (
    #       SELECT MIN(id) FROM surplus WHERE batch_id IS NULL
    #       GROUP BY location_id, article_id
    #   ) AND batch_id IS NULL;
    op.create_index(
        "uq_surplus_no_batch",
        "surplus",
        ["location_id", "article_id"],
        unique=True,
        sqlite_where=sa.text("batch_id IS NULL"),
        postgresql_where=sa.text("batch_id IS NULL"),
    )

    # ------------------------------------------------------------------
    # M-2: Batch — unique constraint on (article_id, batch_code).
    # PRODUCTION NOTE: Existing duplicate (article_id, batch_code) rows will
    # cause this step to fail.  Deduplicate before running this migration.
    # Example deduplication (keep lowest id per pair):
    #   DELETE FROM batch WHERE id NOT IN (
    #       SELECT MIN(id) FROM batch GROUP BY article_id, batch_code
    #   );
    # Then verify all FK references (receiving, stock, surplus, etc.) still
    # point to the surviving batch row; update or nullify stale references.
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        with op.batch_alter_table("batch") as batch_op:
            batch_op.create_unique_constraint(
                "uq_batch_article_code",
                ["article_id", "batch_code"],
            )
    else:
        op.create_unique_constraint(
            "uq_batch_article_code",
            "batch",
            ["article_id", "batch_code"],
        )

    # ------------------------------------------------------------------
    # N-5: InventoryCountLine — defensive uniqueness.
    # UniqueConstraint for non-NULL batch_id rows.
    # ------------------------------------------------------------------
    if dialect == "sqlite":
        with op.batch_alter_table("inventory_count_line") as batch_op:
            batch_op.create_unique_constraint(
                "uq_count_line_count_article_batch",
                ["inventory_count_id", "article_id", "batch_id"],
            )
    else:
        op.create_unique_constraint(
            "uq_count_line_count_article_batch",
            "inventory_count_line",
            ["inventory_count_id", "article_id", "batch_id"],
        )

    # N-5: InventoryCountLine — partial unique index for NULL batch_id rows.
    op.create_index(
        "uq_count_line_no_batch",
        "inventory_count_line",
        ["inventory_count_id", "article_id"],
        unique=True,
        sqlite_where=sa.text("batch_id IS NULL"),
        postgresql_where=sa.text("batch_id IS NULL"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # N-5 rollback
    op.drop_index("uq_count_line_no_batch", table_name="inventory_count_line")
    if dialect == "sqlite":
        with op.batch_alter_table("inventory_count_line") as batch_op:
            batch_op.drop_constraint("uq_count_line_count_article_batch", type_="unique")
    else:
        op.drop_constraint(
            "uq_count_line_count_article_batch", "inventory_count_line", type_="unique"
        )

    # M-2 rollback
    if dialect == "sqlite":
        with op.batch_alter_table("batch") as batch_op:
            batch_op.drop_constraint("uq_batch_article_code", type_="unique")
    else:
        op.drop_constraint("uq_batch_article_code", "batch", type_="unique")

    # M-1 surplus rollback
    op.drop_index("uq_surplus_no_batch", table_name="surplus")
    if dialect == "sqlite":
        with op.batch_alter_table("surplus") as batch_op:
            batch_op.drop_constraint(
                "uq_surplus_location_article_batch", type_="unique"
            )
    else:
        op.drop_constraint(
            "uq_surplus_location_article_batch", "surplus", type_="unique"
        )

    # M-1 stock rollback
    op.drop_index("uq_stock_no_batch", table_name="stock")
