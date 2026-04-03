# Backend Handoff — Wave 3 Phase 6 — Backend Helper & Numbering Deduplication

## Status

Done.

## Scope

- Removed duplicated `_parse_positive_int` / `_parse_bool` implementation logic from `report_service.py`. Both helpers are now thin service-layer adapters that delegate to the shared `app.utils.validators` helpers and convert `QueryValidationError` → `ReportServiceError` to preserve the existing route contract.
- Extracted the shared `IZL-####` DraftGroup numbering helper into a new module `app/utils/draft_numbering.py`. Both previous duplicate implementations (`_next_draft_group_number` in `drafts/routes.py` and `_next_group_number` in `inventory_service.py`) have been removed and replaced with calls to `next_izl_group_number()`.

## Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-006, W3-007)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-004, DEC-INV-001, DEC-INV-005, DEC-BE-013)
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/orchestrator.md`
- `backend/app/utils/validators.py`
- `backend/app/services/report_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`

## Files Changed

### New file

- `backend/app/utils/draft_numbering.py` — single source of `next_izl_group_number()`. Encodes the accepted semantics from DEC-BE-004 and DEC-INV-001: scan all `DraftGroup.group_number` values, ignore non-matching strings (e.g. `IZL-LEGACY-*`), take max matching numeric suffix, format as `IZL-{n+1:04d}`. Both DAILY_OUTBOUND and INVENTORY_SHORTAGE groups share this sequence.

### Modified files

**`backend/app/services/report_service.py`**

Added imports:
```python
from app.utils.validators import QueryValidationError, parse_bool_query, parse_positive_int
```

Changed `_parse_positive_int` and `_parse_bool` from standalone implementations to thin service-layer adapters:

| Helper | Strategy |
|---|---|
| `_parse_positive_int` | Normalizes `""` → `None`, then delegates to `parse_positive_int()`; catches `QueryValidationError` and re-raises as `ReportServiceError` with `{"field": ..., "value": ...}` details. |
| `_parse_bool` | Normalizes `""` → `None`, then delegates to `parse_bool_query()`; catches `QueryValidationError` and re-raises as `ReportServiceError` with `{"field": ..., "value": ...}` details. |

Why this preserves semantics:
- The `""` → `None` normalization ensures blank query strings continue to fall back to their defaults, matching the old `value in (None, "")` guard exactly.
- The shared helpers produce identical error message strings (`"{field} must be a valid integer."`, `"{field} must be greater than zero."`, `"{field} must be 'true' or 'false'."`), so the converted `ReportServiceError` carries the same user-visible message.
- `QueryValidationError` never escapes `report_service.py`; routes still only see `ReportServiceError`.

Call sites that changed (all within `report_service.py`, caller-visible behavior unchanged):
- `_transaction_base_query()`: `_parse_positive_int(article_id, field_name="article_id", default=0)`
- `get_transaction_log()`: `_parse_positive_int(page, ...)` and `_parse_positive_int(per_page, ...)`
- `get_stock_overview()`: `_parse_bool(reorder_only, field_name="reorder_only", default=False)`

**`backend/app/api/drafts/routes.py`**

- Removed `import re`
- Removed `_DRAFT_GROUP_NUMBER_RE = re.compile(r"^IZL-(\d+)$")`
- Removed `_next_draft_group_number()` function
- Added `from app.utils.draft_numbering import next_izl_group_number`
- Replaced `_next_draft_group_number()` call in `_get_or_create_draft_group()` with `next_izl_group_number()`

**`backend/app/services/inventory_service.py`**

- Removed `import re`
- Removed `_GROUP_NUMBER_RE = re.compile(r"^IZL-(\d+)$")`
- Removed `_next_group_number()` function
- Added `from app.utils.draft_numbering import next_izl_group_number`
- Replaced `_next_group_number()` call in `complete_count()` with `next_izl_group_number()`

## Commands Run

```
rg -n 'def _parse_positive_int|def _parse_bool' backend/app/services/report_service.py
# → both names still present (thin wrappers), no standalone implementation logic

rg -n '_next_draft_group_number|_next_group_number' backend/app -g '*.py'
# → no output (both old helpers fully removed)

cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_drafts.py tests/test_inventory_count.py -q
# → 125 passed in 2.41s

cd backend && venv/bin/python -m pytest -q
# → 450 passed in 62.79s
```

## Tests

- Targeted suite (reports + drafts + inventory count): **125 passed**
- Full backend suite: **450 passed**

## Open Issues / Risks

**Test gaps for the testing agent to lock:**

1. **Report blank-string/default behavior**: No existing test explicitly sends `page=""`, `per_page=""`, or `reorder_only=""` to confirm the blank-string → default behavior still holds after the adapter change. The testing agent should add coverage for these cases against the live route (not just the service internals).

2. **Invalid-value error contract through adapter**: No existing test asserts that passing an invalid non-empty value (e.g. `page=abc`) returns `{"error": "VALIDATION_ERROR"}` with status 400 from the Reports API. This is implicitly exercised but not explicitly locked.

3. **Cross-caller IZL sequence**: No existing test explicitly verifies that an inventory-shortage group creation uses a sequence number that is one higher than the last daily-outbound group (or vice versa). `test_group_number_uses_max_existing_suffix_not_id` exists for the draft path. The testing agent should add a cross-caller sequence test.

No circular import risk was identified: `app.utils.draft_numbering` imports only from `app.extensions` and `app.models.draft_group`, which both modules already imported before this change.

## Next Recommended Step

Delegate to the testing agent with the test gaps listed above as minimum required coverage.
