"""Add composite index on login_attempt(bucket_key, attempted_at).

Revision ID: d5e6f7a8b9c0
Revises: c0d1e2f3a4b5
Create Date: 2026-04-08 00:00:00.000000

Fixes N-1 from the 2026-04-08 security review: the check_rate_limit() query
in utils/auth.py filters on both bucket_key AND attempted_at >= window_start.
A composite index (bucket_key, attempted_at) serves this query efficiently.
The existing single-column index on bucket_key is kept; this index is additive.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_login_attempt_bucket_key_attempted_at",
        "login_attempt",
        ["bucket_key", "attempted_at"],
    )


def downgrade():
    op.drop_index(
        "ix_login_attempt_bucket_key_attempted_at",
        table_name="login_attempt",
    )
