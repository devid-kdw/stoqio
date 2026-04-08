"""Merge Alembic heads after the Wave 5 security review remediation.

Revision ID: c0d1e2f3a4b5
Revises: a2b3c4d5e6f7, a9f1b2c3d4e5
Create Date: 2026-04-08 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c0d1e2f3a4b5"
down_revision = ("a2b3c4d5e6f7", "a9f1b2c3d4e5")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
