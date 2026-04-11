# Wave 9 Phase 4 — Frontend Handoff

## Status

Complete — all four findings implemented, tests pass, lint clean, build green.

## Scope

Implemented the frontend side of W9-F-005, W9-F-008, W9-F-009, and W9-F-010:

- **W9-F-008**: All Statistics subsections (`Top 10 po potrošnji`, `Ulaz i izlaz kroz vrijeme`, `Sažetak zona naručivanja`, `Osobna izdavanja`, `Kretanje cijena`) start collapsed by default and open on click using `UnstyledButton` + Mantine `Collapse`. No single-open accordion restriction.
- **W9-F-009**: Reorder-zone drilldown now stays inside the `Statistike` tab. Clicking a zone calls `GET /api/v1/reports/statistics/reorder-drilldown?status=RED|YELLOW|NORMAL` and renders the result as a separate collapsible block within Statistike (locked Option 2). The old `setActiveTab('stock')` + `setStockZoneFilter()` pattern was removed from `handleReorderDrilldown`.
- **W9-F-010**: Movement chart helper note is now hardcoded Croatian client-side (`Količine su zbrojene po svim mjernim jedinicama. Grafikon prikazuje trendove, a ne precizne ukupne iznose.`) instead of rendering the backend English `note` field. Movement chart now supports article filter and category filter (mutually exclusive). Reuses the same article lookup pattern as the transaction log article search with debounced `articlesApi.listWarehouse`.
- **W9-F-005**: New `Kretanje cijena` section visible to ADMIN and MANAGER. Calls `GET /api/v1/reports/statistics/price-movement` and renders a table with: article number, description, category, latest price, previous price, last change date, delta (absolute), delta % (percentage). Price increases are red, decreases are green. Section is collapsible like all other Statistics subsections.

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-04-wave-09-reports-statistics-and-price-movement/orchestrator.md`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/reports/__tests__/ReportsPage.test.tsx`
- `frontend/src/api/articles.ts`
- `stoqio_docs/17_UI_REPORTS.md`

## Files Changed

| File | Changes |
|------|---------|
| `frontend/src/api/reports.ts` | Extended `getMovementStatistics` to accept `MovementFilter` (range, articleId, category). Added `MovementFilter`, `ReorderDrilldownItem/Response`, `PriceMovementItem/Response` types. Added `getReorderDrilldown` and `getPriceMovement` API methods. |
| `frontend/src/pages/reports/ReportsPage.tsx` | Added `Collapse`, `UnstyledButton`, chevron icons, `IconCurrencyEuro` imports. Added `isManager`/`canViewPriceMovement` guards. Added state for collapsed sections, movement filters, drilldown, price movement. Updated `loadMovementStatistics` to accept filter object. Added `loadReorderDrilldown`, `loadPriceMovement` loaders. Updated statistics init to also load price-movement for eligible roles. Added movement article search effect. Updated `handleMovementRangeChange`, added `handleMovementFilterApply`/`Reset`. Rewrote `handleReorderDrilldown` to call `loadReorderDrilldown` instead of switching tabs. Rewrote entire Statistics panel with collapsible sections, reorder drilldown block, movement filters, Croatian note, and price-movement table. |
| `frontend/src/pages/reports/__tests__/ReportsPage.test.tsx` | Expanded from 1 to 10 tests covering: existing blob-error test preserved, W9-F-008 collapsed state and open-on-click, W9-F-009 drilldown stays in Statistics tab, W9-F-010 Croatian note and movement filter wiring, W9-F-005 price-movement visibility for ADMIN/MANAGER and hidden for WAREHOUSE_STAFF. |

### Files NOT changed within ownership

- `frontend/src/pages/reports/reportsUtils.ts` — not needed; existing formatters cover all new rendering needs.

### Files touched outside ownership

- None.

## Commands Run

```
cd frontend && npx vitest run src/pages/reports/__tests__/ReportsPage.test.tsx   → 10/10 pass
cd frontend && npm run lint                                                       → 0 errors
cd frontend && npm run build                                                      → success (3.20s)
```

## Tests

| Test | Finding | Status |
|------|---------|--------|
| shows section headers but hides content when Statistics tab is opened | W9-F-008 | ✅ |
| opens a subsection when the header is clicked | W9-F-008 | ✅ |
| does not switch to Stock Overview tab when a zone is clicked | W9-F-009 | ✅ |
| renders the Croatian helper note instead of backend English note | W9-F-010 | ✅ |
| passes range with null article/category initially | W9-F-010 | ✅ |
| renders the price movement section for ADMIN | W9-F-005 | ✅ |
| renders price movement section when user is MANAGER | W9-F-005 | ✅ |
| does NOT render price movement section when user is WAREHOUSE_STAFF | W9-F-005 | ✅ |
| shows price movement data when section is expanded | W9-F-005 | ✅ |
| preserves the backend blob error message on stock export failure | Existing | ✅ |

## Open Issues / Risks

1. **Backend endpoints required**: The frontend now targets three endpoints that must exist on the backend:
   - `GET /api/v1/reports/statistics/movement` with optional `article_id` and `category` params
   - `GET /api/v1/reports/statistics/price-movement`
   - `GET /api/v1/reports/statistics/reorder-drilldown?status=RED|YELLOW|NORMAL`
   - If the backend worker has not yet added these, the sections will show error alerts on use. The frontend gracefully handles missing endpoints via `runWithRetry` + error state.

2. **Movement note**: The Croatian note is now rendered client-side and the backend's `note` field is ignored. If the backend removes the `note` field, the type in `MovementStatisticsResponse` should be updated (currently still declared as `string`). No runtime impact either way.

3. **`stoqio_docs/17_UI_REPORTS.md`**: Per instructions, this file was NOT edited. The doc already aligns with Wave 9 behavior (sections 6.3–6.9). No doc follow-up needed.

4. **Old stock-tab drilldown path**: The `stockZoneFilter` state and alert in the Stock Overview tab remain functional for direct use, but the automatic drilldown from Statistics no longer routes through it. This is correct per W9-F-009.

## Next Recommended Step

- Backend worker should implement the three new endpoints (`price-movement`, `reorder-drilldown`, and movement filter params) per the locked contracts.
- Testing worker can run the frontend tests independently to confirm the coverage.
- Orchestrator should validate the full end-to-end flow once backend endpoints are live.
