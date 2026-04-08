## Phase Summary

Phase
- Wave 6 - Phase 1 - Backend Security Core

Objective
- Remediate nine Critical/High/Medium backend security findings from the 2026-04-08 code review:
  K-1 (JWT algorithm not pinned), K-3 (approval double-spend race), K-4 (missing HSTS),
  V-3 (pagination no upper bound), V-5 (formula injection in Excel exports),
  V-7 (Surplus no CHECK constraint), S-1 (revoked token unbounded growth),
  S-2 (soft-delete inconsistent in _get_article), S-3 (negative override_quantity).

Source Docs
- `handoff/README.md`
- `handoff/wave-06/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-012 for revoked token, DEC-SEC-001 new)
- `backend/app/config.py`
- `backend/app/__init__.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/article_service.py`
- `backend/app/services/report_service.py`
- `backend/app/models/surplus.py`
- `backend/app/models/revoked_token.py`
- `backend/app/commands.py`
- `backend/migrations/` (for new Alembic migration)
- `backend/tests/` (for regression check and new tests)

Current Repo Reality
- `JWT_ALGORITHM` is never set in `config.py`. Flask-JWT-Extended defaults to HS256 but
  this is not enforced, leaving a theoretical none-algorithm substitution window.
- `__init__.py` sets CSP, X-Frame-Options, Referrer-Policy, X-Content-Type-Options but
  NOT Strict-Transport-Security or Permissions-Policy.
- `approval_service.py` `_approve_pending_bucket()`: draft is read without `with_for_update()`
  at lines ~302-307, then Stock/Surplus are locked AFTER the decision. Two concurrent approvals
  of the same bucket can both read DRAFT status and deduct the same stock twice.
- `report_service.py` per_page is not bounded above; `per_page=999999999` triggers DoS.
- `report_service.py` Excel export uses `sanitize_cell()` selectively; rejection reasons and
  notes can carry formula-injection payloads into Excel exports.
- `models/surplus.py` has no `CHECK (quantity >= 0)` constraint. `models/stock.py` has
  `ck_stock_quantity_gte_zero`. Surplus is inconsistent.
- `commands.py` purge_revoked_tokens runs only on manual CLI invocation; no automatic cleanup.
  The revoked_token table grows unbounded.
- `article_service.py` `_get_article()` does NOT filter `is_active=True`.
  `get_article_detail()` can return a deactivated article without warning.
- `approval_service.py` `edit_aggregated_line()` accepts `new_quantity` as Decimal without
  validating it is >= 0. A negative value silently adds stock.

Contract Locks / Clarifications
- Do NOT change JWT token expiry durations or response shapes.
- Do NOT migrate refresh tokens to cookies — that is a separate scoped decision.
- The approval_service fix must use `with_for_update(nowait=False)` (blocking lock, not skip).
- The `_get_article()` is_active fix MUST verify that no existing test or service deliberately
  fetches deactivated articles by ID (e.g., admin soft-delete verification endpoints).
  If any such path exists, add a separate `_get_article_including_inactive()` helper instead
  of breaking the admin verify flow — do not silently drop functionality.
- sanitize_cell() must be applied to ALL user-controlled string fields in ALL export paths,
  not just the ones already covered.
- Surplus CHECK constraint requires an Alembic migration. Follow existing migration patterns.
- Revoked token auto-cleanup: add an `@app.before_request` hook that runs cleanup at most
  once per hour (track last run in app state). Do NOT add APScheduler or any new dependency.
- Do NOT change rate limiting logic in this phase — that is Phase 2.

Delegation Plan
- Backend:
  - Add `JWT_ALGORITHM = "HS256"` to both Development and Production config classes
  - Add `Strict-Transport-Security` and `Permissions-Policy` to `after_request` security headers
  - Fix `_approve_pending_bucket()`: add `with_for_update()` to the draft read query
  - Add `per_page = min(per_page, 200)` cap in any function using per_page pagination
  - Apply `sanitize_cell()` to all user-controlled string fields in all Excel export paths
  - Write Alembic migration adding `CHECK (quantity >= 0)` to `surplus.quantity`
  - Add `is_active.is_(True)` filter to `_get_article()` — verify no admin path breaks
  - Add `>= 0` validation for `new_quantity` in `edit_aggregated_line()`
  - Add automatic expired-revoked-token cleanup (at most once per hour) in `__init__.py`
  - Write/update backend tests to cover all fixes
  - Document work in `handoff/wave-06/phase-01-wave-06-backend-security-core/backend.md`
- Testing:
  - Verify all existing tests still pass
  - Confirm new Alembic head is single
  - Run regression suite
  - Document in `testing.md`

Acceptance Criteria
- `config.py` Development and Production both set `JWT_ALGORITHM = "HS256"`
- HTTP response headers include `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  and `Permissions-Policy: geolocation=(), camera=(), microphone=()`
- Concurrent approval test: two threads approving the same bucket simultaneously result in
  exactly one approval succeeding and one failing with InsufficientStock — NOT both succeeding
