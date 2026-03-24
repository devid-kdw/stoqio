# Frontend Handoff — Wave 1 Phase 10: Stock Overview Value

## Status
Done

## Scope
Extended the Stock Overview tab with two per-item currency columns and a warehouse-total summary card. No other Reports tabs or the export contract were changed.

## Docs Read
- `stoqio_docs/17_UI_REPORTS.md` § 3, § 9, § 10, § 11
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/phase-10-wave-01-stock-overview-value/orchestrator.md`
- `handoff/phase-10-wave-01-stock-overview-value/backend.md`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`

## Files Changed

### `frontend/src/api/reports.ts`
- Added `unit_value: number | null` and `total_value: number | null` fields to `StockOverviewItem`.
- Added new `StockOverviewSummary` interface: `{ warehouse_total_value: number }`.
- Added `summary: StockOverviewSummary` field to `StockOverviewResponse`.

### `frontend/src/pages/reports/reportsUtils.ts`
- Added `formatCurrency(value: number | null): string` helper.
  - Returns `—` only when value is `null`.
  - Returns Croatian-formatted 2-decimal number with ` €` suffix for all numeric values (including zero).

### `frontend/src/pages/reports/ReportsPage.tsx`
- Imported `formatCurrency` from `reportsUtils`.
- Added warehouse-total summary card (`Alert` with `color="blue"`) rendered when `stockOverview` is loaded, above the stock error alert and table. Displays `summary.warehouse_total_value` via `formatCurrency`. Appends a dimmed note when any item in the result has `unit_value === null`.
- Added `Vrijednost / jed.` and `Ukupna vrijednost` column headers to the Stock Overview table.
- Updated empty-state `colSpan` from 12 to 14.
- Added `unit_value` and `total_value` cells per row using `formatCurrency`.

## Commands Run
```
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

## Tests
- Lint: 0 warnings, 0 errors.
- Build: success (tsc + vite, 2.00 s).
- No frontend unit tests exist for this module; verification is lint + type-checked build.

## Open Issues / Risks
- Export endpoints are unchanged per contract; the XLSX/PDF exports do not include the new value columns. If export scope is broadened in a later wave, `report_service.py` and export tests will need updating (logged in backend handoff as well).
- Backend contract matches the brief exactly. No mismatches found.

## Next Recommended Step
Delegate to the Testing Agent to extend backend regression coverage for the value contract.
