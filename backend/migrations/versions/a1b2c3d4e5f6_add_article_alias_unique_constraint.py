"""add unique constraint on article_alias (article_id, normalized)

Revision ID: a1b2c3d4e5f6
Revises: 7c2d2c6d0f4a
Create Date: 2026-03-23 00:00:00.000000

DEC-BE-015 (amended Wave 2 Phase 1):
  SQLite does not support named unique constraints via the batch copy-and-move
  path.  Using create_unique_constraint inside batch_alter_table triggered an
  Alembic UserWarning ("Skipping unsupported ALTER for creation of implicit
  constraint") and silently dropped the constraint name.

  Fix: use create_index(unique=True) inside the SQLite batch context, which
  produces an equivalent UNIQUE index and is fully enforced by SQLite.  The
  PostgreSQL path continues to use op.create_unique_constraint which maps to
  a named database constraint.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "7c2d2c6d0f4a"
branch_labels = None
depends_on = None

_CONSTRAINT_NAME = "uq_article_alias_article_normalized"
_COLUMNS = ["article_id", "normalized"]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite batch path: a UNIQUE index is the correct/supported equivalent.
        # create_unique_constraint inside batch_alter_table is not supported and
        # emits a misleading warning while silently omitting the constraint.
        with op.batch_alter_table("article_alias") as batch_op:
            batch_op.create_index(
                _CONSTRAINT_NAME,
                _COLUMNS,
                unique=True,
            )
    else:
        op.create_unique_constraint(
            _CONSTRAINT_NAME,
            "article_alias",
            _COLUMNS,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("article_alias") as batch_op:
            batch_op.drop_index(_CONSTRAINT_NAME)
    else:
        op.drop_constraint(
            _CONSTRAINT_NAME,
            "article_alias",
            type_="unique",
        )

