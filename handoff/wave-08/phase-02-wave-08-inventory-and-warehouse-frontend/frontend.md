## [2026-04-08 16:34] Frontend Agent — Wave 8 Phase 2

Status
- completed

Scope
- Implemented the frontend side of W8-F-001, W8-F-002, W8-F-003, and W8-F-004 in the Warehouse
  and Inventory modules:
  - Warehouse article create/edit now exposes `Prosječna cijena` and sends `initial_average_price`
  - Article detail now preserves and displays `initial_average_price`
  - Opening inventory now supports adding opening batch lines for batch-tracked articles
  - Inventory copy now uses `Šarža` and localizes opening-stock labels to Croatian
  - Completed opening counts now surface `OPENING_STOCK_SET` / `opening_stock_set` when present

Docs Read
- handoff/README.md
- handoff/wave-08/README.md
- handoff/wave-08/phase-01-wave-08-opening-inventory-and-valuation/orchestrator.md
- handoff/wave-08/phase-02-wave-08-inventory-and-warehouse-frontend/orchestrator.md
- handoff/Findings/wave-08-user-feedback.md
- handoff/decisions/decision-log.md
- frontend/src/api/articles.ts
- frontend/src/api/inventory.ts
- frontend/src/pages/warehouse/warehouseUtils.ts
- frontend/src/pages/warehouse/WarehouseArticleForm.tsx
- frontend/src/pages/warehouse/ArticleDetailPage.tsx
- frontend/src/pages/inventory/InventoryCountPage.tsx
- frontend/src/pages/inventory/ActiveCountView.tsx
- frontend/src/pages/inventory/CompletedDetailView.tsx
- frontend/src/pages/inventory/HistoryView.tsx
- frontend/src/pages/inventory/ResolutionBadge.tsx
- stoqio_docs/13_UI_WAREHOUSE.md
- stoqio_docs/16_UI_INVENTORY_COUNT.md

Files Changed
- frontend/src/api/articles.ts
- frontend/src/api/inventory.ts
- frontend/src/pages/warehouse/warehouseUtils.ts
- frontend/src/pages/warehouse/WarehouseArticleForm.tsx
- frontend/src/pages/warehouse/ArticleDetailPage.tsx
- frontend/src/pages/inventory/InventoryCountPage.tsx
- frontend/src/pages/inventory/ActiveCountView.tsx
- frontend/src/pages/inventory/CompletedDetailView.tsx
- frontend/src/pages/inventory/HistoryView.tsx
- frontend/src/pages/inventory/ResolutionBadge.tsx
- stoqio_docs/13_UI_WAREHOUSE.md
- stoqio_docs/16_UI_INVENTORY_COUNT.md

Commands Run
```bash
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run lint
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build
date '+%Y-%m-%d %H:%M'
```

Tests
- Passed: `npm run lint`
- Passed: `npm run build`
- Not run: frontend unit tests

Open Issues / Risks
- Opening batch entry is wired to the Phase 1 contract assumptions (`opening-batch-lines`,
  `initial_average_price`, `OPENING_STOCK_SET`). It will need the backend worker's contract work
  to land in parallel for the full flow to function end-to-end.

Next Recommended Step
- Backend worker finalizes the Phase 1 contract so the new opening-batch UI can hit the live
  endpoint and the opening count summaries/resolutions render end-to-end.
