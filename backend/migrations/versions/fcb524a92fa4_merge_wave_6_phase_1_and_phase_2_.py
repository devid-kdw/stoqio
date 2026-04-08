"""Merge Wave 6 Phase 1 and Phase 2 migration heads

Revision ID: fcb524a92fa4
Revises: d1e2f3a4b5c6, d5e6f7a8b9c0
Create Date: 2026-04-08 10:38:49.435600
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcb524a92fa4'
down_revision = ('d1e2f3a4b5c6', 'd5e6f7a8b9c0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
