"""add index on revoked_token.expires_at for cleanup query

Adds a partial index on ``revoked_token(expires_at)`` covering only
non-NULL rows.  This supports the ``flask purge-revoked-tokens`` query
path (``WHERE expires_at IS NOT NULL AND expires_at < :now``) without
indexing the NULL rows that the cleanup deliberately skips.

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-04-03 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_revoked_token_expires_at_nonnull"


def upgrade() -> None:
    # Partial index: skip NULL rows (they are never candidates for cleanup).
    op.create_index(
        _INDEX_NAME,
        "revoked_token",
        ["expires_at"],
        unique=False,
        sqlite_where=sa.text("expires_at IS NOT NULL"),
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="revoked_token")
