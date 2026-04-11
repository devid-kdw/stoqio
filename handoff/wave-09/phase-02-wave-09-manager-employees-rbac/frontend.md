# Wave 9 Phase 2 — Frontend Handoff

Date: 2026-04-11

## Status

Complete. MANAGER now sees and can access the Employees module in read-only mode. Lint and build pass.

## Scope

- W9-F-004: MANAGER gains read-only access to the Employees module (list + detail, quotas, issuance history).
- ADMIN-only mutation controls (create, edit, deactivate, issue article) are already gated behind
  `isAdmin` in both employee screens — no changes were needed there.

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-02-wave-09-manager-employees-rbac/orchestrator.md`
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/employees/EmployeesPage.tsx`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/15_UI_EMPLOYEES.md`

## Files Changed

### `frontend/src/routes.tsx`
- Changed employees route guard from `['ADMIN', 'WAREHOUSE_STAFF']` to
  `['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF']` for both `/employees` and `/employees/:id`.

### `frontend/src/components/layout/Sidebar.tsx`
- Changed `canSeeEmployees` from `['ADMIN', 'WAREHOUSE_STAFF'].includes(role)` to
  `['ADMIN', 'MANAGER', 'WAREHOUSE_STAFF'].includes(role)`.
- MANAGER now sees `Zaposlenici` in the sidebar navigation.

### `stoqio_docs/03_RBAC.md`
- Removed `<!-- Wave 9 -->` placeholder comment from the MANAGER sidebar window entry.
- The permission matrix and display window already reflected the new MANAGER access
  (was pre-written during intake). This change finalizes the doc as implemented.

## Commands Run

```
cd frontend && npm run lint    → clean
cd frontend && npm run build   → clean (TypeScript + Vite, 29 chunks, ✓ built in 2.89s)
```

## Tests

- No new unit tests added. The route guard and sidebar changes are routing/rendering logic that
  are covered by the existing AppShell tests for sidebar rendering.
- `EmployeesPage.tsx` and `EmployeeDetailPage.tsx` required no logic changes — all mutation
  controls were already correctly gated behind `isAdmin = user?.role === 'ADMIN'`, which
  naturally excludes MANAGER.
- MANAGER read/write enforcement at the API layer is the responsibility of the backend worker
  (backend.md).

## Open Issues / Risks

- Backend authorization must extend employees read endpoints to MANAGER (parallel backend worker).
  Until that is deployed, MANAGER will see the UI but the API calls will return 403.
- No new frontend risk introduced — existing `isAdmin` guards are not weakened.

## Next Recommended Step

Orchestrator validates this phase against the backend worker's delivery and confirms both sides
are aligned before marking W9-F-004 complete.
