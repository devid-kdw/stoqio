## Phase Summary

Phase
- Wave 7 - Phase 1 - Backend Concurrency and Transactional Integrity Hardening

Objective
- Remediate six service-layer findings from the 2026-04-08 dual-agent code review:
  H-1 (approval quantities mutable after resolution),
  H-2 (approval double-spend — intra-bucket race on different draft IDs),
  H-3 (inventory count start/complete race-prone),
  H-4 (employee issuance can overspend stock),
  N-1 (approve_all has no group-level lock — deadlock/duplicate-processing risk),
  M-3 (employee issuance accepts arbitrary client UOM without validation).

Source Docs
- `handoff/README.md`
- `handoff/wave-07/README.md`
- `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (H-1, H-2, H-3, H-4, M-3)
- `handoff/Findings/wave-06-second-opinion-review.md` (H-1 through H-4, N-1, M-3 sections)
- `handoff/decisions/decision-log.md`
- `backend/app/services/approval_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/employee_service.py`
- `backend/app/models/draft.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/stock.py`

Current Repo Reality
- `approval_service.py` `edit_aggregated_line()`: loads the Draft to verify group membership but never
  checks `draft.status == 'DRAFT'` or that the group is still actionable. An ApprovalOverride can be
  upserted after resolution with no guard, silently replacing the audited outcome.
- `approval_service.py` `_approve_pending_bucket()`: acquires `with_for_update()` only on the
  representative draft row (one specific line_id), then re-queries all bucket drafts without holding
  a lock on them. Two concurrent requests using different draft IDs from the same bucket do not
  contend on the same representative row and can both pass the status check.
- `approval_service.py` `approve_all()`: loops over buckets and calls `_approve_pending_bucket()`
  per bucket with no group-level lock. Two concurrent `approve_all()` calls on the same group can
  interleave. Due to the per-bucket `with_for_update()`, the likely outcome is a deadlock or one
  request failing — not a clean double-approval of all buckets — but this is still a risk that
  must be closed with a group-level lock. Describe the risk accurately: deadlock/failure risk, not
  guaranteed double-approval.
- `inventory_service.py` `start_count()`: checks for existing IN_PROGRESS count with a plain SELECT
  (no `with_for_update()`). Concurrent start requests can both see no IN_PROGRESS count and both
  insert, creating two active counts.
- `inventory_service.py` `complete_count()`: checks count status without locking the count row.
  Concurrent completion requests can both pass the status check and both process side effects
  (surplus, shortage drafts, transactions).
- `employee_service.py` `create_issuance()`: reads stock for the availability check but does not
  hold a lock on the stock row through the decrement. `CHECK (quantity >= 0)` on the stock table
  prevents silent negative stock but converts the race into a crash (integrity error) rather than
  a graceful business error.
- `employee_service.py` `check_issuance()` and `create_issuance()`: accept `data["uom"]` without
  validating it against the article's `base_uom`. `receiving_service.py` already validates UOM and
  rejects mismatches — that pattern must be copied here.

Contract Locks / Clarifications
- **H-1 status guard**: In `edit_aggregated_line()`, after loading the Draft, check that the
  associated DraftGroup is still in an actionable state. If the group status is APPROVED, REJECTED,
  or PARTIAL-RESOLVED, return HTTP 409 with a clear error message. Do not change the override upsert
  logic itself, only add the guard before it.
- **H-2 bucket locking**: In `_approve_pending_bucket()`, replace the single-row lock on the
  representative draft with a lock on ALL pending (DRAFT status) rows in the bucket. Use
  `with_for_update()` on the full bucket query, ordered deterministically (e.g., by `id ASC`) to
  prevent deadlocks between two concurrent requests that might lock in different orders.
- **N-1 group lock**: At the start of `approve_all()`, acquire a `with_for_update()` lock on the
  DraftGroup row itself before entering the bucket loop. This ensures two concurrent `approve_all()`
  calls serialize at the group level. Describe this in backend.md as preventing deadlock/failure
  risk from concurrent calls, not as preventing guaranteed double-approval.
- **H-3 inventory count locking**:
  - In `start_count()`: use `with_for_update()` on the IN_PROGRESS count check query so the read
    and the subsequent insert are atomic within the transaction.
  - In `complete_count()`: acquire `with_for_update()` on the InventoryCount row before reading
    its status and processing side effects.
  - Do NOT add a DB-level unique constraint on IN_PROGRESS state here — that belongs to Phase 2
    scope and is a schema/migration change.
- **H-4 employee issuance locking**: In `create_issuance()`, lock the stock row with
  `with_for_update()` at the point of the availability check and hold the lock through the
  decrement. Map any integrity errors caused by a race (if CHECK constraint fires) to the same
  business error as insufficient stock, so the user sees a clean message.
- **M-3 UOM validation**: In both `check_issuance()` and `create_issuance()`, after resolving
  the article and its base UOM, validate that `data["uom"]` (if non-empty) matches the article's
  base UOM code. If it does not match, return the same error shape as `receiving_service.py` does
  for UOM_MISMATCH. Read `receiving_service.py:318-329` and `receiving_service.py:417-428` for
  the exact pattern to copy.
- **N-2 (advisory only)**: No code change needed for the dry-run/create coupling. Document in
  `backend.md` that `check_issuance()` is explicitly advisory — its result is not guaranteed to
  hold by the time `create_issuance()` is called.
- Do NOT change API response shapes, token handling, or model/migration schema in this phase.
- Do NOT touch `approval_service.py` serialization logic, only locking and status guard paths.

File Ownership (this phase only — do not touch other files)
- `backend/app/services/approval_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/employee_service.py`
- `handoff/wave-07/phase-01-wave-07-backend-concurrency-hardening/backend.md` (agent writes here)

Delegation Plan
- Backend: implement all six fixes above, write tests, document in backend.md
- Testing: verify suite passes, no regressions

Acceptance Criteria
- `edit_aggregated_line()` returns HTTP 409 when called on a group that is not in a pending/actionable state
- Two concurrent requests with different draft IDs in the same bucket do not both succeed
- Two concurrent `approve_all()` calls on the same group serialize (one waits for the other or one fails cleanly)
- Two concurrent `start_count()` calls result in exactly one active count, not two
- Two concurrent `complete_count()` calls result in one succeeding and one failing cleanly with a status mismatch error
- Two concurrent `create_issuance()` calls against the same stock row with insufficient combined quantity result in one clean "insufficient stock" error, not a raw DB integrity error
- `check_issuance()` and `create_issuance()` both reject a mismatched UOM with a clear error
- All pre-existing backend tests pass
- New tests cover the status guard and error cases above
- `backend.md` handoff entry follows the required section shape

Validation Notes
- 2026-04-08: Orchestrator created Wave 7 Phase 1. Runs in parallel with Phases 2, 3, 4, 5.
- 2026-04-08: Phase 1 agent completed all six fixes. Two new M-3 positive tests (test_create_issuance_correct_uom_succeeds, test_create_issuance_no_uom_falls_back_to_base) used shared emp_data["art"] stock which was depleted by earlier tests in the module. Orchestrator fixed test isolation by giving those two tests dedicated articles via _seed_personal_issue_article_with_stock. Full backend suite: 579 passed, 0 failed. Phase 1 closed.

Next Action
- Backend agent implements all fixes. Can run simultaneously with Phases 2, 3, 4, 5.

---

## Delegation Prompt — Backend Agent

You are the backend concurrency hardening agent for Wave 7 Phase 1 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-07/phase-01-wave-07-backend-concurrency-hardening/orchestrator.md` (this file)
- `handoff/decisions/decision-log.md`
- `backend/app/services/approval_service.py` (read fully)
- `backend/app/services/inventory_service.py` (read fully)
- `backend/app/services/employee_service.py` (read fully)
- `backend/app/models/draft_group.py`
- `backend/app/models/draft.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/stock.py`
- `backend/app/services/receiving_service.py` (lines 310-440 for UOM validation pattern)
- `backend/app/utils/errors.py` (for error shape reference)
- `backend/tests/test_approvals.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_employees.py`

