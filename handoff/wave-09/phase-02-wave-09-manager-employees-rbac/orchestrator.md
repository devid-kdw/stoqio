## Phase Summary

Phase
- Wave 9 - Phase 2 - MANAGER Employees RBAC

Objective
- Remediate W9-F-004:
  MANAGER must gain read-only access to the Employees module without inheriting ADMIN-only
  mutation powers.

Source Docs
- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/15_UI_EMPLOYEES.md`
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/employees/EmployeesPage.tsx`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `backend/app/api/employees/routes.py`
- `backend/tests/test_employees.py`

Current Repo Reality
- Sidebar and route guards expose Employees only to `ADMIN` and `WAREHOUSE_STAFF`.
- Backend employees GET endpoints are limited to `ADMIN` and `WAREHOUSE_STAFF`.
- Employee create/edit/deactivate plus issuance check/create remain ADMIN-only.
- Employee screens already hide mutation UI behind `isAdmin` checks in the frontend.

Contract Locks / Clarifications
- MANAGER access in this wave is read-only:
  - list employees
  - employee detail
  - quota overview
  - issuance history
- MANAGER must not gain:
  - create/update/deactivate employee
  - issuance article lookup
  - issuance check
  - issuance create
- Update docs so the accepted RBAC baseline reflects the new MANAGER visibility.

File Ownership
- `backend/app/api/employees/routes.py`
- `backend/tests/test_employees.py`
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/employees/EmployeesPage.tsx`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/15_UI_EMPLOYEES.md`
- `handoff/wave-09/phase-02-wave-09-manager-employees-rbac/backend.md`
- `handoff/wave-09/phase-02-wave-09-manager-employees-rbac/frontend.md`
- `handoff/wave-09/phase-02-wave-09-manager-employees-rbac/testing.md`

Delegation Plan
- Backend:
  - extend Employees read endpoint authorization to include `MANAGER`
  - preserve ADMIN-only mutation endpoints
  - add regression coverage for MANAGER read access and mutation denial
- Frontend:
  - show Employees in the sidebar for MANAGER
  - allow MANAGER route access to Employees screens
  - keep all mutation controls hidden/disabled for MANAGER
- Testing:
  - verify read-only RBAC end-to-end and no mutation regression

Acceptance Criteria
- MANAGER sees `Zaposlenici` in the sidebar and can open Employees list/detail routes.
- MANAGER can view quotas and issuance history.
- MANAGER cannot mutate employees or create personal issuances.
- Backend and frontend validations pass for touched files.

Validation Notes
- 2026-04-11: Orchestrator opened Wave 9 Phase 2 from the finalized Wave 9 feedback intake.
- 2026-04-11: Orchestrator reviewed `backend.md`, `frontend.md`, and `testing.md` plus the actual
  repo diff across:
  - `backend/app/api/employees/routes.py`
  - `backend/tests/test_employees.py`
  - `frontend/src/routes.tsx`
  - `frontend/src/components/layout/Sidebar.tsx`
  - `stoqio_docs/03_RBAC.md`
  - `stoqio_docs/15_UI_EMPLOYEES.md`
- 2026-04-11: Orchestrator re-ran validation:
  - `backend/venv/bin/python -m pytest backend/tests/test_employees.py -q --tb=short` — passed
    (`61 passed in 1.23s`)
  - `cd frontend && npm run lint` — passed
  - `cd frontend && npm run build` — passed
- 2026-04-11: Accepted work:
  - backend read-only RBAC was widened to include `MANAGER` only on Employees GET endpoints
  - ADMIN-only mutation paths remained unchanged
  - frontend sidebar and route guards now expose Employees to `MANAGER`
  - employee mutation UI remains effectively ADMIN-only through existing `isAdmin` guards
  - RBAC and Employees docs were aligned to the accepted behavior
- 2026-04-11: No blocking findings remained after orchestrator review. Phase 2 is complete.

Next Action
- Proceed to the next Wave 9 implementation phase.
