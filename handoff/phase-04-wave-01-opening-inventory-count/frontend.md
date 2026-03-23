# Frontend Handoff — Wave 1 Phase 4 Opening Inventory Count

Reserved for frontend agent entries. Append only.

---

## Entry — 2026-03-23

### Status
Complete. All tasks implemented and verified.

### Scope
- Added `InventoryCountType` export to `frontend/src/api/inventory.ts`.
- Added `type: InventoryCountType` to `ActiveCount`, `HistoryItem`, and `CountDetail` interfaces.
- Added `opening_count_exists: boolean` to `HistoryResponse`.
- Extended `inventoryApi.start(...)` to accept an optional `type` and pass it in the POST body.
- Added `openingCountExists` state to `InventoryCountPage`; set from `data.opening_count_exists` in `loadHistory`.
- Replaced the flat `handleStart` in `HistoryView` with a `doStart(type)` function and a `handleStart` dispatcher:
  - `openingCountExists === false` → opens type-selection modal with "Opening Stock Count" / "Regular Count" buttons.
  - `openingCountExists === true` → directly calls `doStart('REGULAR')` with no modal.
  - Backend 400 on `OPENING` start → shown inline inside the modal (not fatal, not toast).
  - Network/server error → closes modal and delegates to `onFatalError()` as before.
- Added type-selection modal to `HistoryView` JSX.
- Added "Opening Stock" badge (`color="violet"`) in history table rows next to the "ZAVRŠENA" badge for items with `type === 'OPENING'`.
- Added "Opening Stock" badge in `ActiveCountView` header when `count.type === 'OPENING'`.
- Added "Opening Stock" badge in `CompletedDetailView` header when `count.type === 'OPENING'`.
- All existing `runWithRetry` / `onFatalError` semantics preserved unchanged.

### Docs Read
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` (§ 4, § 5)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-INV-001 through DEC-INV-007)
- `handoff/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- `handoff/phase-04-wave-01-opening-inventory-count/backend.md`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

### Files Changed
- `frontend/src/api/inventory.ts` — added `InventoryCountType`, `type` fields, `opening_count_exists`, extended `start(...)`
- `frontend/src/pages/inventory/InventoryCountPage.tsx` — type-selection modal, badge rendering, `openingCountExists` state wiring

### Commands Run
- `cd frontend && npm run lint` → clean (no output, exit 0)
- `cd frontend && npm run build` → success, built in 1.99s

### Tests
- Lint: clean.
- Build: all 7067 modules transformed, no TS or ESLint errors.

### Open Issues / Risks
- **Backend contract matches orchestrator brief exactly.** No divergence found. The backend agent's `GET /api/v1/inventory` response includes `opening_count_exists`, and every count-shaped response includes `type`, matching the types added here.
- Safe default for `openingCountExists` is `true` (prevents false modal display before first `loadHistory` resolves). By the time `HistoryView` renders, `loadHistory` has always completed successfully, so this default is only a guard.

### Next Recommended Step
- Testing agent: extend `test_inventory_count.py` per the testing delegation prompt and reverify `test_phase2_models.py`.
