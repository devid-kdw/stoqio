# Backend Handoff — Wave 3 Phase 7: Revoked Token Retention Cleanup

## Status

Complete.

## Scope

Implemented one explicit, operator-invoked Flask CLI command (`flask purge-revoked-tokens`) that deletes only expired rows from the `revoked_token` table. Runtime revocation checks (`add_to_blocklist`, `is_token_revoked`, `@jwt.token_in_blocklist_loader`) are unchanged. No implicit cleanup was introduced.

## Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-008, scanned for phase context)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-012, DEC-FE-006 confirmed; no new cross-agent decision required)
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- `backend/app/__init__.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/app/models/revoked_token.py`
- `backend/tests/test_auth.py`
- `backend/migrations/versions/7c2d2c6d0f4a_persist_token_revocation_and_lock_daily_.py` (confirmed `revoked_token` schema and migration head chain)

## Cleanup Mechanism Added

**Flask CLI command: `flask purge-revoked-tokens`**

Location: `backend/app/commands.py`

What it does:
- Queries `revoked_token` for rows where `expires_at IS NOT NULL AND expires_at < now` (UTC).
- Deletes those rows and commits.
- `expires_at IS NULL` rows are explicitly excluded and are never deleted.
- Prints a count of deleted rows on success.

Flags:
- `--dry-run` — counts and reports without writing any changes.

How operators invoke it (from the backend directory with the virtualenv active):

```bash
# Preview — no changes
flask purge-revoked-tokens --dry-run

# Execute cleanup
flask purge-revoked-tokens
```

For scheduled invocation (e.g. daily cron):
```
0 3 * * * cd /path/to/stoqio/backend && venv/bin/flask purge-revoked-tokens >> /var/log/stoqio-cleanup.log 2>&1
```

The command is registered via `register_commands(app)` called inside `create_app()`. It is **not** invoked automatically anywhere.

## Schema / Index Change

**Migration:** `e1f2a3b4c5d6_add_revoked_token_expires_at_index.py`

Added a partial index `ix_revoked_token_expires_at_nonnull` on `revoked_token(expires_at) WHERE expires_at IS NOT NULL`.

Justification: the cleanup query filters on `expires_at IS NOT NULL AND expires_at < :now`. Without an index this is a full table scan. The partial index covers exactly the rows the cleanup touches and adds no overhead for the runtime revocation lookup (which filters by `jti`, not `expires_at`).

Supported on both PostgreSQL and SQLite via the `postgresql_where` / `sqlite_where` kwargs in `op.create_index`.

To apply:
```bash
cd backend && venv/bin/flask db upgrade
```

## Files Changed

| File | Change |
|------|--------|
| `backend/app/commands.py` | New file — `purge_revoked_tokens` CLI command + `register_commands()` |
| `backend/app/__init__.py` | Added `register_commands(app)` call in `create_app()` |
| `backend/migrations/versions/e1f2a3b4c5d6_add_revoked_token_expires_at_index.py` | New migration — partial index on `revoked_token.expires_at` |

No changes to `auth.py`, `routes.py`, `revoked_token.py`, or any test file.

## Commands Run

```
rg -n 'revoked_token|add_to_blocklist|is_token_revoked|logout' backend/app -g '*.py'
cd backend && venv/bin/python -m pytest tests/test_auth.py -q
```

## Tests

- `tests/test_auth.py`: **40 passed, 0 failed** (unchanged from pre-implementation baseline).
- No backend-owned test added. The testing agent owns regression coverage for the cleanup command behavior.

## Open Issues / Risks

- The migration has not been run against the live database yet; the testing agent and documentation agent should note that `flask db upgrade` is required on deploy.
- The `--dry-run` flag is intentionally not tested by the backend agent; it is a simple count path that the testing agent can exercise through Flask's CLI runner.
- Row counts could be zero on a fresh install — the command handles this gracefully (prints "Deleted 0 expired revoked_token row(s).").

## Next Recommended Step

Delegate to the Testing Agent to lock cleanup regression coverage (expired rows deleted, non-expired rows preserved, NULL rows preserved, auth/logout baseline still green), then to the Documentation Agent to update ops/deployment docs with the operator invocation path.
