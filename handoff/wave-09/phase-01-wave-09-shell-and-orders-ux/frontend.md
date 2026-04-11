# Wave 9 Phase 1 — Frontend Handoff

Date: 2026-04-11

## Status

Complete. Both findings remediated. Lint, build, and AppShell tests pass.

## Scope

- W9-F-001: Closed orders list used hardcoded light RGBA gradient backgrounds that broke dark mode.
- W9-F-003: The left module navigation moved with the page scroll instead of staying viewport-pinned.

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-01-wave-09-shell-and-orders-ux/orchestrator.md`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/theme.ts`
- `stoqio_docs/12_UI_ORDERS.md`

## Files Changed

### `frontend/src/components/layout/AppShell.tsx`
- Changed outer shell div from `minHeight: '100vh'` to `height: '100vh'; overflow: 'hidden'`.
- Added `overflowY: 'auto'` to the `<main>` element so only the page content area scrolls.
- The sidebar becomes viewport-pinned as a result — it no longer moves with the page.

### `frontend/src/components/layout/Sidebar.tsx` *(outside ownership list — see note below)*
- Added `height: '100%'`, `overflowY: 'auto'`, and `flexShrink: 0` to the `<nav>` element.
- Needed so the sidebar fills the full viewport height (via flex `align-self: stretch`) and handles
  internal scroll if the nav-item list ever exceeds viewport height.
- **Why this file was touched:** The shell-level fix (AppShell) constrains the viewport to `100vh`.
  Without `height: 100%` on the nav, the sidebar would not correctly fill the constrained container
  and the footer (theme toggle, logout) would no longer be pinned to the bottom. Adding overflow and
  height directly to the `<nav>` element was the minimal, least-invasive way to make the sidebar
  behave correctly in the new layout. Touching AppShell alone would not have been sufficient.

### `frontend/src/pages/orders/OrdersPage.tsx`
- Removed the hardcoded `linear-gradient(…)` backgrounds from `OrdersTableSection`.
- The `style` prop now only carries `opacity: muted ? 0.65 : 1` for muted (closed) sections.
- Mantine `Paper` default surface handles theming correctly in both light and dark mode.
- The open/closed visual distinction is preserved via opacity de-emphasis.

## Commands Run

```
cd frontend && npm run lint      → clean (no errors, no warnings)
cd frontend && npm run build     → clean (TypeScript + Vite, 29 chunks, ✓ built in 3.01s)
npx vitest run src/components/layout/__tests__/AppShell.test.tsx → 2/2 passed
```

## Tests

- Existing AppShell tests (2/2) pass unchanged.
- Tests cover: shell renders location name and role label for non-admin; falls back to defaults on
  API failure.
- Layout behavior (sidebar pinning, main scroll) requires visual/browser verification — JSDOM does
  not compute scroll geometry.

## Open Issues / Risks

- None for this phase. The sidebar overflow case (nav items exceeding viewport height) is now handled
  gracefully, but has not been visually verified at extreme font sizes or very short viewports.

## Next Recommended Step

Orchestrator validates this phase and unblocks or reviews parallel Wave 9 phases (2–5).
