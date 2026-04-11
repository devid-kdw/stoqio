# Wave 9 User Feedback Findings

Date opened: 2026-04-11

Source:
- User feedback in the main Codex orchestration session.

Status:
- Collecting feedback before opening `handoff/wave-09`.

Notes:
- This document is the intake list for Wave 9 planning.
- Items should be confirmed and converted into scoped Wave 9 phase handoffs before implementation.
- Keep entries append-only while feedback is still being collected.

## W9-F-001: Closed orders list uses a white/light background in dark mode

Status:
- open

Area:
- Orders
- Frontend dark mode
- Orders list visual styling

Source:
- User feedback and screenshot, 2026-04-11 18:04 CEST

User report:
- On the Orders screen, the `Zatvorene narudžbenice` section has a white/light background in dark mode.
- This breaks the dark theme and makes the closed-orders block visually inconsistent with the rest of the page.

Observed code pointers:
- `frontend/src/pages/orders/OrdersPage.tsx`
- `OrdersTableSection` currently applies hardcoded light `linear-gradient(...)` backgrounds for both normal and `muted` states.

Expected behavior:
- Closed orders should respect the active dark theme.
- The closed-orders section may still look visually muted compared with open orders, but it must not use a white/light panel in dark mode.
- Any visual de-emphasis should come from theme-aware styling, not hardcoded light backgrounds.

Current likely behavior:
- `OrdersTableSection` uses fixed light RGBA gradient values instead of theme-aware colors.
- Because closed orders are rendered with `muted={true}`, the section keeps a pale background even in dark mode.

Recommended direction:
- Replace the hardcoded panel backgrounds in `OrdersPage.tsx` with Mantine/theme-aware surface colors.
- Preserve the distinction between open and closed orders using dark-mode-safe contrast, opacity, border, or subtle theme-derived background tokens.

## W9-F-002: Warehouse article statistics charts need a stronger visual treatment

Status:
- open

Area:
- Warehouse
- Article detail
- Frontend chart styling / data visualization UX

Source:
- User feedback and screenshot, 2026-04-11 18:05 CEST

User report:
- On `Skladište -> Artikl -> Statistika`, the charts show useful data but the visual presentation feels unattractive and underdesigned.
- The user wants a better-styled visual treatment, but not necessarily a change in the underlying data itself.

Observed code pointers:
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- The statistics section currently renders:
  - `Tjedni izlaz` via `BarChart`
  - `Tjedni ulaz` via `BarChart`
  - `Povijest cijene (primke)` via `LineChart`
- Current rendering uses mostly default Recharts presentation with simple saturated fills, standard dashed grid lines, and minimal visual hierarchy around each chart.

Expected behavior:
- Article statistics should feel clearer, more polished, and more intentional visually.
- The charts should remain easy to read in dark mode.
- The section should look like a compact decision-support dashboard, not a raw default chart embed.

Current likely behavior:
- Bars and line colors are functional but visually harsh against the dark background.
- Chart panels lack enough hierarchy, framing, annotation, or summary context.
- The three charts read more like generic placeholders than finished STOQIO UI.

Recommended direction:
- Treat this as a frontend-only chart presentation improvement unless implementation reveals a real data-shape gap.
- Consider redesigning the statistics block with:
  - theme-aware chart surfaces/cards per chart
  - softer grid/tick styling
  - a more intentional color system
  - compact summary labels or KPIs above each chart
  - better spacing and typographic hierarchy

User clarification / decision:
- 2026-04-11: The user accepted the proposed `Option 1` direction for implementation.
- Locked visual direction for Wave 9:
  - redesign the statistics section as a compact mini-dashboard
  - keep three separate charts
  - place each chart in its own theme-aware card/panel
  - add compact KPI/summary context above each chart
  - improve chart styling rather than changing the underlying data model

## W9-F-003: Left module menu should stay fixed while page content scrolls

Status:
- open

Area:
- Global layout
- Sidebar / navigation shell
- Frontend UX

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- The left module-selection menu currently moves away when the user scrolls down on longer screens.
- This is impractical for navigation.
- The user expects the left menu to stay static regardless of page scrolling.

Observed code pointers:
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `AppShell` currently uses a simple flex layout with `minHeight: '100vh'`.
- `Sidebar` is rendered as a normal flex child without `sticky`/`fixed` positioning or a viewport-pinned shell.

