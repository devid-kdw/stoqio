## 2026-03-14 20:40:22 CET

### Status
- Completed.

### Scope
- Replaced the Warehouse article-detail Phase 9 barcode placeholder with a live ADMIN-only `Ispis barkoda` action.
- Added the article barcode PDF download helper to the frontend articles API using the existing browser blob-download pattern already used for Orders and Reports.
- Preserved MANAGER read-only behavior and left batch-level barcode UI out of scope for this Phase 15 frontend pass.

### Docs Read
- `stoqio_docs/13_UI_WAREHOUSE.md` § 5, § 7, § 8, § 9
- `stoqio_docs/19_IMPLEMENTATION_PLAN.md` § Phase 15 — Barcodes & Export
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-09-warehouse/orchestrator.md`
- `handoff/phase-14-settings/orchestrator.md`
- `handoff/phase-15-barcodes-export/backend.md`

### Files Changed
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/utils/http.ts`
- `handoff/phase-15-barcodes-export/frontend.md`

### Commands Run
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

### Tests
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

### Open Issues / Risks
- Browser handling of the generated PDF still depends on local browser settings; this Phase 15 frontend intentionally hands the PDF off through the existing download flow and does not implement direct OS-printer integration.
- `frontend/src/utils/http.ts` now includes async blob-error parsing so barcode endpoint business errors returned as JSON blobs can still surface as translated Warehouse toasts. Existing Orders/Reports export handlers still use their prior generic fallback behavior.

### Next Recommended Step
- Run an orchestrator/manual smoke check with an ADMIN account against the live backend barcode endpoint, including one article that already has an alphanumeric barcode under `Code128` and one `EAN-13` validation-failure case, to confirm the browser download path and toast behavior end to end.
