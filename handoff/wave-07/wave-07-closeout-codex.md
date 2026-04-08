# Wave 7 Closeout Follow-Up — Codex

Date
- 2026-04-08

Author
- Codex, main orchestrator session

Context
- User reported that Wave 7 fixes were implemented and asked for a review.
- The review found several residual issues after the Phase 1-5 handoffs:
  approval bucket edits were still possible in a partially pending group,
  reject paths were not row-locked like approve paths, inventory count start
  still had an absent-row race, report exports were still paginated, receiving
  unique conflicts could surface as raw integrity errors, and deploy rollback
  capture used the wrong Alembic path.

Files Changed
- `backend/app/services/approval_service.py`
  - Added a group-level `FOR UPDATE` helper and used it before line/group approval
    and rejection actions.
  - `edit_aggregated_line()` now locks and checks the represented bucket itself,
    not only the persisted `DraftGroup.status`. This blocks editing an already
    approved/rejected bucket while another bucket keeps the group `PENDING`.
  - `reject_line()` and `reject_group()` now lock draft rows in deterministic id
    order, matching the approve path.
- `backend/app/services/inventory_service.py`
  - `start_count()` now maps active-count unique violations to a clean
    `COUNT_IN_PROGRESS` business error.
- `backend/app/models/inventory_count.py`
  - Added `uq_inventory_count_in_progress`, a partial unique index enforcing only
    one `IN_PROGRESS` inventory count.
- `backend/migrations/versions/b8c9d0e1f2a3_wave7_closeout_active_inventory_count.py`
  - New Alembic migration for the active inventory-count partial unique index.
  - Production note: if duplicate active counts already exist, complete/cancel
    them before running the migration.
- `backend/app/services/report_service.py`
  - `get_stock_overview()` and `get_surplus_report()` now accept `per_page=None`
    for rate-limited export paths.
  - `export_stock_overview()` and `export_surplus_report()` now request the full
    matching dataset instead of silently exporting page 1.
- `frontend/src/api/reports.ts`
  - Updated report contract comments: screen endpoint remains paginated, export
    bypasses pagination server-side.
  - Added `page` and `per_page` to `SurplusReportResponse`.
- `backend/app/api/receiving/routes.py`
  - Added `IntegrityError` handling for concurrent receiving unique conflicts,
    returning a clean 409 retry response instead of a raw 500.
- `scripts/deploy.sh`
  - Replaced inline trap quoting with `on_deploy_error()`.
  - Fixed Alembic pre-deploy capture to run from `backend/` via
    `$BACKEND_PYTHON -m alembic current`, instead of the nonexistent root
    `venv/bin/alembic`.
- Tests updated:
  - `backend/tests/test_approvals.py`
  - `backend/tests/test_phase2_models.py`
  - `backend/tests/test_reports.py`

Validation
- `cd backend && venv/bin/alembic heads`
  - Passed: one head, `b8c9d0e1f2a3`.
- `bash -n scripts/deploy.sh`
  - Passed.
- Targeted backend regression run:
  - `tests/test_approvals.py::TestConcurrencyHardening`
  - `tests/test_inventory_count.py::TestInventoryCountLocking`
  - `tests/test_phase2_models.py`
  - `tests/test_reports.py::test_stock_overview_export_requests_unpaginated_full_report`
  - `tests/test_reports.py::test_surplus_export_requests_unpaginated_full_report`
  - Result: 11 passed.
- `cd frontend && npm run build`
  - Passed.
- `cd frontend && npm run lint`
  - Passed.
- `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
  - Passed: 582 passed.

Residual Notes
- The report screen endpoints remain paginated by design. This closeout fixed
  full export behavior, not a full stock/surplus pagination UI redesign.
- The receiving conflict handling intentionally returns a retryable 409 on a
  database uniqueness race rather than trying to transparently merge/retry the
  request inside the route.