Your fixes (implement all of them, in this order):

1. **H-1: Status guard in `edit_aggregated_line()`** (`approval_service.py`)
   After loading the Draft row (to verify it belongs to the group), check the DraftGroup status.
   Load the DraftGroup for the given `group_id`. If its status is not in the set of actionable states
   (i.e., if the group is already fully approved, rejected, or otherwise resolved), return HTTP 409
   with a body matching the existing error shape used by this service (look at how other validations
   return errors in this file). The guard must run BEFORE the ApprovalOverride upsert.

2. **H-2: Lock all bucket drafts in `_approve_pending_bucket()`** (`approval_service.py`)
   Find where the representative draft is currently locked with `with_for_update()`. Replace this
   with a query that locks ALL pending (status=DRAFT) drafts in the bucket — using the same
   `(article_id, batch_id)` bucket key — with `with_for_update()` and `order_by(Draft.id.asc())`
   to ensure deterministic lock order and prevent deadlocks between concurrent requests.
   The rest of the function logic can remain the same; only the locking strategy changes.

3. **N-1: Group-level lock in `approve_all()`** (`approval_service.py`)
   At the very start of `approve_all()`, before entering any bucket loop, load the DraftGroup row
   for the given `group_id` with `with_for_update()`. This ensures two concurrent `approve_all()`
   calls on the same group serialize. Document in backend.md that this prevents deadlock/failure
   risk from concurrent calls (the likely outcome without this lock is a deadlock or one request
   failing with a lock timeout, not guaranteed double-approval).

