"""persist token revocation and lock daily outbound draft groups

Revision ID: 7c2d2c6d0f4a
Revises: 9b3c4d5e6f70
Create Date: 2026-03-17 12:30:00.000000
"""

from decimal import Decimal

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c2d2c6d0f4a"
down_revision = "9b3c4d5e6f70"
branch_labels = None
depends_on = None


def _merge_descriptions(group_rows):
    """Combine distinct daily-note texts when duplicate groups are merged."""
    seen = set()
    parts = []
    for row in group_rows:
        description = (row.description or "").strip()
        if description and description not in seen:
            seen.add(description)
            parts.append(description)
    return "\n\n".join(parts) if parts else None


def _merge_pending_daily_outbound_groups(connection) -> None:
    """Collapse duplicate pending daily-outbound groups before indexing."""
    draft_group = sa.table(
        "draft_group",
        sa.column("id", sa.Integer()),
        sa.column("description", sa.Text()),
        sa.column("status", sa.String()),
        sa.column("operational_date", sa.Date()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("group_type", sa.String()),
    )
    draft = sa.table(
        "draft",
        sa.column("draft_group_id", sa.Integer()),
    )
    approval_override = sa.table(
        "approval_override",
        sa.column("id", sa.Integer()),
        sa.column("draft_group_id", sa.Integer()),
        sa.column("article_id", sa.Integer()),
        sa.column("batch_id", sa.Integer()),
        sa.column("batch_key", sa.String()),
        sa.column("override_quantity", sa.Numeric(14, 3)),
    )

    duplicate_dates = [
        row.operational_date
        for row in connection.execute(
            sa.select(draft_group.c.operational_date)
            .where(
                draft_group.c.status == "PENDING",
                draft_group.c.group_type == "DAILY_OUTBOUND",
            )
            .group_by(draft_group.c.operational_date)
            .having(sa.func.count(draft_group.c.id) > 1)
        ).all()
    ]

    for operational_date in duplicate_dates:
        groups = connection.execute(
            sa.select(
                draft_group.c.id,
                draft_group.c.description,
            )
            .where(
                draft_group.c.operational_date == operational_date,
                draft_group.c.status == "PENDING",
                draft_group.c.group_type == "DAILY_OUTBOUND",
            )
            .order_by(draft_group.c.created_at.asc(), draft_group.c.id.asc())
        ).all()
        keeper_id = groups[0].id
        all_group_ids = [row.id for row in groups]
        duplicate_ids = all_group_ids[1:]

        connection.execute(
            draft_group.update()
            .where(draft_group.c.id == keeper_id)
            .values(description=_merge_descriptions(groups))
        )

        if duplicate_ids:
            connection.execute(
                draft.update()
                .where(draft.c.draft_group_id.in_(duplicate_ids))
                .values(draft_group_id=keeper_id)
            )

            overrides = connection.execute(
                sa.select(
                    approval_override.c.article_id,
                    approval_override.c.batch_id,
                    approval_override.c.batch_key,
                    approval_override.c.override_quantity,
                )
                .where(approval_override.c.draft_group_id.in_(all_group_ids))
                .order_by(approval_override.c.id.asc())
            ).all()

            if overrides:
                merged_overrides = {}
                for row in overrides:
                    key = (row.article_id, row.batch_id, row.batch_key)
                    merged_overrides[key] = merged_overrides.get(
                        key,
                        Decimal("0"),
                    ) + Decimal(str(row.override_quantity))

                connection.execute(
                    approval_override.delete().where(
                        approval_override.c.draft_group_id.in_(all_group_ids)
                    )
                )
                for (
                    article_id,
                    batch_id,
                    batch_key,
                ), override_quantity in merged_overrides.items():
                    connection.execute(
                        approval_override.insert().values(
                            draft_group_id=keeper_id,
                            article_id=article_id,
                            batch_id=batch_id,
                            batch_key=batch_key,
                            override_quantity=override_quantity,
                        )
                    )

            connection.execute(
                draft_group.delete().where(draft_group.c.id.in_(duplicate_ids))
            )


def upgrade() -> None:
    bind = op.get_bind()
    group_type_enum = sa.Enum(
        "DAILY_OUTBOUND",
        "INVENTORY_SHORTAGE",
        name="draft_group_type",
        create_constraint=True,
    )
    if bind.dialect.name == "postgresql":
        group_type_enum.create(bind, checkfirst=True)
        op.add_column(
            "draft_group",
            sa.Column(
                "group_type",
                group_type_enum,
                nullable=False,
                server_default="DAILY_OUTBOUND",
            ),
        )
    else:
        # SQLite: use batch_alter_table (copy-and-move) so that existing named
        # constraints (e.g. UniqueConstraint on group_number) are properly
        # reconstructed and Alembic does not emit the "Skipping unsupported
        # ALTER for creation of implicit constraint" UserWarning.
        with op.batch_alter_table("draft_group", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "group_type",
                    sa.Enum(
                        "DAILY_OUTBOUND",
                        "INVENTORY_SHORTAGE",
                        name="draft_group_type",
                        create_constraint=True,
                    ),
                    nullable=False,
                    server_default="DAILY_OUTBOUND",
                )
            )

    op.create_table(
        "revoked_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("token_type", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE draft_group
            SET group_type = 'INVENTORY_SHORTAGE'
            WHERE id IN (
                SELECT DISTINCT draft_group_id
                FROM draft
                WHERE draft_type = 'INVENTORY_SHORTAGE'
            )
            """
        )
    )

    _merge_pending_daily_outbound_groups(connection)

    op.create_index(
        "uq_draft_group_pending_daily_outbound_date",
        "draft_group",
        ["operational_date"],
        unique=True,
        sqlite_where=sa.text(
            "status = 'PENDING' AND group_type = 'DAILY_OUTBOUND'"
        ),
        postgresql_where=sa.text(
            "status = 'PENDING' AND group_type = 'DAILY_OUTBOUND'"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    group_type_enum = sa.Enum(
        "DAILY_OUTBOUND",
        "INVENTORY_SHORTAGE",
        name="draft_group_type",
        create_constraint=True,
    )
    op.drop_index(
        "uq_draft_group_pending_daily_outbound_date",
        table_name="draft_group",
    )
    op.drop_table("revoked_token")

    with op.batch_alter_table("draft_group", schema=None) as batch_op:
        batch_op.drop_column("group_type")
    if bind.dialect.name == "postgresql":
        group_type_enum.drop(bind, checkfirst=True)