Expected behavior:
- The left navigation should remain visible while the main page content scrolls vertically.
- The shell should feel stable across long module screens such as Warehouse article detail, Reports, Settings, and other tall views.
- If the sidebar content ever exceeds viewport height, the sidebar itself should remain usable via its own internal scroll rather than moving with the page.

Current likely behavior:
- The window/body scroll moves both the main content and the sidebar together.
- Because the sidebar is part of the normal document flow, it does not stay pinned to the viewport.

Recommended direction:
- Treat this as a shared shell/layout improvement, not a one-screen fix.
- Refactor `AppShell` / `Sidebar` so the navigation column is viewport-pinned (`sticky` or fixed-height shell with independent main-content scrolling).
- Keep dark/light theme behavior and logout/theme-toggle footer actions intact.

## W9-F-004: MANAGER role should have access to the Employees screen

Status:
- open

Area:
- RBAC
- Employees module
- Frontend routing/sidebar + backend authorization

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- After creating and testing a manager role, the user concluded that MANAGER should have access to the `Zaposlenici` screen.

Observed code pointers:
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/15_UI_EMPLOYEES.md`
- `backend/app/api/employees/routes.py`

Current repo reality:
- Frontend currently exposes Employees only to `ADMIN` and `WAREHOUSE_STAFF`.
- The RBAC spec currently says MANAGER does not have access to employee dossiers.

Expected behavior:
- MANAGER should see the `Zaposlenici` module in the sidebar.
- MANAGER should be able to open the Employees list/detail screens.
- The exact permission depth still needs implementation scoping, but the safe default direction is MANAGER read-only access unless the user later requests mutation rights explicitly.

Important product note:
- This is an explicit RBAC expansion request from the project owner/user and should be treated as a deliberate override of the current locked RBAC baseline once Wave 9 implementation starts.

Recommended direction:
- Add MANAGER to Employees read paths first.
- Preserve ADMIN-only mutation actions unless the user later requests broader MANAGER write access.
- Update both frontend UX guards and backend endpoint authorization rules, then align `03_RBAC.md` and Employees docs.

## W9-F-005: Reports should include a warehouse-wide article price-movement section for ADMIN and MANAGER

Status:
- open

Area:
- Reports
- Price analytics
- Backend reporting contract + frontend reports UI

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- Reports should gain a new section for `kretanje cijena artikala`.
- ADMIN and MANAGER should be able to view it.
- The section should track price changes for all warehouse articles.
- It should show all articles, but prioritize articles whose prices changed most recently by pushing them to the top.

Observed code pointers:
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/api/reports.ts`
- `backend/app/services/report_service.py`
- `stoqio_docs/17_UI_REPORTS.md`
- Existing article-level stats already expose `price_history`, but Reports currently has no warehouse-wide consolidated price-change section.

Expected behavior:
- Reports should expose a dedicated price-movement view/tab/section visible to ADMIN and MANAGER.
- The view should list all articles with relevant pricing history context.
- Articles with the most recent price changes should appear first by default.
- The section should help management review pricing changes across the whole warehouse, not only one article at a time.

Current likely behavior:
- Price history exists only as a per-article stats detail on Warehouse article pages.
- There is no global report aggregating recent price changes across all articles.

Recommended direction:
- Treat this as a new Reports feature, not only a styling change.
- Introduce a dedicated backend report endpoint/query for article price history rollups.
- Surface at least:
  - article identity
  - latest known price
  - previous known price
  - last change date
  - optional change delta / percentage
- Sort by most recent actual price change first, while still allowing access to the full article list.

## W9-F-006: Article statistics should provide a deeper price-history drill-in per article

Status:
- open

Area:
- Warehouse
- Article detail statistics
- Price history UX

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- Each article should have an option in its statistics area to enter and review price changes throughout history.

Observed code pointers:
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `backend/app/api/articles/routes.py` (`GET /api/v1/articles/{id}/stats`)
- `backend/app/services/article_service.py` (`price_history` already exists in article stats)

Current repo reality:
- Article statistics already include a simple `Povijest cijene (primke)` line chart.
- The current UI does not appear to provide a more detailed history drill-in beyond that chart.

Expected behavior:
- From an article's statistics area, the user should be able to open a richer historical price view.
- The drill-in should make it easy to inspect concrete price changes over time, not only a compact sparkline-style summary.
- This detailed view should align with the new Wave 9 price-movement reporting direction so article-level and global price analytics feel like one system.

