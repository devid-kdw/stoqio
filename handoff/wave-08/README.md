# Wave 8 Handoffs

This folder stores Wave 8 user-feedback remediation handoff folders.

Use the existing `handoff/README.md` protocol and create one subfolder per phase in the format:

- `phase-NN-wave-08-*`

## Wave 8 Purpose

Wave 8 addresses user feedback collected on 2026-04-08 in:

- `handoff/Findings/wave-08-user-feedback.md`

This wave is a product-behavior and localization correction wave. Every change must be traceable
to one or more `W8-F-*` findings. Scope creep is not permitted.

## Phases

| Phase | Owner | Primary Findings | Can run in parallel |
|-------|-------|------------------|---------------------|
| `phase-01-wave-08-opening-inventory-and-valuation` | Backend | W8-F-001, W8-F-003, W8-F-004 | Yes |
| `phase-02-wave-08-inventory-and-warehouse-frontend` | Frontend | W8-F-001, W8-F-002, W8-F-003, W8-F-004 | Yes, after using Phase 1 contract |
| `phase-03-wave-08-orders-and-settings-frontend` | Frontend | W8-F-005, W8-F-006 | Yes |

## File Ownership Per Phase

- Phase 1 backend:
  - `backend/app/models/article.py`
  - `backend/app/models/enums.py`
  - `backend/app/models/inventory_count.py`
  - `backend/app/services/article_service.py`
  - `backend/app/services/inventory_service.py`
  - `backend/app/services/report_service.py`
  - `backend/app/api/inventory_count/routes.py`
  - `backend/migrations/versions/*.py` (new migrations only)
  - `backend/tests/test_articles.py`
  - `backend/tests/test_inventory_count.py`
  - `backend/tests/test_reports.py`
  - `stoqio_docs/05_DATA_MODEL.md`
- Phase 2 frontend:
  - `frontend/src/api/articles.ts`
  - `frontend/src/api/inventory.ts`
  - `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
  - `frontend/src/pages/warehouse/warehouseUtils.ts`
  - `frontend/src/pages/warehouse/WarehousePage.tsx`
  - `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
  - `frontend/src/pages/inventory/*`
  - `stoqio_docs/13_UI_WAREHOUSE.md`
  - `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- Phase 3 frontend:
  - `frontend/src/api/orders.ts`
  - `frontend/src/pages/orders/OrdersPage.tsx`
  - `frontend/src/pages/orders/OrderDetailPage.tsx` (only if the same add-line bug exists there)
  - `frontend/src/pages/orders/orderUtils.ts`
  - `frontend/src/pages/orders/__tests__/*`
  - `frontend/src/pages/settings/SettingsPage.tsx`
  - `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`
  - `stoqio_docs/18_UI_SETTINGS.md`

If implementation proves a phase needs a file outside its ownership list, the agent must document
why in its handoff entry.

## Finding Reference

| ID | Description | Phase |
|----|-------------|-------|
| W8-F-001 | Opening inventory completion records initial stock as surplus | 1, 2 |
| W8-F-002 | Completed inventory uses `Serija` instead of `Šarža` | 2 |
| W8-F-003 | Opening inventory needs a way to enter existing batches for batch-tracked articles | 1, 2 |
| W8-F-004 | Initial purchase/average price is missing when creating articles and opening stock | 1, 2 |
| W8-F-005 | Purchase order article selection does not autofill supplier article code | 3 |
| W8-F-006 | Settings section titles are still in English | 3 |

## Local Data Reset

The user also requested a local dev database reset so existing article stock quantities return to
zero, surplus rows created by the bad opening-inventory run are removed, and the opening inventory
record is cleared so the fixed flow can be tested again. The orchestrator handles this separately
from implementation and records the command/results in the final closeout.
