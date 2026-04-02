# Backend Agent — Phase 08 Wave 2: Direct Label Printer Support

## Entry: 2026-04-02

---

### Status

Done. All tests pass. Full suite: 425 passed, 0 failed.

---

### Scope

- Added `label_printer_ip`, `label_printer_port`, `label_printer_model` to barcode settings (GET/PUT) and `SystemConfig` defaults.
- Added ZPL II label generation for `zebra_zpl` model.
- Added TCP socket send helper with 5-second timeout.
- Added `POST /api/v1/articles/{id}/barcode/print` and `POST /api/v1/batches/{id}/barcode/print` (ADMIN-only).
- Added `PRINTER_NOT_CONFIGURED`, `PRINTER_UNREACHABLE`, `PRINTER_MODEL_UNKNOWN` to i18n catalog (hr/en/de/hu).
- Updated `seed.py` with new config defaults.
- Existing PDF download endpoints (`GET /api/v1/articles/{id}/barcode`, `GET /api/v1/batches/{id}/barcode`) are untouched.

---

### Docs Read

- `stoqio_docs/13_UI_WAREHOUSE.md` § 7
- `stoqio_docs/18_UI_SETTINGS.md` § 8
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (first 200 lines)
- `backend/app/services/barcode_service.py` (full)
- `backend/app/api/articles/routes.py` (full)
- `backend/app/services/settings_service.py` (barcode section)
- `backend/app/api/settings/routes.py` (barcode endpoints)
- `backend/app/utils/i18n.py` (full)
- `backend/seed.py` (system config section)
- `backend/tests/test_articles.py` (barcode test class)
- `backend/tests/test_settings.py` (barcode settings test)

---

### Files Changed

| File | Change |
|---|---|
| `backend/app/utils/i18n.py` | Added `PRINTER_NOT_CONFIGURED`, `PRINTER_UNREACHABLE`, `PRINTER_MODEL_UNKNOWN` catalog entries in hr/en/de/hu |
| `backend/app/services/settings_service.py` | Added `_DEFAULT_LABEL_PRINTER_IP/PORT/MODEL`, `_ALLOWED_PRINTER_MODELS`, `_parse_label_printer_port()`; extended `get_barcode_settings()` and `update_barcode_settings()` with 3 new fields |
| `backend/app/services/barcode_service.py` | Added `import socket`; added `_generate_zpl()`, `generate_label()`, `_send_to_printer()`, `_get_validated_printer_config()`, `print_article_label()`, `print_batch_label()`, `_LABEL_GENERATORS` dispatch map |
| `backend/app/api/articles/routes.py` | Added `POST /articles/{id}/barcode/print` and `POST /batches/{id}/barcode/print` endpoints (ADMIN-only) |
| `backend/seed.py` | Added `label_printer_ip`, `label_printer_port`, `label_printer_model` to `_seed_system_config()` defaults |
| `backend/tests/test_settings.py` | Updated `test_barcode_settings_get_put_and_validate_format` assertions for new fields; added 3 new tests for label printer settings |
| `backend/tests/test_articles.py` | Added `from unittest.mock import patch` import; added 7 new print endpoint tests inside `TestWarehouseArticles` |

---

### Commands Run

```
cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_settings.py tests/test_i18n.py -q
# 120 passed

cd backend && venv/bin/python -m pytest -q
# 425 passed
```

---

### Tests

**test_settings.py (3 new + 1 updated):**
| Test | Assertion |
|---|---|
| `test_barcode_settings_get_put_and_validate_format` (updated) | New keys present in GET response; port is int |
| `test_barcode_settings_label_printer_fields` | PUT persists ip/port/model; DB values verified |
| `test_barcode_settings_rejects_unknown_printer_model` | 400 VALIDATION_ERROR for `hp_pcl` |
| `test_barcode_settings_rejects_invalid_port` | 400 VALIDATION_ERROR for port=0 |

**test_articles.py (7 new):**
| Test | Assertion |
|---|---|
| `test_print_barcode_endpoints_are_admin_only` | 403 for MANAGER on both print endpoints |
| `test_print_article_barcode_returns_400_when_printer_not_configured` | 400 PRINTER_NOT_CONFIGURED when IP is blank |
| `test_print_batch_barcode_returns_400_when_printer_not_configured` | 400 PRINTER_NOT_CONFIGURED when IP is blank |
| `test_print_article_barcode_returns_400_for_unknown_model` | 400 PRINTER_MODEL_UNKNOWN when model is `hp_pcl` |
| `test_print_article_barcode_returns_502_when_printer_unreachable` | 502 PRINTER_UNREACHABLE when socket.create_connection raises OSError |
| `test_print_article_barcode_success` | 200 `{status: sent, printer_ip, model}`; `_send_to_printer` called once |
| `test_print_batch_barcode_success` | 200 `{status: sent, printer_ip, model}`; `_send_to_printer` called once |

---

### Assumptions

- ZPL field positions (FO offsets) are reasonable defaults for a 100×60mm label; exact layout may need tuning on real hardware.
- Port is stored as a string in `SystemConfig` (consistent with all other config values) and converted to int in `get_barcode_settings()`.
- The `update_barcode_settings` PUT is still a mostly-full-replace: missing `label_printer_*` fields reset to defaults, not to previously saved values. This is consistent with how `barcode_printer` was already handled.
- `barcode_printer` (the legacy OS printer name field) is kept unchanged. The new `label_printer_ip/port/model` fields are for the direct network path.

---

### Open Issues / Risks

- Frontend agent must wire up the two new print endpoints to UI buttons on the article/batch detail views.
- The ZPL label layout (positions, font sizes) uses placeholder values — real Zebra hardware will need field-level validation against the actual label stock size.
- `WAREHOUSE_STAFF` and other non-ADMIN roles are blocked at the route level. No special handling needed.
- `_send_to_printer` sets a 5-second connect+send timeout. Very large labels or slow networks could cause 502 responses that are actually in-progress — acceptable for v1.

---

### Next Recommended Step

Frontend agent: add "Print Label" buttons to article/batch detail pages that call the new `POST /api/v1/articles/{id}/barcode/print` and `POST /api/v1/batches/{id}/barcode/print` endpoints. Expose the new printer config fields in the Settings → Barcode section.
