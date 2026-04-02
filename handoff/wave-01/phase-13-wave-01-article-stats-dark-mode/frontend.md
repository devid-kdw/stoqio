# Frontend Handoff — Phase 13 Wave 1: Article Statistics UI + Dark Mode

- Date: 2026-03-26
- Agent: frontend

---

## Status

COMPLETE. Item A (article statistics section) and Item B (dark mode) implemented. Lint and build both pass.

---

## Scope

- Item A: `GET /api/v1/articles/{id}/stats` UI — collapsible Statistics section on ArticleDetailPage, lazy-loaded on first open, period selector, Recharts bar/line charts, empty state.
- Item B: Dark mode — Mantine 8 `localStorageColorSchemeManager` wired to key `stoqio_color_scheme`, default `light`, toggle in Sidebar, hardcoded light surfaces removed from AppShell.

---

## Docs Read

- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `frontend/package.json`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/main.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/backend.md` (backend contract reference)

---

## Blocker Logged

Recharts was absent from `frontend/package.json`. Per the locked contract, no substitute was used.

- Manual command required and confirmed run by user: `cd frontend && npm install recharts`
- Implementation proceeded only after user confirmed package installed.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/api/articles.ts` | Added `StatPeriod`, `ArticleStatWeekBucket`, `ArticleStatPricePoint`, `ArticleStatsResponse` types; added `getStats(articleId, period)` method to `articlesApi` |
| `frontend/src/pages/warehouse/ArticleDetailPage.tsx` | Added Recharts imports (`BarChart`, `Bar`, `LineChart`, `Line`, `XAxis`, `YAxis`, `CartesianGrid`, `RechartsTooltip`, `ResponsiveContainer`); added `Collapse`, `SegmentedControl`, `UnstyledButton` from Mantine; added stats state (`statsOpen`, `statsPeriod`, `stats`, `statsLoading`, `statsError`, `statsLoadedForRef`); added `loadStats`, `handleToggleStats`, `handleStatsPeriodChange` callbacks; added Statistics collapsible Paper section between Aliases and Transaction History |
| `frontend/src/main.tsx` | Imported `localStorageColorSchemeManager`; created manager instance with key `stoqio_color_scheme`; applied `colorSchemeManager` and `defaultColorScheme="light"` to both `MantineProvider` instances (app + bootstrap loading) |
| `frontend/src/components/layout/Sidebar.tsx` | Imported `ActionIcon`, `Tooltip`, `useMantineColorScheme`, `IconSun`, `IconMoon`; added `isDark` derived from `colorScheme`; wired `toggleColorScheme()` to an `ActionIcon` with sun/moon icon placed above Logout; updated sidebar surface colors and link colors to be theme-aware |
| `frontend/src/components/layout/AppShell.tsx` | Replaced hardcoded `background: '#fafafa'` (wrapper) and `background: '#fff'` (main) with `var(--mantine-color-body)` so surfaces switch in dark mode |

---

## Implementation Decisions

### Statistics section
- Implemented as a collapsible `Paper` (Mantine `Collapse` + `UnstyledButton` header) — additive, no redesign of existing sections.
- **Lazy-load**: `getStats()` is called only when the section is first opened, not on page mount.
- **Period switch without page reload**: period selector re-calls `getStats()` directly; loading spinner stays inline. The `statsLoadedForRef` guards against redundant network calls when re-opening without changing period.
- **Empty state**: shown when `outbound_by_week` and `inbound_by_week` are all-zero AND `price_history` is empty. Message: `"No transaction history available yet."` (per locked contract).
- `stock_history` is returned by the backend but **not rendered** in this wave, consistent with the backend handoff note.
- Recharts tooltip formatters use `String(value)` / `String(label)` to satisfy TypeScript's `ValueType | undefined` signatures without unsafe casts.

### Dark mode
- Uses Mantine 8's `localStorageColorSchemeManager` — no legacy `ColorSchemeProvider` pattern.
- Key: `stoqio_color_scheme`. Supported values: `dark` | `light`. Default: `light`.
- Toggle: `useMantineColorScheme().toggleColorScheme()` called from an `ActionIcon` in Sidebar. Persists automatically via the manager.
- AppShell: only the two shared hardcoded light-surface colors (`#fafafa`, `#fff`) were replaced with `var(--mantine-color-body)`. No other shared layout changes.
- Sidebar: inline color overrides for background, border, and link colors derived from `isDark` boolean — minimal surface change, no component-level structural change.

---

## Commands Run

```
cd frontend && npm install recharts          # user ran manually (blocker resolved)
cd frontend && npm run lint -- --max-warnings=0   # PASSED
cd frontend && npm run build                    # PASSED
```

---

## Tests

| Check | Result |
|-------|--------|
| `npm run lint -- --max-warnings=0` | PASSED — 0 warnings, 0 errors |
| `npm run build` | PASSED — 7711 modules transformed, build in 2.66s |

---

## Open Issues / Risks

- Recharts bundle adds ~114 kB (gzip) to the `ArticleDetailPage` chunk. Acceptable for v1; consider code-splitting if the page becomes a load bottleneck.
- `stock_history` field from the stats endpoint is unused in this wave. If future agents render it, note the backend handoff caveat: opening balance includes all `tx_type` values (including `INVENTORY_ADJUSTMENT` etc.) so the rendered balance may diverge from the `Stock` table if external corrections exist.
- Sidebar dark colors are hardcoded inline values matching Mantine's default dark palette (`#1a1b1e`, `#2c2e33`, `#373a40`). If the Mantine theme is later customised, these may need updating.

---

## Next Recommended Step

- Testing agent: verify that the stats endpoint returns the expected shape when the Statistics section is opened in a running environment, and confirm dark mode persists on page reload.
