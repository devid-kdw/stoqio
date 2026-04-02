# Backend Handoff — Wave 3 Phase 1: Runtime Language Switching & Locale Foundation

---

## Entry 1 — 2026-04-02

### Status

Complete. Backend contract was already correct; one targeted test was added to lock canonical round-trip behavior.

### Scope

Audit `default_language` handling across:
- `GET /api/v1/settings/general`
- `GET /api/v1/settings/shell`
- `PUT /api/v1/settings/general`

Confirm no stale serializer path exists. Add a test if needed to lock the cross-endpoint contract.

### Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-001)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-I18N-001)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `backend/tests/conftest.py`

### Audit Results

**`get_general_settings()` (line 615–621 of `settings_service.py`)**
- Calls `_system_config_value("default_language")` which issues a fresh `SystemConfig` query every call.
- No stale path. ✓

**`get_shell_settings()` (line 597–612 of `settings_service.py`)**
- Calls the same `_system_config_value("default_language")` helper.
- No stale path. ✓

**`update_general_settings()` (line 624–651 of `settings_service.py`)**
- Updates `SystemConfig.value` in session via `_set_system_config_value()`.
- Calls `db.session.commit()` before the read-back.
- Returns `get_general_settings()` which re-queries from DB after commit. SQLAlchemy's default `expire_on_commit=True` guarantees the identity map is expired, so the subsequent `filter_by().first()` always reflects the committed value.
- No stale path. ✓

**Conclusion:** The backend contract was already correct. `SystemConfig.default_language` is the single persisted source of truth, and all three endpoints read from it consistently. No code changes were required.

**Test gap identified:**
Existing tests verified `GET /settings/general` returns persisted language, and `PUT /settings/general` saves and echoes the updated language — but no test confirmed `GET /settings/shell` reflects the same updated value after a save. This cross-endpoint round-trip lock was missing.

### Files Changed

- `backend/tests/test_settings.py` — added `test_default_language_canonical_round_trip`

### Commands Run

```
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
```

### Tests

- Before change: 47 passed
- After change: 48 passed (new test: `test_default_language_canonical_round_trip`)
- No failures, no regressions.

`test_default_language_canonical_round_trip` verifies:
1. `PUT /settings/general` with `"en"` returns `default_language == "en"` in the response.
2. `GET /settings/general` immediately after returns `default_language == "en"`.
3. `GET /settings/shell` immediately after returns `default_language == "en"`.

The `reset_settings_state` autouse fixture restores `"hr"` after each test, so this test has full isolation.

### Open Issues / Risks

None. The backend contract is clean. No new cross-agent contract decisions were required.

### Next Recommended Step

Frontend agent may proceed with the runtime language lifecycle work. The backend guarantees:
- `GET /settings/shell` always returns the canonical persisted `default_language`.
- `PUT /settings/general` immediately reflects the updated language in both `GET /settings/general` and `GET /settings/shell` responses in the same request cycle.
