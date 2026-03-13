"""add report_count to missing_article_report

Revision ID: 9b3c4d5e6f70
Revises: f3a590393799
Create Date: 2026-03-13 18:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b3c4d5e6f70"
down_revision = "f3a590393799"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "missing_article_report",
        sa.Column(
            "report_count",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    connection = op.get_bind()
    report = sa.table(
        "missing_article_report",
        sa.column("id", sa.Integer()),
        sa.column("normalized_term", sa.String()),
        sa.column("report_count", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    duplicate_terms = [
        row[0]
        for row in connection.execute(
            sa.select(report.c.normalized_term)
            .where(report.c.status == "OPEN")
            .group_by(report.c.normalized_term)
            .having(sa.func.count(report.c.id) > 1)
        ).all()
    ]
    for normalized_term in duplicate_terms:
        rows = connection.execute(
            sa.select(
                report.c.id,
                report.c.report_count,
            )
            .where(
                report.c.normalized_term == normalized_term,
                report.c.status == "OPEN",
            )
            .order_by(report.c.created_at.asc(), report.c.id.asc())
        ).all()
        keeper_id = rows[0].id
        total_count = sum((row.report_count or 1) for row in rows)
        duplicate_ids = [row.id for row in rows[1:]]

        connection.execute(
            sa.update(report)
            .where(report.c.id == keeper_id)
            .values(report_count=total_count)
        )
        if duplicate_ids:
            connection.execute(
                sa.delete(report).where(report.c.id.in_(duplicate_ids))
            )

    op.create_index(
        "uq_missing_article_report_open_normalized_term",
        "missing_article_report",
        ["normalized_term"],
        unique=True,
        sqlite_where=sa.text("status = 'OPEN'"),
        postgresql_where=sa.text("status = 'OPEN'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_missing_article_report_open_normalized_term",
        table_name="missing_article_report",
    )
    op.drop_column("missing_article_report", "report_count")
