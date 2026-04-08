## Phase Summary

Phase
- Wave 6 - Phase 2 - Backend IDOR and Authorization

Objective
- Remediate four Critical/High/Info backend authorization findings from the 2026-04-08 review:
  K-2 (IDOR on drafts — any operator can modify/delete any draft),
  V-4 (list endpoints without pagination — report_service .all() calls),
  V-12 (no rate limiting on expensive endpoints — barcode PDF, report exports),
  N-1 (LoginAttempt missing composite index for rate limit query performance).

Source Docs
- `handoff/README.md`
- `handoff/wave-06/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-013 for draft group model context)
- `backend/app/api/drafts/routes.py`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`
- `backend/app/api/articles/routes.py` (barcode endpoints)
- `backend/app/models/login_attempt.py`
- `backend/app/utils/auth.py` (check_rate_limit, rate_limit_check decorator)
- `backend/migrations/` (for new Alembic migration — composite index)
- `backend/tests/test_drafts.py` (if exists) and related test files

Current Repo Reality
- `api/drafts/routes.py` PATCH and DELETE endpoints retrieve draft by ID without checking
  `draft.created_by == current_user.id`. Any authenticated OPERATOR can modify or delete
  any other user's draft line. ADMIN should be exempt from this check (admin oversight).
- `report_service.py` `get_stock_overview()` and `get_surplus_report()` call `.all()` on
  their queries with no pagination, loading every row into memory on large datasets.
- Barcode PDF endpoints (`GET /api/v1/articles/<id>/barcode`,
  `GET /api/v1/batches/<id>/barcode`) and report export endpoints have no rate limiting.
  An attacker can trigger hundreds of PDF/Excel generations in parallel.
- `models/login_attempt.py` has only a single-column index on `bucket_key`. The
  `check_rate_limit()` query in `utils/auth.py` filters on both `bucket_key` AND
  `attempted_at >= window_start`. A composite index would serve this query properly.

Contract Locks / Clarifications
- IDOR fix: ADMIN role must NOT be blocked by the ownership check — only OPERATOR and
  SUPERVISOR should be owner-restricted. Read how @require_role works before implementing.
- IDOR fix: The ownership check must be on `draft.created_by == current_user.id`. Do not
  use any other ownership field.
- Do NOT add APScheduler or any new dependency for rate limiting on endpoints. Use the
  existing `check_rate_limit` / decorator pattern from `utils/auth.py` if suitable, or
  Flask's g object for simple request-level guards. Keep it simple.
- For report pagination: add `page` and `per_page` query parameters with sensible defaults
  (per_page=100 for stock overview, per_page=100 for surplus). Cap at 500. Update the
  response shape to include `{ items, total, page, per_page }` for these endpoints.
  This IS a response-shape change — document it in this handoff as a new decision log entry.
- The composite index is additive — it does not remove the existing single-column index.
  A separate migration is preferred over modifying the existing one.
- Do NOT change any other auth utils, rate limiting logic, or other route files.

Delegation Plan
- Backend:
  - Add ownership check to PATCH and DELETE `/api/v1/drafts/<id>` endpoints
  - Add pagination to `get_stock_overview()` and `get_surplus_report()` in report_service.py
  - Update the corresponding routes in `api/reports/routes.py` to pass page/per_page
  - Add simple rate limiting to barcode PDF endpoints and report export endpoints
  - Write Alembic migration adding composite index `(bucket_key, attempted_at)`
    to `login_attempt` table
  - Write/update backend tests for IDOR fix and pagination
  - Document in `backend.md`
- Testing:
  - Verify IDOR: OPERATOR A cannot PATCH/DELETE OPERATOR B's draft
  - Verify ADMIN CAN PATCH/DELETE any draft
  - Verify paginated stock overview and surplus report responses
  - All pre-existing tests pass
  - Document in `testing.md`

Acceptance Criteria
- PATCH `/api/v1/drafts/<id>` by OPERATOR who did NOT create that draft returns 403
- DELETE `/api/v1/drafts/<id>` by OPERATOR who did NOT create that draft returns 403
- ADMIN can PATCH and DELETE any draft regardless of creator
- `GET /api/v1/reports/stock-overview` accepts `page` and `per_page` and returns
  `{ items, total, page, per_page }` — does not load all rows into memory
