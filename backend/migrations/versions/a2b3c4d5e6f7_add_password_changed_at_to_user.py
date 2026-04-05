"""add password_changed_at to user

Adds a nullable timezone-aware timestamp column to the ``user`` table.
Stamped by the Settings service every time an admin changes or resets a
user's password.  The /auth/refresh endpoint rejects refresh tokens
whose ``iat`` (issued-at) predates this value, terminating stale
sessions after a credential change.

The column is nullable so existing rows are not broken — a NULL value
means no admin password change has been recorded and refresh proceeds
using the normal user-activity and revocation checks only.

Revision ID: a2b3c4d5e6f7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-05 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a2b3c4d5e6f7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "password_changed_at")
