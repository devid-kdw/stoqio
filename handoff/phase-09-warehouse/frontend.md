## 2026-03-13 17:05:39 CET

### Status
Completed

### Scope
Implemented the Phase 9 Warehouse frontend for ADMIN and MANAGER: real `/warehouse` list and `/warehouse/articles/:id` detail routes, Warehouse article list/detail/create/update/deactivate/transactions/lookups API usage, admin-only create/edit/deactivate actions, manager read-only behavior, disabled barcode control, and Warehouse-specific form/list/detail UI.

Preserved the Draft Entry / Receiving article lookup path explicitly by leaving `articlesApi.lookup(q)` on the existing exact-match `GET /api/v1/articles?q={query}` contract and adding separate Warehouse methods in `frontend/src/api/articles.ts` (`listWarehouse`, `getDetail`, `create`, `update`, `deactivate`, `listTransactions`, `lookupCategories`, `lookupUoms`). The Warehouse pages always call list mode with explicit `page` and `per_page`, so they do not reuse or repurpose the compatibility lookup.

### Docs Read
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.1, § 4, § 5
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-WH-001`, `DEC-WH-002`, `DEC-WH-003`)
- `handoff/README.md`
- `handoff/phase-09-warehouse/orchestrator.md`
- `handoff/phase-09-warehouse/backend.md`

### Files Changed
- `frontend/src/api/articles.ts`
- `frontend/src/routes.tsx`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `handoff/phase-09-warehouse/frontend.md`

### Commands Run
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

### Tests
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

### Open Issues / Risks
- None

### Next Recommended Step
- Testing agent should verify the Warehouse flows against the live Phase 9 backend with ADMIN and MANAGER accounts, including the preserved Draft Entry / Receiving `articlesApi.lookup()` compatibility path and the disabled Phase 9 barcode affordance.