4. **H-3: Lock the count row in `complete_count()`** (`inventory_service.py`)
   In `complete_count()`, find the query that loads the InventoryCount row and adds `.with_for_update()`
   to it. This must happen before checking count status or processing any side effects.
   In `start_count()`, find the query that checks for existing IN_PROGRESS counts and add
   `.with_for_update()` to it (or use a `SELECT ... FOR UPDATE` equivalent so concurrent starts
   contend on the same row rather than both seeing no IN_PROGRESS count).
   Note: two concurrent `start_count()` calls may still create two counts if both enter before
   either commits. The lock on the check row reduces this window significantly. If no IN_PROGRESS
   count exists to lock, document in backend.md that a DB-level unique constraint on IN_PROGRESS
   state (Phase 2 scope) would be the complete fix.

5. **H-4: Lock the stock row in `create_issuance()`** (`employee_service.py`)
   Find the stock row availability check in `create_issuance()`. Change the stock row query to use
   `.with_for_update()` at the point of the check, and verify the same query object (or a
   re-fetch of the locked row) is used for the decrement — do not re-query the stock row unlocked
   between the check and the update. Wrap the stock decrement in a try/except that catches
   `IntegrityError` (from SQLAlchemy) and converts it to the same "insufficient stock" business
   error so users see a clean message rather than a 500.

6. **M-3: UOM validation in `check_issuance()` and `create_issuance()`** (`employee_service.py`)
   Read `receiving_service.py` lines 310-440 to understand the UOM validation pattern.
   In both `check_issuance()` and `create_issuance()`, after resolving the article and its base UOM:
   - If `data.get("uom")` is non-empty and does not match the article's base UOM code,
     return/raise the appropriate error (same shape as receiving_service UOM_MISMATCH).
   - If `data.get("uom")` is empty/None, fall back to the article's base UOM (existing behavior).

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Fix any failures before completing
- Write your entry in `handoff/wave-07/phase-01-wave-07-backend-concurrency-hardening/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
- Include in Open Issues / Risks: note that H-3 `start_count()` still has a small race window
  without a DB-level unique constraint on IN_PROGRESS state (that constraint is Phase 2 scope).
- Include in Open Issues / Risks: note that `check_issuance()` is advisory — its result is not
  guaranteed to hold by the time `create_issuance()` is called. This is by design and acceptable.
