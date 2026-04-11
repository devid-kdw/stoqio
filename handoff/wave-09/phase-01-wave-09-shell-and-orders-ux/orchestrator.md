## Phase Summary

Phase
- Wave 9 - Phase 1 - Shell and Orders UX

Objective
- Remediate W9-F-001 and W9-F-003:
  closed orders must respect dark mode, and the left shell navigation must remain visible while
  long page content scrolls.

Source Docs
- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/theme.ts`
- `stoqio_docs/12_UI_ORDERS.md`

Current Repo Reality
- `OrdersPage.tsx` applies hardcoded light gradients to `OrdersTableSection`, so the closed-orders
  panel looks pale/white in dark mode.
- `AppShell.tsx` uses a straightforward flex shell with `minHeight: '100vh'`, and the window/body
  scroll moves both content and navigation together.
- Sidebar behavior currently depends on normal document flow rather than a viewport-pinned shell.

Contract Locks / Clarifications
- Fix the navigation issue at the shell/layout level, not with one-off screen hacks.
- Preserve the existing sidebar footer, theme toggle, and logout controls.
- Closed orders may remain visually de-emphasized relative to open orders, but must use
  theme-aware styling in both light and dark modes.
- This phase does not change RBAC or module visibility.

File Ownership
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/theme.ts` (only if needed)
- `stoqio_docs/12_UI_ORDERS.md` (only if behavior docs need alignment)
- `handoff/wave-09/phase-01-wave-09-shell-and-orders-ux/frontend.md`

Delegation Plan
- Frontend:
  - make the app shell keep navigation visible during vertical content scroll
  - keep any sidebar overflow usable without breaking the rest of the layout
  - replace the closed-orders hardcoded light panel styling with theme-aware surfaces
  - run frontend validation for the touched shell/orders files

Acceptance Criteria
- The left module navigation remains visible while long pages scroll.
- Closed orders no longer render a white/light block in dark mode.
- Orders open/closed visual distinction still exists without hardcoded light gradients.
- Frontend build and lint pass.

Validation Notes
- 2026-04-11: Orchestrator opened Wave 9 Phase 1 from the finalized Wave 9 feedback intake.
- 2026-04-11: Post-delivery orchestrator review found one regression risk in the shell-scroll
  change:
  `AppShell` moved vertical scrolling from `window` to the `<main>` content container, but
  `frontend/src/pages/warehouse/ArticleDetailPage.tsx` still used `window.scrollTo(...)` after a
  successful article save. That would have broken the accepted Wave 8 UX fix that returns the user
  to the top of the article page after saving.
- 2026-04-11: Orchestrator remediation applied directly:
  - added `id="app-shell-main-scroll"` to the shell `<main>` container in
    `frontend/src/components/layout/AppShell.tsx`
  - updated `frontend/src/pages/warehouse/ArticleDetailPage.tsx` to scroll that shell container to
    the top after save, with `window.scrollTo(...)` kept as a fallback when the shell container is
    unavailable
  - this remediation was performed by the main orchestrator session after code review so future
    agents should treat the shell scroll container ID as the accepted Wave 9 baseline for any
    future “scroll current page content to top” behavior inside the authenticated app shell

Next Action
- Frontend worker implements and records `frontend.md`.
