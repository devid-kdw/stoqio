## 2026-03-14 20:35:09 CET

### Status
- Completed.

### Scope
- Implemented Phase 15 backend barcode PDF generation for article and batch labels under a new `barcode_service`.
- Replaced the Phase 9 article barcode `501` scaffold and added the new ADMIN-only batch barcode download route.
- Hardened Reports export formatting/tests so Excel exports verify sheet names, headers, data rows, widths, and filenames, while PDF exports verify title/subtitle/orientation inputs through service-level coverage.
- Logged the Phase 15 contract resolutions for batch label count, missing barcode persistence, and the current Reports `export_format` limitation.

### Docs Read
- `stoqio_docs/19_IMPLEMENTATION_PLAN.md` § Phase 15
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 2.4, § 3
- `stoqio_docs/05_DATA_MODEL.md` § 2, § 7, § 15
- `stoqio_docs/13_UI_WAREHOUSE.md` § 5, § 7, § 9
- `stoqio_docs/17_UI_REPORTS.md` § 6, § 8, § 10
- `stoqio_docs/18_UI_SETTINGS.md` § 8, § 9
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 1.4, § 4
- `stoqio_docs/07_ARCHITECTURE.md` § 1, § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/implementation/phase-14-settings/orchestrator.md`

### Files Changed
- `backend/app/services/barcode_service.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_reports.py`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-15-barcodes-export/backend.md`

### Commands Run
- `backend/venv/bin/python -m py_compile backend/app/services/barcode_service.py backend/app/api/articles/routes.py backend/app/services/report_service.py backend/tests/test_articles.py backend/tests/test_reports.py`
- `backend/venv/bin/pytest backend/tests/test_articles.py -q`
- `backend/venv/bin/pytest backend/tests/test_reports.py -q`
- `backend/venv/bin/pytest backend/tests -q`

### Tests
- `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `26 passed`
- `backend/venv/bin/pytest backend/tests/test_reports.py -q` -> `27 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `251 passed`

### Open Issues / Risks
- `DEC-BE-010` locks the v1 batch barcode route to one label per batch because `Receiving.barcodes_printed` is receiving-scoped, ambiguous across multiple receipts, and currently never populated by the receiving flow.
- `DEC-BE-011` means existing imported alphanumeric barcode values remain printable with `Code128`, but ADMIN receives `INVALID_BARCODE_VALUE` if `EAN-13` is selected for a stored barcode that cannot be represented as EAN without inventing a new persisted value.
- `DEC-REP-002` leaves Reports Excel exports on the current generic contract even when Settings persist `export_format = sap`; SAP-specific sheet/column mapping still needs a documented follow-up spec.
- Direct OS printer integration remains intentionally unimplemented in Phase 15; barcode printing is download/open/print of generated PDFs only.

### Next Recommended Step
- Frontend/orchestrator follow-up should wire the Warehouse barcode actions to the now-live PDF download routes, keep direct printing out of scope, and decide whether a post-v1 receiving-level multi-label print workflow or a fully specified SAP export profile is needed next.
