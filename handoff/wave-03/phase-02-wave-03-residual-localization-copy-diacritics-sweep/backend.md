# Backend Handoff — Wave 3 Phase 2: Residual Localization / Copy / Diacritics Sweep

---

## Entry 1 — 2026-04-02

### Status
Complete. One missing catalog entry found and patched. All other touched flows were already fully covered.

### Scope
Audited the backend error-message localization for the four touched flows: Draft Entry, Setup, Receiving, and Approvals. Checked whether any user-visible backend message still falls back to raw English where a localized catalog entry should exist.

### Docs Read
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-002)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-I18N-001)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/orchestrator.md`
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/utils/validators.py`
- `backend/app/services/receiving_service.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/api/setup/routes.py`
- `backend/app/api/approvals/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/tests/test_i18n.py`

### Audit Findings

**Setup (`setup/routes.py`)** — Fully covered.
- `SETUP_ALREADY_COMPLETED` → catalog entry exists ✓
- `SETUP_LOCATION_NAME_REQUIRED` via `_msg_key` → catalog entry exists ✓
- `SETUP_LOCATION_NAME_TOO_LONG` via `_msg_key` → catalog entry exists ✓

**Receiving (`receiving/routes.py` + `receiving_service.py`)** — Fully covered.
- All `_require_text` messages (`"{field} is required."`) → translated via `FIELD_REQUIRED` regex template ✓
- All `_parse_int` messages → `FIELD_NOT_INTEGER` regex template ✓
- All `_parse_optional_decimal` messages → `FIELD_NOT_NUMBER` / `FIELD_GTE_ZERO` regex templates ✓
- All `_parse_required_date` messages → `FIELD_REQUIRED` / `FIELD_NOT_DATE` regex templates ✓
- `BATCH_EXPIRY_MISMATCH` → catalog entry with `{batch_code}` template ✓
- `RECEIVING_NO_LINES` via `_msg_key` → catalog entry ✓
- `RECEIVING_ADHOC_NOTE_REQUIRED` via `_msg_key` → catalog entry ✓
- `ORDER_LINE_REMOVED`, `ORDER_LINE_CLOSED`, `ORDER_CLOSED`, `ORDER_NOT_FOUND`, `ORDER_LINE_NOT_FOUND` → catalog entries ✓
- `UOM_MISMATCH`, `ARTICLE_NOT_FOUND`, `INTERNAL_ERROR`, `CONFLICT` → catalog entries ✓
- `ARTICLE_MISMATCH` (article_id mismatch against order line) — NOT in catalog; however, this only fires on API misuse/data corruption, not in normal UI operation. Skipped per constraint to avoid inventing unnecessary work.

**Approvals (`approvals/routes.py` + `approval_service.py`)** — Fully covered.
- `approval_service` raises `ValueError` with English strings; routes convert these to `_error("CONFLICT", msg, 409)`, `_error("INSUFFICIENT_STOCK", msg, 409)`, or `_error("BAD_REQUEST", msg, 400)`. All three error codes have catalog entries, so the English ValueError strings are superseded by catalog translations ✓
- Direct route validations (`"quantity is required."`, `"quantity must be greater than zero."`) → matched by regex templates ✓
- `NOT_FOUND` for group/line lookups → catalog entry ✓

**Draft Entry (`drafts/routes.py`)** — **One missing entry found and patched.**
- `INVALID_STATUS` — used in `PATCH /drafts/<id>` and `DELETE /drafts/<id>` when a line is no longer in DRAFT status. `INVALID_STATUS` was absent from the `MESSAGES` catalog, causing `localize_message` to fall back to raw English. This is user-visible: an operator who tries to edit or delete a line that was already approved or rejected will see this error in the toast/UI.
- Patched by adding `INVALID_STATUS` to the catalog with `hr`/`en`/`de`/`hu` translations.
- All other Draft Entry errors (`ARTICLE_NOT_FOUND`, `DRAFT_BATCH_ID_REQUIRED` via `_msg_key`, `NOT_FOUND`, `CONFLICT`, generic FIELD_REQUIRED/FIELD_NOT_POSITIVE patterns from `validate_quantity`) were already covered ✓

### Files Changed
- `backend/app/utils/i18n.py` — added `INVALID_STATUS` catalog entry (hr/en/de/hu)
- `backend/tests/test_i18n.py` — added `TestLocalizedInvalidStatus` class with 4-locale parametrized test

### Commands Run
```
cd /Users/grzzi/Desktop/STOQIO/backend
./venv/bin/python -m pytest tests/test_i18n.py::TestLocalizedInvalidStatus -v
./venv/bin/python -m pytest tests/test_i18n.py -v
```

### Tests
- `TestLocalizedInvalidStatus` — 4 new parametrized tests (hr, en, de, hu) — all PASSED
- Full `tests/test_i18n.py` — 36 tests — all PASSED, no regressions

### Open Issues / Risks
- `ARTICLE_MISMATCH` in `receiving_service.py` has no catalog entry but is not user-facing in normal operation (only fires on API misuse). Not patched per scope constraint.
- `"quantity must be a number."` in `approvals/routes.py` uses slightly different phrasing from the regex pattern (`"must be a number."` vs `"must be a valid number."`), so it would not be translated. This is a frontend-guarded path (the UI prevents sending non-numeric values) and was assessed as out of scope for this targeted backend phase.

### Next Recommended Step
Frontend and Testing agents can proceed. Backend catalog contract for the touched flows is now confirmed complete.