Recommended direction:
- Keep the existing inline price chart as the compact summary.
- Add a clear drill-in action from article statistics into either:
  - an article-scoped detailed history panel/table/modal, or
  - the new Reports price-movement section prefiltered to that article.
- Prefer one shared source of truth for detailed price-history data so Warehouse and Reports do not diverge.

## W9-F-007: Identifier should replace surplus with order status and role-sensitive purchasing visibility

Status:
- open

Area:
- Identifier
- RBAC-sensitive field visibility
- Backend identifier contract + frontend result cards

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- On the Identifier screen, when searching for an article, the current result shows how much stock exists and whether there is surplus.
- The user wants the surplus display removed.
- Instead, Identifier should show whether the article is currently ordered and, if it is ordered, how much is ordered.
- Identifier should also show the latest purchase price.
- However, `zadnja nabavna cijena` and `koliko je naručeno` must be visible only to ADMIN and MANAGER.
- Other roles that can access Identifier should see only whether the article is in stock and whether it is ordered.

Observed code pointers:
- `stoqio_docs/14_UI_IDENTIFIER.md`
- `frontend/src/pages/identifier/IdentifierPage.tsx`
- `frontend/src/api/identifier.ts`
- `backend/app/services/article_service.py` (`search_identifier_articles`, `_serialize_identifier_item`)

Current repo reality:
- Identifier currently returns:
  - `stock` + `surplus` for non-VIEWER roles
  - `in_stock` boolean only for VIEWER
- The UI currently renders `Na stanju` and `Višak` for quantity-style results.
- There is no current Identifier field for:
  - ordered/not ordered status
  - ordered quantity
  - latest purchase price

Expected behavior:
- Identifier should stop surfacing `Višak`.
- Identifier should include order-state information in the search-result card.
- Visibility should become role-sensitive:
  - `ADMIN` and `MANAGER`:
    - exact stock quantity
    - whether ordered
    - ordered quantity
    - latest purchase price
  - other roles with Identifier access (`WAREHOUSE_STAFF`, `VIEWER`):
    - whether in stock
    - whether ordered
    - no exact ordered quantity
    - no latest purchase price

Important product impact:
- This changes the current Identifier visibility model from the accepted Wave 1 baseline.
- In particular, `WAREHOUSE_STAFF` appears to lose exact stock quantity visibility in Identifier and move to a simpler boolean-style availability display.
- Treat that as an explicit product-direction override from the user when Wave 9 implementation begins.

Open implementation questions for Wave 9 scoping:
- `Je li naručeno` should likely mean the article has at least one active/open purchase-order line, but the exact rule should be locked before implementation.
- `Koliko je naručeno` likely should mean outstanding ordered quantity still not received, not just the historical sum of all open-order line quantities; confirm this during scoping.
- `Zadnja nabavna cijena` should likely come from the latest relevant receiving/unit-price source already used elsewhere, but this should be aligned with existing Reports/Orders pricing rules.

User clarification / decision:
- 2026-04-11: The user confirmed that `koliko je naručeno` means the currently outstanding quantity on open purchase orders, not a historical ordered total.
- If the same article appears on multiple open orders at the same time, the Identifier should sum those still-open/outstanding quantities to produce the displayed `koliko je naručeno` value.
- `Je li naručeno` should therefore resolve to `true` when the summed outstanding quantity across open orders for the article is greater than zero.

Recommended direction:
- Update the Identifier backend response shape to be explicitly role-aware, not only `VIEWER` vs everyone else.
- Remove `surplus` from Identifier cards and docs.
- Add:
  - `ordered` / `is_ordered` boolean
  - role-gated ordered quantity
  - role-gated latest purchase price
- Update Identifier UI and docs so result cards match the new role matrix exactly.

## W9-F-008: Reports statistics subsections should be collapsed by default and opened on click

Status:
- open

Area:
- Reports
- Statistics sub-screen
- Frontend information architecture / UX

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- On `Izvještaji -> Statistike`, the subsections `Top 10 po potrošnji`, `Ulaz i izlaz kroz vrijeme`, `Sažetak zona naručivanja`, and `Osobna izdavanja` are currently open by default.
- The user wants them all collapsed initially and opened only on click.
- The goal is a cleaner and more selective reading experience, where only the desired subsection is expanded.

Observed code pointers:
- `frontend/src/pages/reports/ReportsPage.tsx`
- `stoqio_docs/17_UI_REPORTS.md`
- The current Statistics tab renders all four sections directly inside always-visible `Paper` cards.

