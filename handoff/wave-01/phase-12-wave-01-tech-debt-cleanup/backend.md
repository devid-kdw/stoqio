# Phase 12 Wave 1 — Backend Handoff Log
## Locale-Aware API Error Messages (DEC-I18N-001)

**Date:** 2026-03-24
**Agent:** backend
**Result:** ✅ All 334 tests pass

---

## What was built

### New files

| File | Purpose |
|---|---|
| `backend/app/utils/i18n.py` | Core i18n module: MESSAGES catalog (hr/en/de/hu), `resolve_locale()`, `translate()`, `localize_message()` |
| `backend/app/utils/errors.py` | Shared `api_error()` function imported as `_error` by all route modules |
| `backend/app/api/warehouse/README.md` | Structural placeholder as required by spec |
| `backend/tests/test_i18n.py` | Regression suite: 11 tests covering 404/409 localization and fallback behavior |

### Modified files

**Routes** — removed local `_error()` definitions, replaced with:
```python
from app.utils.errors import api_error as _error
```
Affected: `articles`, `approvals`, `drafts`, `employees`, `inventory_count`, `orders`, `receiving`, `reports`, `settings`, `setup`, `auth` routes.

**Services** — added `_msg_key` to `details` for tested VALIDATION_ERROR sub-cases:
- `article_service.py`: `ARTICLE_DUPLICATE_SUPPLIER_ID`, `ARTICLE_INACTIVE_SUPPLIER`
- `receiving_service.py`: `RECEIVING_NO_LINES`, `RECEIVING_ADHOC_NOTE_REQUIRED`
- `settings_service.py`: `FIELD_REQUIRED`, `FIELD_TOO_LONG` (via `_require_text` helper)
- `order_service.py`: `ORDER_INVALID_VIEW`

**Routes** — added `_msg_key` to VALIDATION_ERROR calls:
- `drafts/routes.py`: `DRAFT_BATCH_ID_REQUIRED`
- `setup/routes.py`: `SETUP_LOCATION_NAME_REQUIRED`, `SETUP_LOCATION_NAME_TOO_LONG`

**Tests** — added `Accept-Language: en` to tests asserting English message content:
- `test_settings.py`, `test_orders.py`, `test_inventory_count.py`, `test_receiving.py`, `test_aliases.py`, `test_setup.py`, `test_articles.py`, `test_drafts.py`

---

## Architecture decisions

### `_msg_key` in details
VALIDATION_ERROR is used for dozens of distinct messages. Since the error code alone cannot select the right catalog entry, service helpers embed `_msg_key` in `details`. The key is prefixed with `_` to signal internal metadata; `api_error()` strips all `_`-prefixed keys before serializing the response.

### Fallback chain
`Accept-Language` header → `SystemConfig.default_language` → `hr` (hard-coded).
Test DB has no SystemConfig row, so tests without `Accept-Language` receive Croatian.

### English `message` parameter is preserved
If a catalog entry exists for the resolved error code (or `_msg_key`), it is used. If no catalog entry is found, `api_error()` falls back to the original English `message` parameter. This means uncatalogued errors still return a useful English message rather than silently losing the text.

---

## Issues encountered and resolved

### Rate limiter in test_i18n.py
Module-scoped fixture meant all `_login()` calls reused the same IP, hitting the rate limiter on the final test. Fixed by giving each test a unique `remote_addr` (127.0.30.1–127.0.30.11).

### Generic VALIDATION_ERROR swallowing specific messages
Three tests checked for content presence in message text (e.g. `"batch_id" in message`). These tests were NOT broken — they were correctly checking meaningful content. The i18n system initially swallowed these specific messages by matching the generic VALIDATION_ERROR catalog entry. Fixed by:
1. Adding specific catalog entries: `DRAFT_BATCH_ID_REQUIRED`, `ARTICLE_DUPLICATE_SUPPLIER_ID`, `ARTICLE_INACTIVE_SUPPLIER`
2. Adding `_msg_key` to the corresponding `_error()` / `raise` call sites
3. Adding `Accept-Language: en` to the test requests (since the tests check English text by substring)

---

## Catalog coverage
All unique error codes used across the codebase are catalogued in `i18n.py`. Dynamic VALIDATION_ERROR sub-cases with tested assertions all have `_msg_key` entries. Untested dynamic VALIDATION_ERROR cases (e.g. inline quantity/field validation in route handlers) continue to fall back to the English `message` parameter — correct behavior, no data loss.

---

## Test results
```
334 passed, 1 warning in 17.63s
```
Including `test_i18n.py`: 11/11 passed (hr, en, de, hu, fallback, complex Accept-Language header).
