"""Maintenance CLI commands for STOQIO WMS.

Register these commands by calling ``register_commands(app)`` inside
:func:`~app.create_app` so they are available via ``flask <command>``.
"""

import click
from datetime import datetime, timezone
from flask.cli import with_appcontext


@click.command("purge-revoked-tokens")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the count of rows that would be deleted without deleting them.",
)
@with_appcontext
def purge_revoked_tokens(dry_run: bool) -> None:
    """Delete expired rows from the revoked_token table.

    Only rows whose ``expires_at`` is strictly in the past are removed.
    Rows with ``expires_at IS NULL`` are never touched.

    Invoke explicitly — this command is never run automatically by the
    application at startup, on requests, or during logout.

    Examples::

        # Preview (no changes written)
        flask purge-revoked-tokens --dry-run

        # Execute cleanup
        flask purge-revoked-tokens
    """
    from app.extensions import db  # noqa: PLC0415
    from app.models.revoked_token import RevokedToken  # noqa: PLC0415

    now = datetime.now(timezone.utc)

    expired_q = db.session.query(RevokedToken).filter(
        RevokedToken.expires_at.isnot(None),
        RevokedToken.expires_at < now,
    )

    count = expired_q.count()

    if dry_run:
        click.echo(
            f"[dry-run] {count} expired revoked_token row(s) would be deleted."
        )
        return

    expired_q.delete(synchronize_session=False)
    db.session.commit()
    click.echo(f"Deleted {count} expired revoked_token row(s).")


def register_commands(app) -> None:
    """Attach all maintenance CLI commands to *app*."""
    app.cli.add_command(purge_revoked_tokens)
