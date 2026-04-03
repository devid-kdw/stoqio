# Backend Handoff — Wave 3 Phase 4: Draft Serialization Performance Cleanup

## [2026-04-03 14:45 CEST] Backend Agent Delivery

---

### Status

Complete.

---

### Scope

Eliminated the N+1 query pattern from the daily draft serialization path in
`backend/app/api/drafts/routes.py` without changing the API response shape.

The original `_serialize_draft()` issued per-row `db.session.get()` calls for
`Article`, `Batch`, and `User`, plus a separate `ApprovalAction` query via
`_get_rejection_reason()` for every rejected line.  The list endpoints
(`GET /drafts?date=today` and `GET /drafts/my`) both called `_serialize_draft()`
inside a loop, producing 3–4 queries × N rows.

---

### Docs Read

- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-004)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/orchestrator.md`
- `backend/app/api/drafts/routes.py`
- `backend/app/models/draft.py`
- `backend/app/models/approval_action.py`
- `backend/tests/test_drafts.py`

---

### Old Query Shape (per-row N+1)

For a list of N draft rows the old code issued:

```
GET /drafts?date=today with N drafts:

  [per row × N]   SELECT * FROM article WHERE id = ?       ← db.session.get(Article, draft.article_id)
  [per row × N]   SELECT * FROM batch WHERE id = ?         ← db.session.get(Batch, draft.batch_id)
  [per row × N]   SELECT * FROM user WHERE id = ?          ← db.session.get(User, draft.created_by)
  [per row × R]   SELECT * FROM approval_action WHERE ...  ← _get_rejection_reason(draft.id) for REJECTED rows
```

Same pattern repeated for `same_day_lines` (which can span multiple groups and
be larger than `items`), and again for `GET /drafts/my`.

---

### New Bounded-Query Shape

```
GET /drafts?date=today with N drafts:

  1. SELECT draft_group ... WHERE operational_date = ? AND status = PENDING AND group_type = DAILY_OUTBOUND
  2. SELECT draft JOIN article JOIN batch JOIN user WHERE draft_group_id = ?   ← joinedload, resolves N rows in 1–3 queries
  3. SELECT draft_group ... WHERE operational_date = ? AND group_type = DAILY_OUTBOUND   (same-day groups)
  4. SELECT draft JOIN article JOIN batch JOIN user WHERE draft_group_id IN (...)         ← joinedload, same-day all rows
  5. SELECT approval_action WHERE draft_id IN (...) AND action = REJECTED                ← _build_rejection_map (items)
  6. SELECT approval_action WHERE draft_id IN (...) AND action = REJECTED                ← _build_rejection_map (same_day)

Total: O(1) bounded queries regardless of N
```

For `GET /drafts/my` the shape is the same but only steps 3, 4, and one
rejection-map query are needed (no separate pending-group subquery).

---

### Files Changed

| File | Change |
|---|---|
| `backend/app/api/drafts/routes.py` | Refactored serialization path; see details below |

#### `backend/app/api/drafts/routes.py` — detailed changes

1. **Added `joinedload` import** from `sqlalchemy.orm`.

2. **Replaced `_get_rejection_reason(draft_id)`** (per-row query) with
   `_build_rejection_map(draft_ids)`.  The new helper issues one
   `SELECT … WHERE draft_id IN (…) AND action = REJECTED` query and returns a
   `dict[int, str | None]` keyed by `draft_id`.  Only the latest action per
   draft is kept (identical semantics to the old per-row helper since both sort
   by `acted_at DESC` and pick the first row).

3. **Refactored `_serialize_draft()`** signature:
   - Accepts an optional keyword-only `rejection_map` parameter.
   - Reads `draft.article`, `draft.batch`, and `draft.creator` from the already-
     loaded ORM relationship attributes instead of calling `db.session.get(…)`.
     When called from a list path with joinedload the relationships are already
     in the session identity map; when called from a single-row mutation path
     SQLAlchemy resolves them with a normal lazy-select (one row, not N).
   - Uses `rejection_map.get(draft.id)` for rejected lines when the map is
     provided; falls back to a direct query for the single-row mutation path.

4. **Updated `get_drafts()`** (`GET /drafts?date=today`):
   - Loads pending-group drafts via `db.session.query(Draft).options(joinedload(Draft.article), joinedload(Draft.batch), joinedload(Draft.creator))`.
   - Loads same-day drafts with the same `options(...)` clause.
   - Calls `_build_rejection_map(pending_ids)` and `_build_rejection_map(same_day_ids)` before the serialization loop.
   - Passes the appropriate map to each `_serialize_draft()` call.

5. **Updated `get_my_drafts()`** (`GET /drafts/my`):
   - Same treatment: `joinedload` on the draft query and `_build_rejection_map` before serialization.

6. **`POST /drafts` and `PATCH /drafts/<id>` mutation responses** were not
   changed.  They call `_serialize_draft(draft)` for a single row with no
   loop; the new default (no `rejection_map`) triggers the single-row fallback
   path which is correct and has no N+1 risk.

7. **Updated module-level docstring** to reflect the new query strategy.

8. **Removed unused `from collections import defaultdict`** that was accidentally
   introduced during the edit.

---

### Commands Run

```bash
cd backend && venv/bin/python -m pytest tests/test_drafts.py -q
# → 54 passed in 1.09s

cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q
# → 92 passed in 48.16s
```

---

### Tests

- All 54 existing `tests/test_drafts.py` tests pass without modification.
- The test suite covers:
  - Normal draft lines (non-batch and batch articles)
  - Rejected lines with rejection reason preserved
  - `same_day_lines` spanning pending + resolved groups
  - `INVENTORY_SHORTAGE` group exclusion from `same_day_lines`
  - `/drafts/my` response shape, rejection reason, user scoping, ordering
  - Field presence including `rejection_reason` on every serialized line
- No tests were added in this phase; the existing suite provides sufficient
  behavioral coverage of the unchanged contract.  Query-count regression
  coverage is not practical with the current SQLite-backed test stack; the
  improvement is documented in this handoff instead per the task guidance.

---

### Whether /drafts/my or Mutation Responses Were Touched

- **`GET /drafts/my`** — yes, touched.  The query now uses `joinedload` and
  `_build_rejection_map`.  The response shape is identical.
- **`POST /drafts` (idempotency return)** — the call `jsonify(_serialize_draft(existing))` was
  not changed.  The new `_serialize_draft` is backward-compatible; it uses the
  ORM relationship attributes (`draft.article`, etc.) which SQLAlchemy resolves
  lazily for single-row paths.
- **`PATCH /drafts/<id>`** — same as POST: single-row `_serialize_draft(draft)`
  unchanged, no N+1 risk.

---

### Open Issues / Residual Risk

- **SQLite test isolation:** The `joinedload` strategy is dialect-agnostic and
  tested on SQLite (same as the rest of the suite).  No PostgreSQL-specific
  risk is expected.
- **Session identity map:** On very large same-day lists the `IN (…)` clause
  for rejection reasons will grow proportionally.  This is still O(1) extra
  queries and far better than O(N).  If the list ever becomes very large (e.g.
  thousands of lines in one day) a LIMIT or pagination approach would be the
  next step, but that is out of scope for this phase.
- **`Article`, `Batch`, `User` still imported at module level** — these are
  used in `create_draft()` for validation (`db.session.get(Article, …)` etc.),
  not for serialization.  The imports remain correct.

---

### Next Recommended Step

Proceed to Wave 3 Phase 5 — SQLAlchemy Relationship Modernization (W3-005).