- All paginated endpoints cap `per_page` at 200 maximum
- All user-controlled string fields in Excel exports pass through `sanitize_cell()`
- `venv/bin/alembic heads` reports a single head after new migration
- `SELECT quantity FROM surplus WHERE quantity < 0` returns zero rows on any valid state
- `article_service.get_article_detail()` returns 404 for an article where `is_active=False`
- `edit_aggregated_line()` returns a validation error for `new_quantity < 0`
- Expired revoked tokens are automatically purged (last_cleanup tracked in app state)
- All pre-existing tests pass without modification
- Handoff files exist and follow the required `handoff/README.md` section shape

Validation Notes
- 2026-04-08: Orchestrator created Wave 6 Phase 1 handoff and delegated to backend agent.
- 2026-04-08 10:40 CEST: Backend agent completed all 9 fixes. Surplus migration had SQLite batch-mode issue (DEC-BE-015 pattern) — fixed by orchestrator. Merge migration created for Phase 1 + Phase 2 heads. 4 tests updated to match new scrypt/moderate-audit-level baseline.
- 2026-04-08 10:45 CEST: Full backend suite: 567 passed, 0 failed. Phase 1 closed.

Next Action
- Backend agent implements all fixes above.
- Testing agent verifies after backend completes.


---

## Delegation Prompt — Backend Agent

You are the backend security remediation agent for Wave 6 Phase 1 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-06/phase-01-wave-06-backend-security-core/orchestrator.md` (this file's parent)
- `handoff/decisions/decision-log.md`
- `backend/app/config.py`
- `backend/app/__init__.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/article_service.py`
- `backend/app/services/report_service.py`
- `backend/app/models/surplus.py`
- `backend/app/models/stock.py` (for CHECK constraint pattern reference)
- `backend/app/models/revoked_token.py`
- `backend/app/commands.py`
- `backend/tests/` (list and read relevant test files)

Your fixes (implement all of them):

1. **JWT_ALGORITHM pinning** (`backend/app/config.py`)
   Add `JWT_ALGORITHM = "HS256"` to both `Development` and `Production` config classes.

2. **HSTS + Permissions-Policy headers** (`backend/app/__init__.py`)
   In the `after_request` security-headers hook, add:
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

3. **Approval double-spend race** (`backend/app/services/approval_service.py`)
   In `_approve_pending_bucket()`, the draft must be read with a row-level lock BEFORE
   the decision. Find where the draft/bucket is first read and add `.with_for_update()`.
   The lock must happen before checking status or quantities.

4. **Pagination upper bound** (all files that use per_page)
   Cap `per_page` at 200 in every paginated query. Find all uses of `per_page` from
   request arguments and add `per_page = min(per_page, 200)`. Check `report_service.py`,
   `article_service.py`, and any other service with pagination.

5. **Formula injection — sanitize_cell() completeness** (`backend/app/services/report_service.py`)
   Read the full Excel export functions. Apply `sanitize_cell()` to EVERY user-controlled
   string field (article_no, description, batch_code, notes, rejection_reason, reference,
   supplier_name, employee names, any text field from user input). Do not leave any string
   field unsanitized in any `_build_xlsx()` or equivalent function.

6. **Surplus CHECK constraint** (new Alembic migration)
   Create a new migration that adds `CHECK (quantity >= 0)` to `surplus.quantity`.
   Follow the pattern in existing migrations. Make sure `venv/bin/alembic heads` shows
   a single head after the migration is added. Name it descriptively:
   `add_surplus_quantity_non_negative_check`.

7. **is_active filter in _get_article()** (`backend/app/services/article_service.py`)
   Add `.filter(Article.is_active.is_(True))` to `_get_article()`. Before doing this,
   search for all callers of `_get_article()` and verify none of them legitimately need
   to fetch deactivated articles. If any admin path (like the deactivation confirmation)
   needs to fetch inactive articles, create a separate `_get_article_including_inactive()`
   helper for that path only. Do not silently break any functionality.

8. **Negative override_quantity validation** (`backend/app/services/approval_service.py`)
   In `edit_aggregated_line()`, after parsing `new_quantity`, validate it is >= 0.
   If negative, raise a ValueError or return an appropriate HTTP 400 error.

9. **Automatic revoked token cleanup** (`backend/app/__init__.py`)
   Add a `@app.before_request` handler that runs expired revoked token cleanup at most
   once per hour. Use a module-level variable `_last_token_cleanup = None` and check
   `datetime.now(timezone.utc) - _last_token_cleanup > timedelta(hours=1)` before
   running the cleanup. The cleanup should delete rows where `expires_at < now()`.
   Do NOT add any new package dependency.

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Run: `venv/bin/alembic heads`
- Fix any failures before completing
- Write your entry in `handoff/wave-06/phase-01-wave-06-backend-security-core/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
