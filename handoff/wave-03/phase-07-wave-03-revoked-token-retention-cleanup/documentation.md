# Documentation Handoff — Wave 3 Phase 7: Revoked Token Retention Cleanup

### 2026-04-03 16:19:03 CEST

## Status

Complete.

## Scope

Updated the repo's deployment-facing documentation so operators can discover and run the explicit expired revoked-token cleanup path that landed in backend. Documented the exact Flask CLI command, the `--dry-run` preview, when operators should run it in a local-host deployment, the migration prerequisite, and the fact that cleanup removes only expired revoked rows without weakening active revocation.

## Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-008`)
- `handoff/README.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `scripts/deploy.sh`
- `backend/app/commands.py`
- `backend/app/__init__.py`

## Files Changed

| File | Change |
|------|--------|
| `README.md` | Added a local-host maintenance section with the explicit `venv/bin/flask purge-revoked-tokens` operator path and safety notes |
| `stoqio_docs/07_ARCHITECTURE.md` | Added auth-architecture note plus a local-server runbook subsection covering cleanup semantics, when to run it, and one practical cron example |
| `stoqio_docs/05_DATA_MODEL.md` | Added a `RevokedToken` retention note documenting the explicit cleanup contract and preserved revocation semantics |
| `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/documentation.md` | Created this documentation-agent handoff log |

## Commands Run

```bash
git status --short
rg --files handoff | rg 'phase-07-wave-03-revoked-token-retention-cleanup|README.md|decision-log.md'
rg -n "revoked token|revoked-token|cleanup" handoff README.md stoqio_docs scripts backend frontend -g '!node_modules'
sed -n '1,240p' /Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md
sed -n '1,260p' handoff/README.md
sed -n '1,260p' handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md
sed -n '1,260p' handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md
sed -n '1,260p' handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md
sed -n '1,260p' README.md
sed -n '260,430p' stoqio_docs/07_ARCHITECTURE.md
sed -n '430,560p' stoqio_docs/05_DATA_MODEL.md
sed -n '1,260p' scripts/deploy.sh
sed -n '1,240p' backend/app/commands.py
sed -n '1,220p' backend/app/__init__.py
cd backend && venv/bin/flask --help
cd backend && venv/bin/flask purge-revoked-tokens --help
cd backend && venv/bin/flask purge-revoked-tokens --dry-run
git diff -- README.md stoqio_docs/07_ARCHITECTURE.md stoqio_docs/05_DATA_MODEL.md
```

## Tests

No documentation-owned automated tests.

Manual verification performed:
- Confirmed `backend/app/commands.py` defines `purge-revoked-tokens` and that `backend/app/__init__.py` registers it through `register_commands(app)`.
- Confirmed the root/backend CLI exposes the command with `cd backend && venv/bin/flask purge-revoked-tokens --help`.
- Ran `cd backend && venv/bin/flask purge-revoked-tokens --dry-run` against the local backend environment; it completed successfully and reported `[dry-run] 3 expired revoked_token row(s) would be deleted.`.
- Confirmed backend/testing handoffs match the documented operator path and cover the destructive path plus auth-regression behavior.

## Open Issues / Risks

- The actual delete path (`venv/bin/flask purge-revoked-tokens` without `--dry-run`) was intentionally not run manually during documentation work because it mutates the local database. Destructive behavior is covered by the backend/testing delivery for this phase.
- The scheduling example uses Linux cron because the repo's deployment model is local-host Linux/systemd. Operators on other local-host environments should use an equivalent scheduler while keeping the same backend command path.

## Next Recommended Step

Have the orchestrator review the doc wording against the backend/testing handoffs, then append validation notes to `orchestrator.md` and close the phase.
