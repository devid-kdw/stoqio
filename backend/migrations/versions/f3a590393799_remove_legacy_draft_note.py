"""remove legacy draft note

Revision ID: f3a590393799
Revises: e692013166e4
Create Date: 2026-03-11 21:50:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f3a590393799"
down_revision = "e692013166e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("draft", schema=None) as batch_op:
        batch_op.drop_column("note")


def downgrade() -> None:
    with op.batch_alter_table("draft", schema=None) as batch_op:
        batch_op.add_column(sa.Column("note", sa.Text(), nullable=True))
