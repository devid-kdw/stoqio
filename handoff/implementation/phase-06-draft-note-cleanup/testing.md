## [2026-03-11 21:50] Codex

Status
- completed

Scope
- Revalidate that the head schema no longer contains `draft.note` and that backend regression tests still pass after the cleanup.

Docs Read
- `handoff/README.md`
- `backend/tests/test_phase2_models.py`

Files Changed
- `backend/tests/test_phase2_models.py`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_phase2_models.py -q
backend/venv/bin/pytest backend/tests/test_drafts.py backend/tests/test_approvals.py -q
backend/venv/bin/pytest backend/tests -q
```

Tests
- Passed: `backend/tests/test_phase2_models.py -q` (`2 passed`), `backend/tests/test_drafts.py backend/tests/test_approvals.py -q` (`45 passed`), `backend/tests -q` (`92 passed`)
- Failed: None
- Not run: None

Open Issues / Risks
- Existing dev/prod databases still need the new Alembic upgrade before manual runtime verification, otherwise they will retain the legacy `draft.note` column until upgraded.

Next Recommended Step
- Apply `alembic upgrade head` anywhere the project is already using a pre-cleanup database.
