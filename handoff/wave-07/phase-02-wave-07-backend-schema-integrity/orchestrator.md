## Phase Summary

Phase
- Wave 7 - Phase 2 - Backend DB Schema Integrity

Objective
- Remediate three schema/data-integrity findings from the 2026-04-08 dual-agent code review:
  M-1 (stock/surplus NULL batch_id uniqueness incomplete; surplus has no uniqueness at all),
  M-2 (batch table has no unique constraint on article_id + batch_code),
  N-5 (InventoryCountLine has no uniqueness constraint — good defensive measure, not a direct
  fix for the H-3 race which creates separate counts, not duplicate lines within one count).

Source Docs
- `handoff/README.md`
- `handoff/wave-07/README.md`
- `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (M-1, M-2)
- `handoff/Findings/wave-06-second-opinion-review.md` (M-1, M-2, N-5 with correction note)
- `handoff/decisions/decision-log.md`
- `backend/app/models/stock.py`
- `backend/app/models/surplus.py`
- `backend/app/models/batch.py`
- `backend/app/models/inventory_count.py`
- `backend/migrations/versions/` (read existing migrations for pattern reference)
- `backend/migrations/versions/733fdf937291_initial.py` (original schema)

Current Repo Reality
- `stock.py` has `UniqueConstraint('location_id', 'article_id', 'batch_id', name='uq_stock_location_article_batch')`.
  In PostgreSQL, UNIQUE constraints allow multiple NULLs, so multiple no-batch stock rows for the
  same (location_id, article_id) can exist when batch_id IS NULL. A partial unique index is needed
  for the NULL case alongside the existing constraint covering non-NULL rows.
- `surplus.py` has NO uniqueness constraint at all. Duplicate surplus buckets for the same
  (location_id, article_id, batch_id) can exist, causing incorrect inventory calculations in
  the approval and receiving paths.
- `batch.py` has no unique constraint on (article_id, batch_code). Concurrent receiving can create
  duplicate batch rows for the same article/code. Later `.first()` queries become nondeterministic.
- `inventory_count.py` count lines have nullable batch_id with no unique constraint on
  (inventory_count_id, article_id, batch_id). Note: the H-3 race (Phase 1) creates two separate
  active counts, not duplicate lines within one count. N-5 is a defensive constraint — it prevents
  any future code path from creating duplicate lines within the same count, and is worth adding
  even though it does not directly fix H-3.

Contract Locks / Clarifications
- **M-1 stock NULL uniqueness**: Do NOT remove the existing `uq_stock_location_article_batch`
  UniqueConstraint (it correctly covers non-NULL batch_id rows). ADD a partial unique index via
  Alembic migration that covers only the NULL case:
  ```sql
  CREATE UNIQUE INDEX uq_stock_no_batch ON stock (location_id, article_id) WHERE batch_id IS NULL;
  ```
  This requires a raw SQL index in the migration (SQLAlchemy ORM UniqueConstraint does not support
  partial indexes — use `op.create_index()` with `postgresql_where` or raw SQL via `op.execute()`).
  Also update `stock.py` model to document this dual-constraint design in a comment.
- **M-1 surplus uniqueness**: ADD a full uniqueness solution for surplus. Because surplus.batch_id
  is nullable, the same partial-index approach is needed:
  - For non-NULL batch_id: `UniqueConstraint('location_id', 'article_id', 'batch_id')` in the
    model + migration.
  - For NULL batch_id: `CREATE UNIQUE INDEX uq_surplus_no_batch ON surplus (location_id, article_id) WHERE batch_id IS NULL;`
  - Check whether any existing surplus data would violate this constraint. If the migration could
    fail on existing duplicates, add a comment in backend.md and the migration itself noting that
    a pre-migration data cleanup may be needed in production.
- **M-2 batch unique constraint**: Add `UniqueConstraint('article_id', 'batch_code', name='uq_batch_article_code')`
  to the Batch model and create a corresponding Alembic migration. Handle the case where existing
  duplicate (article_id, batch_code) rows may exist: add a `DO UPDATE` / `ON CONFLICT` note in
  backend.md, or add a pre-constraint deduplication step in the migration with a comment.
- **N-5 InventoryCountLine**: Add a unique constraint on (inventory_count_id, article_id, batch_id)
  with the same partial-index approach for NULL batch_id. This is defensive hardening, not a fix
  for the H-3 race. Mark it explicitly as defensive in backend.md. Apply same NULL-handling pattern
  as M-1.
- **Migration strategy**: All four migrations (stock partial index, surplus uniqueness, batch unique,
  inventory_count_line unique) should be in SEPARATE migration files or consolidated into one
  clearly named migration. Do NOT create multiple Alembic heads. After all migrations are created,
  run `venv/bin/alembic heads` and ensure exactly one head is reported. If multiple heads exist,
  create a merge migration following the pattern in `migrations/versions/fcb524a92fa4_merge_wave_6_*.py`.
- **SQLite compatibility**: Existing tests use SQLite in-memory. Partial indexes with WHERE clauses
  are supported in SQLite 3.8.9+. Verify tests still pass. If partial index creation fails in
  SQLite test environment, add `if op.get_bind().dialect.name == 'postgresql':` guards in the
  migration (following the Wave 6 migration pattern for SQLite compatibility).
- Do NOT change service logic, API routes, or any file outside the model and migration layers.

File Ownership (this phase only — do not touch other files)
- `backend/app/models/stock.py`
- `backend/app/models/surplus.py`
- `backend/app/models/batch.py`
- `backend/app/models/inventory_count.py`
- `backend/migrations/versions/*.py` (new migration files only)
- `handoff/wave-07/phase-02-wave-07-backend-schema-integrity/backend.md`

Delegation Plan
- Backend: add constraints to models, write Alembic migrations, update tests, document

Acceptance Criteria
- `venv/bin/alembic heads` reports exactly one head after all migrations
- `SELECT COUNT(*) FROM stock WHERE batch_id IS NULL GROUP BY location_id, article_id HAVING COUNT(*) > 1` returns zero rows on any valid state (partial unique index enforces this)
- Surplus has a uniqueness constraint covering both NULL and non-NULL batch_id cases
- `SELECT COUNT(*) FROM batch GROUP BY article_id, batch_code HAVING COUNT(*) > 1` returns zero rows on any valid state
- InventoryCountLine has a unique constraint on (inventory_count_id, article_id) for NULL batch_id and on (inventory_count_id, article_id, batch_id) for non-NULL batch_id
- All pre-existing backend tests pass
- backend.md notes any production data cleanup risk for surplus and batch deduplication

Validation Notes
- 2026-04-08: Orchestrator created Wave 7 Phase 2. Runs in parallel with Phases 1, 3, 4, 5.
- 2026-04-08: Phase 2 agent completed all model changes and migration (a7b8c9d0e1f2). Single Alembic head confirmed. Full backend suite: 579 passed, 0 failed. Phase 2 closed.

Next Action
- Backend agent implements all constraints and migrations. Can run simultaneously with Phases 1, 3, 4, 5.

---

## Delegation Prompt — Backend Agent

You are the backend schema integrity agent for Wave 7 Phase 2 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-07/phase-02-wave-07-backend-schema-integrity/orchestrator.md` (this file)
- `handoff/decisions/decision-log.md`
- `backend/app/models/stock.py`
- `backend/app/models/surplus.py`
- `backend/app/models/batch.py`
- `backend/app/models/inventory_count.py`
- `backend/migrations/versions/733fdf937291_initial.py` (for schema reference)
- `backend/migrations/versions/d1e2f3a4b5c6_add_surplus_quantity_non_negative_check.py` (for recent migration pattern)
- `backend/migrations/versions/fcb524a92fa4_merge_wave_6_phase_1_and_phase_2_.py` (for merge pattern)
- `backend/tests/test_phase2_models.py`
- `backend/tests/test_receiving.py` (batch lookup tests)
- `backend/tests/test_inventory_count.py`

Your fixes (implement all of them):

1. **M-1: Stock partial unique index for NULL batch_id**
   In `backend/app/models/stock.py`: add a comment explaining the dual-constraint design
   (existing UniqueConstraint covers non-NULL batch_id; new partial index covers NULL batch_id).
   Create a new Alembic migration that adds:
   ```sql
   CREATE UNIQUE INDEX uq_stock_no_batch ON stock (location_id, article_id) WHERE batch_id IS NULL;
   ```
   Use `op.execute()` for the raw SQL, or `op.create_index()` with the appropriate dialect parameter.
   Add a SQLite compatibility guard if needed (check `op.get_bind().dialect.name == 'postgresql'`).

2. **M-1: Surplus full uniqueness**
   In `backend/app/models/surplus.py`: add `UniqueConstraint('location_id', 'article_id', 'batch_id',
   name='uq_surplus_location_article_batch')` to the model (covers non-NULL batch_id).
   In the same or a separate Alembic migration, add:
   - The UniqueConstraint via `op.create_unique_constraint()`
   - A partial index for NULL case via `op.execute()`:
     `CREATE UNIQUE INDEX uq_surplus_no_batch ON surplus (location_id, article_id) WHERE batch_id IS NULL;`
   Add a comment in the migration noting that production may need data deduplication before this
   migration runs if duplicate no-batch surplus rows exist.

3. **M-2: Batch unique constraint on (article_id, batch_code)**
   In `backend/app/models/batch.py`: add `UniqueConstraint('article_id', 'batch_code', name='uq_batch_article_code')`.
   Create an Alembic migration that adds this constraint via `op.create_unique_constraint()`.
   Add a comment in the migration noting that production may need deduplication if duplicate
   (article_id, batch_code) rows exist before this migration runs.

4. **N-5: InventoryCountLine uniqueness (defensive)**
   In `backend/app/models/inventory_count.py`: locate the InventoryCountLine model or equivalent
   count line table. Add a unique constraint on (inventory_count_id, article_id, batch_id) for
   non-NULL batch_id, and a partial index for NULL batch_id:
   `CREATE UNIQUE INDEX uq_count_line_no_batch ON inventory_count_line (inventory_count_id, article_id) WHERE batch_id IS NULL;`
   Note in the migration and in backend.md: this is defensive hardening. The H-3 race (Phase 1)
   creates two separate active counts, not duplicate lines within one count. This constraint
   prevents any future code path from creating such duplicates.

5. **Single Alembic head**
   After creating all migrations, run: `venv/bin/alembic heads`
   If multiple heads appear, create a merge migration following the pattern in:
   `backend/migrations/versions/fcb524a92fa4_merge_wave_6_phase_1_and_phase_2_.py`

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Run: `venv/bin/alembic heads`
- Fix any failures before completing
- Write your entry in `handoff/wave-07/phase-02-wave-07-backend-schema-integrity/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
- Note any production data cleanup risks in Open Issues / Risks
