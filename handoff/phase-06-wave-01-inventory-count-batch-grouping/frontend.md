# Frontend Handoff — Wave 1 Phase 6 Inventory Count Batch Grouping

Reserved for frontend agent entries. Append only.

---

## Entry — 2026-03-24

### Status
Done.

### Scope
Active Inventory Count table: rename batch column header to `Batch`, restructure batch-tracked articles into expandable parent rows with per-batch child rows, preserve autosave / progress / filter semantics.

### Docs Read
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/phase-06-wave-01-inventory-count-batch-grouping/orchestrator.md`
- `handoff/phase-12-inventory-count/orchestrator.md`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `frontend/src/api/inventory.ts`

### Files Changed
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
  - Added `useMemo` to React imports.
  - Added `IconChevronDown`, `IconChevronRight` to tabler-icons import.
  - Added module-level types: `BatchGroup`, `ActiveDisplayItem`, `FilteredDisplayItem`.
  - Added `expandedArticles: Set<number>` state and `toggleArticle` helper inside `ActiveCountView`.
  - Added `allDisplayItems` (memoised on `lines`): builds an ordered list of `non-batch` and `batch-group` items from the flat `count.lines` array, grouping batch lines by `article_id` while preserving original backend order.
  - Replaced `displayLines` filter with `filteredDisplayItems` loop: filters leaf rows, keeps a `batch-group` item only when at least one child line survives the active filter.
  - Replaced flat table body render with `flatMap` over `filteredDisplayItems`:
    - `non-batch` items: identical row shape to original.
    - `batch-group` items: one parent row (chevron, article_no, description, "N batches / X.XX UOM total" summary, no qty input) + per-child rows when expanded (batch_code, expiry_date, system_qty, uom, qty input, difference).
  - Renamed active-table column header `Serija` → `Batch`.
  - Progress counting (`countedCount`, `allCounted`, `{X} / {Y} prebrojano`) unchanged — already operated on the flat `lines` leaf array.
  - Autosave (`handleBlur`) unchanged — still PATCHes by `line_id`.
  - Extracted `renderCountedQtyInput` and `renderDiff` helpers to reduce duplication between non-batch and child rows.

### Commands Run
- `cd frontend && npm run lint` — passed, 0 warnings
- `cd frontend && npm run build` — passed, 0 errors

### Tests
None required by scope (no test agent delegation for this phase).

### Open Issues / Risks
None. Scope is frontend-only; no backend changes made.

### Next Recommended Step
Orchestrator validation and formal phase closeout.
