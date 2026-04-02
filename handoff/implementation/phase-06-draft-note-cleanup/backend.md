## [2026-03-11 21:50] Codex

Status
- completed

Scope
- Removed the legacy `Draft.note` field from the SQLAlchemy model and added a dedicated Alembic migration to drop the column from existing databases.

Docs Read
- `handoff/implementation/phase-05-draft-entry/orchestrator.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`

Files Changed
- `backend/app/models/draft.py`
- `backend/migrations/versions/f3a590393799_remove_legacy_draft_note.py`
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-06-draft-note-cleanup/orchestrator.md`

Commands Run
```bash
date '+%Y-%m-%d %H:%M'
rg -n "Draft\\.note|draft\\.note|\\bnote\\b" backend/app backend/tests handoff stoqio_docs -g '!backend/venv'
```

Tests
- Passed: None
- Failed: None
- Not run: Backend verification is recorded in `testing.md`.

Open Issues / Risks
- Existing PostgreSQL/SQLite databases must run `alembic upgrade head` to apply the drop-column migration.

Next Recommended Step
- Run migration regression and the full backend test suite, then upgrade local databases before manual testing.
