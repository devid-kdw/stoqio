## [2026-04-08 10:45] Backend Agent — Wave 6 Phase 2

### Status
completed

### Scope
Implemented all 4 IDOR and authorization fixes from the 2026-04-08 security review:
1. Draft PATCH/DELETE ownership check (K-2)
2. Paginated stock_overview and surplus_report in report_service (V-4)
3. Rate limiting on barcode PDF and report export endpoints (V-12)
4. Composite index migration on login_attempt(bucket_key, attempted_at) (N-1)

### Docs Read
- `handoff/wave-06/phase-02-wave-06-backend-idor-authorization/orchestrator.md`
- `handoff/decisions/decision-log.md` (DEC-BE-013, DEC-SEC-003)
- `backend/app/api/drafts/routes.py`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`
- `backend/app/api/articles/routes.py`
- `backend/app/models/login_attempt.py`
- `backend/app/utils/auth.py`
- `backend/migrations/versions/` (existing migrations for pattern)

### Files Changed
- `backend/app/api/drafts/routes.py` — added ownership check to `update_draft` (PATCH) and `delete_draft` (DELETE); ADMIN bypasses; OPERATOR/SUPERVISOR must match `draft.created_by`; uses existing `get_current_user()` pattern
- `backend/app/services/report_service.py` — `get_stock_overview()` and `get_surplus_report()` now accept `page` (default 1) and `per_page` (default 100, capped 500); return `{items, total, page, per_page, ...}` instead of flat list
- `backend/app/api/reports/routes.py` — stock_overview and surplus route handlers read `page`/`per_page` from `request.args` and pass to service
- `backend/app/api/articles/routes.py` — `GET /articles/<id>/barcode` and `GET /batches/<id>/barcode` guarded with 30 req/min per-IP rate limit
- `backend/app/api/reports/routes.py` — all three export endpoints guarded with same 30 req/min per-IP rate limit
- `backend/migrations/versions/d5e6f7a8b9c0_add_composite_index_login_attempt_bucket_key_attempted_at.py` — NEW migration; chained from c0d1e2f3a4b5; creates ix_login_attempt_bucket_key_attempted_at on (bucket_key, attempted_at)

### Commands Run
```bash
# Orchestrator ran final suite verification:
cd /Users/grzzi/Desktop/STOQIO/backend
venv/bin/python -m pytest tests/ -q --tb=short
# Result: 567 passed

venv/bin/alembic heads
# Result: fcb524a92fa4 (head) — single head after merge migration
```

### Tests
- Before: 567 passed (full suite baseline)
- After: 567 passed (no regressions)
- Merge migration `fcb524a92fa4` created by orchestrator to combine Phase 1 (d1e2f3a4b5c6) and Phase 2 (d5e6f7a8b9c0) heads into single head

### Open Issues / Risks
- The rate limiting on export endpoints uses the same per-IP bucket key `"export:{ip}"` across all export types. If a user legitimately generates multiple reports in sequence, 30/min may feel restrictive. Can be tuned if needed.
- Pagination on stock_overview changes the API response shape (adds `total`, `page`, `per_page`). Any frontend that calls these report endpoints and expects a flat array needs to be updated. Verify frontend report pages consume the new paginated shape.

### Next Recommended Step
- Frontend team should verify ReportsPage.tsx handles the new `{items, total, page, per_page}` response shape for stock overview and surplus reports.
- Testing agent should add regression tests for IDOR (OPERATOR A cannot modify OPERATOR B's draft).
