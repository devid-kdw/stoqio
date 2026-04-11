# Wave 9 Handoffs

This folder stores Wave 9 user-feedback remediation handoff folders.

Use the existing `handoff/README.md` protocol and create one subfolder per phase in the format:

- `phase-NN-wave-09-*`

## Wave 9 Purpose

Wave 9 addresses user feedback collected on 2026-04-11 in:

- `handoff/Findings/wave-09-user-feedback.md`

This wave is a mixed UX, RBAC, Identifier, and Reports expansion wave. Every change must be
traceable to one or more `W9-F-*` findings. Scope creep is not permitted.

## Phases

| Phase | Owner | Primary Findings | Can run in parallel |
|-------|-------|------------------|---------------------|
| `phase-01-wave-09-shell-and-orders-ux` | Frontend | W9-F-001, W9-F-003 | Yes |
| `phase-02-wave-09-manager-employees-rbac` | Full stack | W9-F-004 | Yes |
| `phase-03-wave-09-identifier-order-visibility` | Full stack | W9-F-007 | Yes |
| `phase-04-wave-09-reports-statistics-and-price-movement` | Full stack | W9-F-005, W9-F-008, W9-F-009, W9-F-010 | Yes |
| `phase-05-wave-09-warehouse-article-stats-refresh` | Frontend | W9-F-002, W9-F-006 | Yes |

## File Ownership Per Phase

- Phase 1 frontend:
  - `frontend/src/components/layout/AppShell.tsx`
  - `frontend/src/components/layout/__tests__/AppShell.test.tsx`
  - `frontend/src/pages/orders/OrdersPage.tsx`
  - `frontend/src/theme.ts` (only if needed)
  - `stoqio_docs/12_UI_ORDERS.md` (only if behavior docs need alignment)
- Phase 2 full stack:
  - `backend/app/api/employees/routes.py`
  - `backend/tests/test_employees.py`
  - `frontend/src/routes.tsx`
  - `frontend/src/components/layout/Sidebar.tsx`
  - `frontend/src/pages/employees/EmployeesPage.tsx`
  - `frontend/src/pages/employees/EmployeeDetailPage.tsx`
  - `stoqio_docs/03_RBAC.md`
  - `stoqio_docs/15_UI_EMPLOYEES.md`
- Phase 3 full stack:
  - `backend/app/services/article_service.py`
  - `backend/tests/test_articles.py`
  - `backend/tests/test_aliases.py` (only if identifier alias coverage is touched)
  - `frontend/src/api/identifier.ts`
  - `frontend/src/pages/identifier/IdentifierPage.tsx`
  - `frontend/src/pages/identifier/identifierUtils.ts`
  - `stoqio_docs/03_RBAC.md`
  - `stoqio_docs/14_UI_IDENTIFIER.md`
- Phase 4 full stack:
  - `backend/app/api/reports/routes.py`
  - `backend/app/services/report_service.py`
  - `backend/tests/test_reports.py`
  - `frontend/src/api/reports.ts`
  - `frontend/src/pages/reports/ReportsPage.tsx`
  - `frontend/src/pages/reports/reportsUtils.ts` (only if needed)
  - `frontend/src/pages/reports/__tests__/ReportsPage.test.tsx`
  - `stoqio_docs/17_UI_REPORTS.md`
- Phase 5 frontend:
  - `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
  - `stoqio_docs/13_UI_WAREHOUSE.md`

If implementation proves a phase needs a file outside its ownership list, the agent must document
why in its handoff entry.

## Finding Reference

| ID | Description | Phase |
|----|-------------|-------|
| W9-F-001 | Closed orders list uses a white/light background in dark mode | 1 |
| W9-F-002 | Warehouse article statistics charts need a stronger visual treatment | 5 |
| W9-F-003 | Left module menu should stay fixed while page content scrolls | 1 |
| W9-F-004 | MANAGER role should have access to the Employees screen | 2 |
| W9-F-005 | Reports should include a warehouse-wide article price-movement section for ADMIN and MANAGER | 4 |
| W9-F-006 | Article statistics should provide a deeper price-history drill-in per article | 5 |
| W9-F-007 | Identifier should replace surplus with order status and role-sensitive purchasing visibility | 3 |
| W9-F-008 | Reports statistics subsections should be collapsed by default and opened on click | 4 |
| W9-F-009 | Reorder-zone drilldown should stay inside Reports statistics instead of switching to Stock Overview | 4 |
| W9-F-010 | Movement chart note is still in English and the chart needs article/category filtering | 4 |
