## Phase Summary

Phase
- Wave 9 - Phase 4 - Reports Statistics and Price Movement

Objective
- Remediate W9-F-005, W9-F-008, W9-F-009, and W9-F-010:
  Reports must gain a warehouse-wide price-movement section, the Statistics tab should become
  collapsible and more self-contained, reorder-zone drilldown must stay inside Statistics, and the
  movement chart needs Croatian copy plus article/category filtering.

Source Docs
- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `stoqio_docs/17_UI_REPORTS.md`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/reports/__tests__/ReportsPage.test.tsx`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`

Current Repo Reality
- The Statistics tab renders all sections expanded by default.
- Reorder-zone drilldown currently switches the user to the Stock Overview tab.
- The movement chart helper note is still English.
- Movement statistics currently support only a `range` filter and always aggregate the whole
  warehouse.
- Reports have no dedicated warehouse-wide article price-movement section.

Contract Locks / Clarifications
- Statistics subsections should start collapsed and open on click. No single-open restriction is
  required unless implementation naturally chooses it.
- Reorder-zone drilldown must stay inside `Statistike`.
- The user selected `Option 2` for zone drilldown presentation:
  clicking a zone opens the related article list in a separate collapsible block inside the
  Statistics tab.
- Movement chart defaults to whole-warehouse mode but must support:
  - exact article filter
  - article category filter
- The movement helper note must be Croatian.
- Add a new warehouse-wide article price-movement section visible to `ADMIN` and `MANAGER`,
  sorted by most recent actual price change first while still surfacing the full article set.
- The price-movement section should expose enough context to review pricing changes without opening
  Warehouse article detail for every item.

File Ownership
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts` (only if needed)
- `frontend/src/pages/reports/__tests__/ReportsPage.test.tsx`
- `stoqio_docs/17_UI_REPORTS.md`
- `handoff/wave-09/phase-04-wave-09-reports-statistics-and-price-movement/backend.md`
- `handoff/wave-09/phase-04-wave-09-reports-statistics-and-price-movement/frontend.md`
- `handoff/wave-09/phase-04-wave-09-reports-statistics-and-price-movement/testing.md`

Delegation Plan
- Backend:
  - extend movement statistics to support optional article/category filtering
  - add a dedicated price-movement report endpoint/query
  - keep MANAGER access on read endpoints
  - add coverage for sorting and filters
- Frontend:
  - refactor Statistics into collapsed subsections
  - keep reorder-zone drilldown local to Statistics using the locked Option 2 pattern
  - localize the movement helper note
  - add article/category movement filters
  - add the new price-movement section to Reports
- Testing:
  - verify filters, drilldowns, section state, and price-movement report coverage

Acceptance Criteria
- Statistics subsections are collapsed by default and open on click.
- Reorder-zone drilldown no longer switches to Stock Overview.
- Movement chart note is Croatian.
- Movement chart supports default warehouse mode plus exact article and category filters.
- Reports expose a warehouse-wide price-movement section for ADMIN and MANAGER.
- Reports tests and frontend validations pass for touched behavior.

Validation Notes
- 2026-04-11: Orchestrator opened Wave 9 Phase 4 from the finalized Wave 9 feedback intake.

Next Action
- Backend, frontend, and testing workers implement and record their handoffs.