- `GET /api/v1/reports/surplus` (or equivalent) is similarly paginated
- Barcode PDF and report export endpoints have basic rate limiting
- `venv/bin/alembic heads` reports a single head
- All pre-existing tests pass
- Handoff files follow the required section shape

Validation Notes
- 2026-04-08: Orchestrator created Wave 6 Phase 2 handoff.
- 2026-04-08 10:45 CEST: Backend agent completed all 4 fixes. Migration d5e6f7a8b9c0 branched from same parent as Phase 1 migration — resolved with merge migration fcb524a92fa4. Final suite: 567 passed, single Alembic head confirmed.
- 2026-04-08 10:45 CEST: Phase 2 closed. Note: report pagination changes response shape for stock_overview/surplus — frontend pages should verify compatibility.

Next Action
- Backend agent implements all fixes. Can run in parallel with Phase 1 and Phase 3.


---

## Delegation Prompt — Backend Agent

You are the backend IDOR and authorization remediation agent for Wave 6 Phase 2 of the
STOQIO WMS project. This phase runs in parallel with Phases 1 and 3.

Read before coding:
- `handoff/README.md`
- `handoff/wave-06/phase-02-wave-06-backend-idor-authorization/orchestrator.md`
- `handoff/decisions/decision-log.md`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`
- `backend/app/api/articles/routes.py`
- `backend/app/models/login_attempt.py`
- `backend/app/utils/auth.py`
- `backend/tests/` (find and read draft-related and report-related tests)

Your fixes (implement all of them):

1. **IDOR on Draft PATCH/DELETE** (`backend/app/api/drafts/routes.py`)
   In the PATCH (update_draft) and DELETE (delete_draft) endpoint handlers, after
   fetching the draft by ID (and confirming it exists), add an ownership check:
   ```python
   if current_user.role not in ("ADMIN",) and draft.created_by != current_user.id:
       return error_response(403, "FORBIDDEN", "Access denied")
   ```
   ADMIN bypasses ownership. OPERATOR and SUPERVISOR are owner-restricted.
   Check how `current_user` is obtained in this file (likely `get_jwt_identity()` or
   similar). Read the existing pattern carefully before implementing.

2. **Paginate stock_overview and surplus_report** (`backend/app/services/report_service.py`
   and `backend/app/api/reports/routes.py`)
   - In `get_stock_overview()` (or equivalent): add `page: int = 1` and
     `per_page: int = 100` parameters, cap per_page at 500, apply `.paginate()` or
     `.offset().limit()` and return `{ items: [...], total: int, page: int, per_page: int }`.
   - Do the same for the surplus report endpoint.
   - Update the route handlers to accept `page` and `per_page` from query string and
     pass them to the service.
   - Keep backward compat: if no page/per_page is provided, default to page=1, per_page=100.

3. **Rate limiting on expensive endpoints** (`backend/app/api/articles/routes.py` barcode
   endpoints and `backend/app/api/reports/routes.py` export endpoints)
   Add a simple per-IP rate limit using the existing `check_rate_limit` mechanism from
   `backend/app/utils/auth.py`. Apply a limit of 30 requests per minute per IP to:
   - `GET /api/v1/articles/<id>/barcode`
   - `GET /api/v1/batches/<id>/barcode`
   - All `GET` export endpoints that generate PDF or Excel files
   Return 429 if limit is exceeded. Follow the exact same pattern as auth rate limiting.

4. **Composite index on LoginAttempt** (new Alembic migration)
   Create a migration that adds a composite index `ix_login_attempt_bucket_key_attempted_at`
   on `(bucket_key, attempted_at)` to the `login_attempt` table. This is additive and does
   not remove the existing `bucket_key` single-column index.
   Run `venv/bin/alembic heads` to confirm single head after adding.

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Run: `venv/bin/alembic heads`
- Fix any failures before completing
- Write your entry in `handoff/wave-06/phase-02-wave-06-backend-idor-authorization/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
