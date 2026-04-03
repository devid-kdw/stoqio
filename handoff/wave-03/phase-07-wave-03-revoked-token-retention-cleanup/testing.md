# Testing Handoff — Wave 3 Phase 7: Revoked Token Retention Cleanup

## Status

Complete.

## Scope

Locked regression coverage for the `flask purge-revoked-tokens` CLI command introduced in
`backend/app/commands.py`. Added 9 new tests to `backend/tests/test_auth.py` covering:

1. Cleanup behaviour — all three retention categories (expired / non-expired / NULL-expiry).
2. Mixed-set selectivity — only expired rows deleted when rows of all three kinds coexist.
3. `--dry-run` — no writes occur; output contains expected markers.
4. Zero-count path — command succeeds cleanly when no expired rows exist.
5. Auth/logout regression locks — revoked-refresh still blocked after purge; logout still
   persists a revoked row with the cleanup command registered.

## Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-008)
- `handoff/README.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md`
- `backend/app/commands.py`
- `backend/app/utils/auth.py`
- `backend/app/models/revoked_token.py`
- `backend/tests/test_auth.py`
- `backend/tests/conftest.py`

## Files Changed

| File | Change |
|------|--------|
| `backend/tests/test_auth.py` | Appended `TestCleanupCommand` class (9 new tests) |

No other files were modified. `testing.md` created (this file).

## Commands Run

```
cd backend && venv/bin/python -m pytest tests/test_auth.py -q
cd backend && venv/bin/python -m pytest -q
```

## Tests

### `tests/test_auth.py` — targeted run

**49 passed, 0 failed** (was 40 before; 9 new tests added by this agent).

### Full backend suite

**464 passed, 0 failed** in 55.93 s.

### New tests and what they lock

| Test | Behaviour locked |
|------|-----------------|
| `test_purge_deletes_expired_rows` | Expired rows (`expires_at < now`) are deleted |
| `test_purge_preserves_non_expired_rows` | Future rows (`expires_at > now`) are preserved |
| `test_purge_preserves_null_expiry_rows` | `expires_at IS NULL` rows are never touched |
| `test_purge_deletes_only_expired_in_mixed_set` | Selectivity across all three kinds simultaneously |
| `test_purge_dry_run_makes_no_writes` | `--dry-run` makes zero DB changes |
| `test_purge_dry_run_reports_correct_count` | `--dry-run` output contains `row(s)` count phrase |
| `test_purge_empty_table_succeeds_with_zero_count` | Command exits 0 with `0` in output when idle |
| `test_revoked_refresh_token_still_rejected_after_purge` | Runtime revocation check still rejects revoked refresh token even after cleanup runs |
| `test_logout_still_persists_revoked_row_after_cleanup_lands` | Logout still writes exactly one revoked_token row with cleanup command registered |

### Testing approach

Tests are driven through Click's `CliRunner` invoking the `purge_revoked_tokens` command
object directly inside an `app.app_context()`. This exercises the real registered CLI path
(`register_commands → app.cli.add_command`) and matches the operator-invoked
`flask purge-revoked-tokens` path exactly. No internal helper functions are tested in
isolation.

## Which cleanup behaviours were explicitly locked

- ✅ Expired rows (`expires_at IS NOT NULL AND expires_at < now`) are removed.
- ✅ Non-expired rows (`expires_at > now`) are preserved.
- ✅ `expires_at IS NULL` rows are preserved.
- ✅ Selectivity holds when all three kinds exist simultaneously.
- ✅ `--dry-run` emits the `[dry-run]` prefix and makes no writes.
- ✅ Zero-count execution path completes without error.

## Which auth/logout regressions were explicitly revalidated

- ✅ `is_token_revoked` / blocklist check still rejects a revoked refresh token (401 TOKEN_REVOKED)
  after `purge-revoked-tokens` has been run.
- ✅ `/api/v1/auth/logout` still persists exactly one `revoked_token` row per logout call
  with `commands.py` registered — confirming `add_to_blocklist` was not altered.

Pre-existing regression suite (40 tests) remained green without modification.

## Open Issues / Risks

- The partial index migration (`e1f2a3b4c5d6_add_revoked_token_expires_at_index.py`) has not
  been applied to any live database yet. `flask db upgrade` is required before first operator
  invocation in production. Tests run on in-memory SQLite which does not enforce this
  migration; schema assertion was omitted intentionally per testing guidance (behavioural
  coverage preferred over schema minutiae).
- Tests use unique, hard-coded JTI strings (e.g. `purge-expired-jti-001`). The session-scoped
  `app` fixture makes the database persistent across tests in the same session. If the suite
  is run more than once in the same Python process (rare with pytest), duplicate JTI inserts
  would fail on the `unique` constraint. This is acceptable under normal CI single-session runs.

## Next Recommended Step

Delegate to the Documentation Agent to update ops/deployment runbook with:
- `flask db upgrade` prerequisite before first purge.
- `flask purge-revoked-tokens` operator invocation path and recommended cron schedule
  (as documented in `backend.md`).
