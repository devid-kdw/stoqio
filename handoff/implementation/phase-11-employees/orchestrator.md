## Phase Summary

Phase
- Phase 11 - Employees

Objective
- Deliver the Employees module end to end:
- employee list and employee detail screens
- personal issuance workflow for ADMIN
- quota overview and issuance history for ADMIN and WAREHOUSE_STAFF
- dedicated issuance article lookup and dry-run quota check contracts

Source Docs
- `stoqio_docs/15_UI_EMPLOYEES.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 8
- `stoqio_docs/05_DATA_MODEL.md` § 5, § 19, § 20, § 21
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/decisions/decision-log.md`
- `handoff/README.md`

Delegation Plan
- Backend:
- Implement Employees API, issuance workflow, quota logic, lookup/check endpoints, and backend integration coverage.
- Frontend:
- Replace `/employees` placeholders with real list/detail pages and wire the issuance UI to the dedicated Phase 11 backend contract.
- Testing:
- Verify backend Employees coverage and keep the full backend suite green.

Acceptance Criteria
- ADMIN can create, edit, deactivate, and inspect employees.
- WAREHOUSE_STAFF can view employees, quotas, and issuance history but cannot mutate.
- Issuance lookup returns only personal-issue articles.
- Issuance check/create returns `issued_by` as username, not user id.
- Quota warning/block behavior follows the locked priority rules.
- Phase 11 leaves a complete handoff trail across orchestration, backend, frontend, and testing.

Validation Notes
- Initial post-agent review found two issues:
- the insufficient-stock path in personal issuance still allowed a successful issuance/transaction while leaving stock unchanged
- this phase folder was missing `orchestrator.md`, so the handoff trace was incomplete
- Testing handoff also ended with a stale "Proceed to frontend documentation and implementation" note even though frontend delivery was already complete. Per `handoff/README.md`, this orchestrator file is the canonical closeout record and supersedes that stale next-step line without editing the testing agent's file.

Next Action
- Apply orchestrator follow-up remediation, rerun verification, then formally close Phase 11 if green.

## Orchestrator Follow-Up - 2026-03-14 CET

Status
- Follow-up remediation applied directly by orchestrator after review.

Accepted Work
- Backend, frontend, and testing agent deliveries remain accepted as the Phase 11 baseline.

Rejected / Missing Items
- The original backend issuance flow accepted insufficient-stock requests.
- The original frontend create flow did not redirect to employee detail after create, contrary to the Employees UI spec.
- The phase lacked the required `orchestrator.md` trace.

Orchestrator Changes
- `backend/app/services/employee_service.py`
- `backend/tests/test_employees.py`
- `frontend/src/pages/employees/EmployeesPage.tsx`
- `stoqio_docs/15_UI_EMPLOYEES.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-11-employees/orchestrator.md`

What Changed
- Personal issuance now blocks with `400 INSUFFICIENT_STOCK` during both dry-run check and final create when the requested quantity exceeds the available stock row.
- Batch-tracked issuance now distinguishes "no available batches" from "selected batch exists but requested quantity exceeds available stock".
- Regression tests were added for insufficient-stock failures on both batch and non-batch issuance paths, and to assert no issuance/transaction is persisted on rejection.
- Employee creation now redirects to the employee detail page after a successful create, matching the UI spec.
- The Employees UI doc now explicitly documents the insufficient-stock edge case.
- `DEC-EMP-003` records the orchestrator decision that supersedes the earlier permissive stock fallback.

Verification
- `backend/venv/bin/pytest backend/tests/test_employees.py -q`
- `backend/venv/bin/pytest backend/tests -q`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Residual Notes
- The stale next-step line in `handoff/implementation/phase-11-employees/testing.md` reflected a backend-only testing review that was not updated after frontend completion. This closeout note supersedes it.
- `Settings` remains a placeholder, so the admin quota-management button on the employee detail page still leads to the existing scaffold. That is expected for the current phase boundary.

Next Action
- Phase 11 can be treated as formally closed once this orchestrator closeout note and `DEC-EMP-003` are accepted as the final baseline.
