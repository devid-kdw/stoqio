## Phase Summary

Phase
- Wave 8 - Phase 2 - Frontend Inventory and Warehouse Opening Setup

Objective
- Remediate frontend portions of W8-F-001, W8-F-002, W8-F-003, and W8-F-004:
  opening inventory UI must support batch setup without price entry, Inventory copy should use
  Croatian `Šarža`, and Warehouse article setup should expose the starting average price entered
  by ADMIN/procurement.

Source Docs
- `handoff/README.md`
- `handoff/wave-08/README.md`
- `handoff/Findings/wave-08-user-feedback.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-008`, `DEC-PRICE-001`, `DEC-PRICE-002`)
- `handoff/wave-08/phase-01-wave-08-opening-inventory-and-valuation/orchestrator.md`
- `frontend/src/api/articles.ts`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/inventory/ActiveCountView.tsx`
- `frontend/src/pages/inventory/CompletedDetailView.tsx`
- `frontend/src/pages/inventory/HistoryView.tsx`
- `frontend/src/pages/inventory/activeCountDisplay.ts`
- `frontend/src/pages/inventory/inventoryFormatters.ts`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`

Contract Locks / Clarifications
- Use the Phase 1 backend contract:
  - Article payload/detail field: `initial_average_price: number | null`.
  - Opening batch endpoint:
    `POST /api/v1/inventory/{count_id}/opening-batch-lines`
    with `{ article_id, batch_code, expiry_date, counted_quantity }`.
    The endpoint returns the refreshed active-count payload.
  - Opening count summaries may include `opening_stock_set`; line resolution may include
    `OPENING_STOCK_SET`.
- Add the starting price field to Warehouse article create/setup, not to opening inventory.
- User-facing label should be Croatian. Prefer `Prosječna cijena` unless implementation discovers
  a stronger local naming pattern.
- Opening inventory should capture physical facts only: article/batch/expiry/quantity.
- Inventory UI must use `Šarža`, not `Serija` or `Batch`, for batch/lot labels.
- Localize visible `Opening Stock` labels to Croatian (for example `Inicijalna inventura`).
- Do not add price inputs to the active opening inventory table.

File Ownership
- `frontend/src/api/articles.ts`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/inventory/*`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `handoff/wave-08/phase-02-wave-08-inventory-and-warehouse-frontend/frontend.md`

Delegation Plan
- Frontend worker implements UI/API/doc updates for inventory and Warehouse article setup.

Acceptance Criteria
- Warehouse article create/edit form supports `Prosječna cijena` / initial average price and sends
  `initial_average_price` to the backend.
- Article detail/read form reflects the existing value without overwriting it unintentionally.
- Opening inventory UI allows adding one or more batch lines for batch-tracked articles that have
  no existing batch rows.
- Opening inventory UI does not ask warehouse staff to enter price.
- Completed and active inventory views use `Šarža` consistently and localize `Opening Stock`.
- Frontend build and lint pass.

Validation Notes
- 2026-04-08: Orchestrator created Wave 8 Phase 2 from user feedback intake.

Next Action
- Frontend worker implements and records `frontend.md`.

---

## Delegation Prompt - Frontend Worker

You are the frontend worker for STOQIO Wave 8 Phase 2.

Read the files listed above before editing. You are not alone in the codebase: a backend worker is
editing the Phase 1 backend contract in parallel, and another frontend worker owns Orders/Settings.
Do not edit Orders or Settings files. Do not revert or overwrite unrelated changes.

Implement the frontend side of the Phase 1 contract as described here. Run `npm run build` and
`npm run lint` if feasible. Write your handoff entry to
`handoff/wave-08/phase-02-wave-08-inventory-and-warehouse-frontend/frontend.md` using the standard
agent template.
