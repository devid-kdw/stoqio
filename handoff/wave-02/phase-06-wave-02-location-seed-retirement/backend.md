# Backend Handoff - Phase 06 Wave 02 Location Seed Retirement

Reserved for backend agent entries. Append only.

## 2026-04-02 Backend Agent

Status
- completed

Scope
- Retire the obsolete location-seeding helper, update the affected handoff/review markdown, and record the cleanup in the wave 2 phase 6 handoff trail.

Docs Read
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-024`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-003`)
- `handoff/implementation/phase-04-first-run-setup/orchestrator.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `handoff/wave-02/phase-06-wave-02-location-seed-retirement/orchestrator.md`
- `backend/seed.py`

Files Changed
- `backend/seed_location.py` [DELETED] - retired the obsolete bootstrap helper so it can no longer seed or preserve a current-install `Location` row.
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` [MODIFIED] - converted `F-024` to past tense and noted that the helper has been retired.
- `handoff/implementation/phase-03-authentication/testing.md` [MODIFIED] - added a supersession note and removed current instructions to run `seed_location.py`.
- `handoff/implementation/phase-03-authentication/verification_commands.md` [MODIFIED] - replaced obsolete seed-helper instructions with the current supported setup path.
- `handoff/implementation/phase-03-authentication/backend.md` [MODIFIED] - added a supersession note so the historical closure log stays honest.
- `handoff/implementation/phase-03-authentication/orchestrator.md` [MODIFIED] - updated validation/live-environment notes to reflect that the helper is retired.
- `handoff/decisions/decision-log.md` [MODIFIED] - added a narrow baseline clarification that the supported initial-location path is `/setup`, while `seed_location.py` is now retired.
- `handoff/wave-02/phase-06-wave-02-location-seed-retirement/orchestrator.md` [MODIFIED] - updated the phase state from planned cleanup to completed cleanup.

Commands Run
```bash
rg -n "seed_location\\.py|python seed_location|seed location" handoff stoqio_docs docs memory README.md backend -g '!backend/venv/**'
cd backend && venv/bin/python -m pytest tests/test_setup.py tests/test_auth.py -q
```

Tests
- Passed: `tests/test_setup.py` and `tests/test_auth.py`
- Passed: repo-wide search confirmed no remaining current instruction path points to `seed_location.py`
- Failed: None

Open Issues / Risks
- Historical Phase 3 artifacts still mention the helper in supersession context, but they no longer present it as a supported current-install path.

Next Recommended Step
- No further work required for this cleanup scope.
