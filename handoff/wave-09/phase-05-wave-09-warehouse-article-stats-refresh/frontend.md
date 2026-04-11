---
agent: frontend
date: 2026-04-11
phase: wave-09/phase-05-wave-09-warehouse-article-stats-refresh
---

## Status

Done — lint passes (0 warnings), build passes (2.65 s).

## Scope

W9-F-002 — Warehouse article Statistics section visual refresh (mini-dashboard cards, KPIs, theme-aware charts)
W9-F-006 — Deeper local price-history drill-in (collapsible table within the price chart card)

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-05-wave-09-warehouse-article-stats-refresh/orchestrator.md`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/orchestrator.md`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/frontend.md`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/api/articles.ts`
- `frontend/src/theme.ts`
- `frontend/src/pages/reports/ReportsPage.tsx` (dark-mode pattern reference)
- `stoqio_docs/13_UI_WAREHOUSE.md`

## Files Changed

### `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

**Imports added:**
- `useMantineColorScheme`, `useMantineTheme` from `@mantine/core`

**New helpers (outside component):**
- `fmtStat(v: number): string` — formats quantities, strips trailing decimal zeros
- `fmtPrice(v: number): string` — formats unit prices to 4 decimal places, strips trailing zeros

**New state:**
- `priceTableOpen: boolean` — controls the price-history drill-in table collapse

**New hooks / derived values (in component body):**
- `colorScheme`, `theme`, `isDark` — from `useMantineColorScheme` / `useMantineTheme`
- `chartGridColor`, `chartTickColor` — theme-aware chart styling constants
- `statsKpis` (useMemo) — derived from `stats`: `totalOut`, `activeWeeksOut`, `totalIn`, `activeWeeksIn`, `lastPrice`, `delta`, `deltaPct`

**Statistics section redesign:**

Previous: three `<Stack gap="xs">` blocks with plain Recharts charts, no visual hierarchy, English empty-state text.

New:
- Each chart is wrapped in a themed `<Paper withBorder radius="md">` mini-dashboard card.
- Every card has a dimmed uppercase section label + a compact KPI row above the chart.
- All chart `CartesianGrid`, `XAxis`, `YAxis`, and `RechartsTooltip` elements use theme-aware colours (`chartGridColor`, `chartTickColor`, `theme.colors.dark[6]` / `#fff`).
- Outbound card KPIs: Ukupno izlaz (base UOM) + Aktivnih tjedana.
- Inbound card KPIs: Ukupno ulaz (base UOM) + Aktivnih tjedana.
- Price card KPIs: Zadnja cijena + Promjena (delta + %) + Zapisa.
  - Delta colour: red for price increase, green for decrease (matching Croatian warehouse convention where lower price = saving).
- Bar fill colours updated: outbound `#f03e3e` (red), inbound `#339af0` (blue). Price line stays `#51cf66` (green).
- Tick font size reduced from 11 → 10 px for cleaner layout in cards.
- Empty-state text changed from English to Croatian: `"Nema dostupne povijesti transakcija."`

**Price history drill-in (W9-F-006):**
- "Prikaži sve zapise" / "Sakrij zapise" toggle at the bottom of the price chart card.
- `<Collapse in={priceTableOpen}>` reveals a compact `<Table>` (max-width 360 px) showing all price points newest-first.
- Columns: Datum primke (date only) | Cijena / jed. (monospace formatted price).
- State (`priceTableOpen`) is not reset on period change — user intent is preserved between period switches.

**Preserved behavior:**
- Lazy-load on first expand is unchanged.
- Period selector behavior (30 / 90 / 180 days, `statsLoadedForRef` guard) is unchanged.
- All existing section structure (aliases, batches, suppliers, transactions, barcode actions) is untouched.

### `stoqio_docs/13_UI_WAREHOUSE.md`

- Added Section 5.5 "Statistics Section (Statistika)" documenting:
  - lazy-load behavior
  - period selector
  - three mini-dashboard card layout with KPI columns
  - price history drill-in table (columns, sort order, toggle)
  - empty state
- Renumbered former 5.5 "Article Actions" to 5.6.

## Commands Run

```
cd frontend && npm run lint
cd frontend && npm run build
```

## Tests

| Check | Result |
|-------|--------|
| `npm run lint` | PASSED — 0 warnings, 0 errors |
| `npm run build` | PASSED — 2.65 s, ArticleDetailPage 395 kB / 116 kB gzip |

No new automated frontend tests were added. The Statistics section is a pure render path with no new business logic (KPI derivation is in `useMemo`); test coverage of the stats fetch flow is unchanged from Wave 1 Phase 13. Manual verification of the UI is recommended when the dev server is running.

## Open Issues / Risks

- **`ArticleDetailPage` bundle size**: The chunk is ~116 kB gzip (unchanged from before this phase). The Recharts library is already co-bundled from Wave 1 Phase 13 — this phase adds no new dependencies.
- **Price delta colour convention**: Price increase shown in red and decrease in green. This matches a "higher cost = bad" warehouse framing. If the product later wants the opposite convention (e.g., price drop = warning), it is a one-line change in `c={...}`.
- **`priceTableOpen` not reset on period change**: Intentional — preserves the user's drill-in state when switching periods. If the preference changes, add `setPriceTableOpen(false)` inside `handleStatsPeriodChange`.
- **`stock_history` still unused**: Consistent with the Wave 1 Phase 13 decision. Rendering it is still a future-work item.
- **Manual browser verification not performed**: Acceptance is based on code-path review and green lint/build gates, consistent with the Wave 1 Phase 13 orchestrator validation note.

## Next Recommended Step

No immediate blocker. Wave 9 Phase 5 is complete on the frontend side.

If further visual polish is requested, consider:
- Responsive two-column chart layout for wide screens (currently all three stack vertically).
- Adding a sparkline or trend arrow to the KPI row for outbound/inbound total context.