Expected behavior:
- All Statistics subsections should start in a collapsed/summary state.
- The user should open only the subsection they want to inspect.
- The Statistics tab should feel more compact and navigable, especially as more Reports features are added in Wave 9.

Current likely behavior:
- All four sections are rendered fully expanded, creating a long, visually heavy page.
- This makes the Statistics screen harder to scan and less modular than it could be.

Recommended direction:
- Convert the Statistics sub-screen into a collapsible structure using theme-consistent section headers.
- Treat this as a shared Reports UX pattern because more Statistics content is likely coming in Wave 9.
- Preserve lazy/data-loading considerations where sensible so collapsed sections do not feel wasteful.

## W9-F-009: Reorder-zone drilldown should stay inside Reports statistics instead of switching to Stock Overview

Status:
- open

Area:
- Reports
- Statistics sub-screen
- Reorder-zone drilldown UX

Source:
- User feedback in the main Codex session, 2026-04-11

User report:
- On `Izvještaji -> Statistike -> Sažetak zona naručivanja`, clicking a zone such as `Crvena zona` currently opens the `Doseg zaliha` screen with the corresponding drilldown filter.
- The user does not find that practical.
- They prefer this interaction to stay inside the Statistics sub-screen so the drilldown result opens there instead of switching context.

Observed code pointers:
- `frontend/src/pages/reports/ReportsPage.tsx`
- `handleReorderDrilldown()` currently sets `setActiveTab('stock')`.
- `stoqio_docs/17_UI_REPORTS.md` currently documents this same stock-overview redirect behavior.

Expected behavior:
- Clicking a reorder zone from `Sažetak zona naručivanja` should open the related article list within `Statistike`, not redirect the user to another Reports tab.
- The drilldown should feel local to the summary widget and keep the user's analytical context intact.

Current likely behavior:
- Zone drilldown is implemented as a tab switch to `Doseg zaliha`.
- This breaks the user's focus and makes the Statistics tab feel like a launcher rather than a self-contained analysis area.

Recommended direction:
- Keep zone drilldown results inside the Statistics tab.
- Prefer an inline or local drilldown result area that shows the articles belonging to the selected zone without leaving the current sub-screen.
- Update both code and `17_UI_REPORTS.md` so the accepted Reports interaction model stays aligned.

User clarification / decision:
- 2026-04-11: The user selected `Option 2` for reorder-zone drilldown presentation.
- When a zone such as `Crvena zona` is clicked, the related article list should open in a separate collapsible block within the `Statistike` tab, rather than inline under the summary widget and rather than switching to `Doseg zaliha`.

## W9-F-010: Movement chart note is still in English and the chart needs article/category filtering

Status:
- open

Area:
- Reports
- Statistics sub-screen
- Movement chart copy + filtering

Source:
- User feedback and screenshot, 2026-04-11 18:23 CEST

User report:
- On `Izvještaji -> Statistike -> Ulaz i izlaz kroz vrijeme`, the explanatory note below the chart is still in English and should be localized.
- The user also wants an option to enter/select a specific article and view this trend only for that article.
- The default should remain the current whole-warehouse trend.
- The chart should additionally support filtering by article category.

Observed code pointers:
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/api/reports.ts`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`
- `stoqio_docs/17_UI_REPORTS.md`
- Current `getMovementStatistics()` accepts only `range` and returns a backend-provided English `note`.

Current repo reality:
- The movement chart currently aggregates inbound/outbound activity across the whole warehouse.
- The note shown under the chart is English.
- There is no movement-level filter for:
  - specific article
  - article category

Expected behavior:
- The explanatory note under the movement chart should be Croatian.
- The chart should support three practical modes:
  - default: entire warehouse
  - filtered by one exact article
  - filtered by one article category
- The warehouse-wide trend should remain the default landing state.

Important product note:
- Filtering by a single article avoids the mixed-UOM “trend only” ambiguity for that case and makes the chart more operationally useful.
- Category filtering should stay easy to use from the Statistics screen without forcing the user to leave the tab.

Recommended direction:
- Treat this as both a localization fix and a reporting-contract enhancement.
- Extend the movement endpoint/query to accept optional `article_id` and `category` filters.
- Update the Statistics UI to expose:
  - an exact article selector/search field
  - a category selector
  - clear default/reset behavior back to warehouse-wide mode
- Localize the note text and, if needed, let the frontend render role-neutral Croatian helper copy rather than relying on an English backend string.
