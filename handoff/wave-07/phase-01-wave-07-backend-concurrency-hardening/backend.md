## 2026-04-08 Backend Concurrency Hardening Agent

Status
- blocked (tests not run — Bash execution permission denied by shell sandbox)

Scope
- Wave 7 Phase 1: remediate H-1, H-2, H-3, H-4, N-1, M-3 from 2026-04-08 dual-agent code review.
- Files owned: approval_service.py, inventory_service.py, employee_service.py.
- Also updated approvals/routes.py (minimal, necessary to surface ApprovalServiceError as HTTP 409 — no other route file touched).

Docs Read
- handoff/README.md
- handoff/wave-07/phase-01-wave-07-backend-concurrency-hardening/orchestrator.md
- handoff/decisions/decision-log.md (read; no new decisions required)
- backend/app/services/approval_service.py
- backend/app/services/inventory_service.py
- backend/app/services/employee_service.py
- backend/app/models/draft_group.py
- backend/app/models/draft.py
- backend/app/models/inventory_count.py
- backend/app/models/stock.py
- backend/app/services/receiving_service.py (lines 310–440, UOM validation pattern)
- backend/app/utils/errors.py
- backend/app/api/approvals/routes.py
- backend/tests/test_approvals.py
- backend/tests/test_inventory_count.py
- backend/tests/test_employees.py

Files Changed
- backend/app/services/approval_service.py
  - Added ApprovalServiceError exception class (mirrors InventoryServiceError / EmployeeServiceError)
  - H-1: edit_aggregated_line() — added DraftGroup status guard; raises ApprovalServiceError(409, GROUP_ALREADY_RESOLVED) when group.status in {APPROVED, REJECTED, PARTIAL}
  - H-2: _approve_pending_bucket() — replaced single-row lock on representative draft with lock on ALL DRAFT-status rows in the bucket, ordered by id ASC for deterministic lock order and deadlock prevention
  - N-1: approve_all() — added with_for_update() lock on DraftGroup row at function entry before the bucket loop; raises ValueError("Group not found.") if group does not exist

- backend/app/services/inventory_service.py
  - H-3 start_count(): added .with_for_update() to the IN_PROGRESS count check query
  - H-3 complete_count(): replaced db.session.get(InventoryCount, count_id) with a locked query (.filter_by(id=count_id).with_for_update().first()) before status check and all side-effect processing

- backend/app/services/employee_service.py
  - Added IntegrityError import from sqlalchemy.exc
  - _issuance_stock_row(): added for_update=False parameter; passes .with_for_update() to query when True
  - M-3 check_issuance(): after resolving article base UOM, validates data["uom"] against authoritative_uom; raises EmployeeServiceError(UOM_MISMATCH, 400) on mismatch, falls back to authoritative_uom if empty
  - M-3 create_issuance(): same UOM validation before stock check
  - H-4 create_issuance(): calls _issuance_stock_row(..., for_update=True) at the availability check; reuses the same locked row for the decrement; removed the redundant second _issuance_stock_row() call in the "Stock decrement" block; wraps stock_row.quantity -= quantity and flush() in try/except IntegrityError → maps to clean INSUFFICIENT_STOCK EmployeeServiceError

- backend/app/api/approvals/routes.py  (minimal addition only)
  - Imports ApprovalServiceError from approval_service
  - edit_aggregated_line route: wraps service call in try/except ApprovalServiceError → _error(exc.error, exc.message, exc.status_code, exc.details)
  - approve_all route: wraps service call in try/except ValueError → 404 on "not found", 400 otherwise

- backend/tests/test_approvals.py
  - Added TestConcurrencyHardening class with 4 tests:
    - test_h1_edit_rejected_group_returns_409: PATCH on REJECTED group → 409 GROUP_ALREADY_RESOLVED
    - test_h1_edit_approved_group_returns_409: PATCH on APPROVED group → 409 GROUP_ALREADY_RESOLVED
    - test_h1_edit_pending_group_still_allowed: PATCH on PENDING group → 200 (regression guard)
    - test_n1_approve_all_nonexistent_group_raises_error: approve_all on non-existent group_id → not 200

- backend/tests/test_employees.py
  - Added TestIssuanceUOMValidation class with 5 tests:
    - test_create_issuance_wrong_uom_returns_400: wrong UOM → 400 UOM_MISMATCH
    - test_check_issuance_wrong_uom_returns_400: wrong UOM in check → 400 UOM_MISMATCH
    - test_create_issuance_correct_uom_succeeds: correct UOM → 201
    - test_create_issuance_no_uom_falls_back_to_base: no UOM → 201 with base UOM
    - test_check_issuance_no_uom_falls_back_to_base: no UOM in check → no UOM_MISMATCH error

- backend/tests/test_inventory_count.py
  - Added TestInventoryCountLocking class with 2 tests:
    - test_complete_count_idempotent_rejection: completing an already-COMPLETED count → 400 COUNT_NOT_IN_PROGRESS
    - test_start_count_rejects_duplicate: starting when IN_PROGRESS exists → 400 COUNT_IN_PROGRESS

Commands Run
```bash
# BLOCKED — Bash execution permission denied by shell sandbox.
# Command to run (must be run by orchestrator or user):
cd /Users/grzzi/Desktop/STOQIO/backend && venv/bin/python -m pytest tests/ -q --tb=short
```

Tests
- Passed: N/A — Bash permission blocked; tests not run
- Failed: N/A
- Not run: All tests (Bash sandbox denied). Orchestrator must run tests manually.

Open Issues / Risks

1. **Bash blocked — tests unverified**: All code changes are implemented and reviewed for correctness, but the full test suite has NOT been executed. The orchestrator must grant Bash permission and run `cd backend && venv/bin/python -m pytest tests/ -q --tb=short` to verify. Any failures must be fixed before marking this phase complete.

2. **H-3 start_count() race window**: The with_for_update() on the IN_PROGRESS check helps when a row already exists, but if no IN_PROGRESS count exists at the moment both concurrent requests read, neither gets a lock and both can insert. A DB-level unique constraint on IN_PROGRESS state (Phase 2 scope, schema/migration change) is the complete fix for this edge case.

3. **N-2 advisory check_issuance (by design)**: check_issuance() is explicitly advisory — its result is not guaranteed to hold by the time create_issuance() is called. This is by design and acceptable. The create_issuance() path performs its own locked availability check (H-4).

4. **approvals/routes.py touched**: The orchestrator's File Ownership section lists only the three service files, but the H-1 acceptance criteria requires HTTP 409 from the edit_aggregated_line endpoint. The route had no try/except for ApprovalServiceError. The minimal addition (import + try/except in two routes) was necessary. No serialization logic, no other routes, no other files were changed.

Next Recommended Step
- Orchestrator grants Bash permission and runs: `cd /Users/grzzi/Desktop/STOQIO/backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Review any failures and fix. Known risk area: inventory count tests may be order-sensitive (they use a shared IN_PROGRESS count state via module-scoped fixture).
- If all tests pass, mark Phase 1 Backend complete and proceed to integration with Phases 2–5.
