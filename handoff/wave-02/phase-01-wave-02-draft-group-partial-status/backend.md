# Backend Handoff — Wave 2 Phase 1: DraftGroup PARTIAL Persistence

## Status

**COMPLETE** — All done criteria met. Tests pass. Migration verified on SQLite. Ready for Frontend and Testing agents.

---

## Scope

Resolve F-030 / DEC-APP-001: promote `PARTIAL` from a computed-only display escape hatch into a real, persisted `DraftGroup.status` value. Fix the pre-existing bug where mixed fully-resolved approval groups were permanently stored as `PENDING` in the database.

---

## Docs Read

- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (F-030)
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/05_DATA_MODEL.md` §10-12
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` §5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-APP-001 and all prior approvals decisions)
- `handoff/implementation/phase-06-approvals/orchestrator.md`
- `handoff/implementation/phase-06-approvals-followup/orchestrator.md`
- `handoff/wave-02/phase-01-wave-02-draft-group-partial-status/orchestrator.md`

---

## Files Changed

### 1. `backend/app/models/enums.py`
- Added `PARTIAL = "PARTIAL"` to `DraftGroupStatus`.

### 2. `backend/app/services/approval_service.py`

**`_update_group_status_if_done` (lines 541–561):**
- Replaced the old `pass` branch that deliberately skipped persisting `PARTIAL`.
- Now writes `DraftGroupStatus.PARTIAL` to the DB when `_compute_group_display_status` returns `"PARTIAL"` (i.e., no remaining `DRAFT` lines + mix of `APPROVED` and `REJECTED`).
- `PENDING` (any remaining `DRAFT` rows) still leaves the group status unchanged — no regression.

**`get_history_draft_groups` (lines 65–85):**
- Removed the per-group `_compute_group_display_status()` recomputation loop.
- Now uses the authoritative persisted `group.status` directly (since it is now correct for all resolved groups).
- History segmentation logic (no `DRAFT` rows = history) is unchanged.

### 3. `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py` *(new file)*

- **Revision:** `c3d4e5f6a7b8` — chains from `b2c3d4e5f6a7` (add_inventory_count_type)
- **SQLite upgrade path:** Uses `batch_alter_table` to rebuild the column with the new 4-value `Enum` (avoids ALTER TABLE limitations).
- **PostgreSQL upgrade path:** Issues `ALTER TYPE draft_group_status ADD VALUE IF NOT EXISTS 'PARTIAL'` (idempotent, no data loss).
- **Backfill:** After the schema change, a single SQL `UPDATE` corrects any existing rows that are `PENDING` but have no remaining `DRAFT` lines and contain both `APPROVED` and `REJECTED` child rows.
- **Downgrade:** Reverts `PARTIAL` rows to `PENDING`, then drops/recreates the enum type on PostgreSQL (or rebuilds the column on SQLite) with the old 3-value set.

### 4. `backend/migrations/versions/7c2d2c6d0f4a_persist_token_revocation_and_lock_daily_.py` *(amended)*

- **SQLite warning fix (opportunistic, requested by user):** The original migration used `op.add_column("draft_group", ...)` directly for all dialects. On SQLite this triggered `UserWarning: Skipping unsupported ALTER for creation of implicit constraint` because Alembic's non-batch ADD COLUMN path cannot reproduce named constraints (specifically the `UniqueConstraint` on `group_number`) during schema reflection.
- Fix: split the `add_column` into a PostgreSQL path (`op.add_column` as before) and a SQLite path (`batch_alter_table` → `batch_op.add_column`). The copy-and-move strategy properly reconstructs all constraints and suppresses the warning.

### 5. `backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py` *(amended)*

- **SQLite warning fix (opportunistic, requested by user):** The original migration used `batch_op.create_unique_constraint(...)` inside `batch_alter_table`. SQLite's batch path does not support named unique constraints and emits the same `UserWarning` while silently dropping the constraint name.
- Fix: replaced `batch_op.create_unique_constraint` with `batch_op.create_index(..., unique=True)` for the SQLite path. A `UNIQUE INDEX` is fully equivalent to a `UNIQUE CONSTRAINT` for SQLite enforcement. Downgrade now uses `batch_op.drop_index` symmetrically. The PostgreSQL path is unchanged.

### 6. `backend/tests/test_approvals.py`
- Added `TestPartialStatusPersistence` class (6 new test methods) at the end of the file.
- **New tests:**
  - `test_partial_persisted_in_db_after_mixed_resolution` — core contract: DB row `DraftGroup.status == DraftGroupStatus.PARTIAL`
  - `test_partial_group_not_in_pending_list` — PARTIAL group absent from pending API
  - `test_partial_group_appears_in_history_with_correct_status` — PARTIAL group present in history API with `"status": "PARTIAL"`
  - `test_fully_approved_group_still_persists_as_approved` — regression guard for APPROVED path
  - `test_fully_rejected_group_still_persists_as_rejected` — regression guard for REJECTED path
  - `test_group_with_remaining_draft_lines_stays_pending` — group with mixed approval and a remaining DRAFT line stays as PENDING

---

## Migration / Backfill Behavior

- **Fresh SQLite install (test environment):** `alembic upgrade head` runs cleanly through the new migration. The `PARTIAL` value is added to the column enum check. No data to backfill on a fresh DB.
- **Existing DB with stale PENDING groups:** The `UPDATE` at the end of `upgrade()` corrects them atomically with the schema change.
- **PostgreSQL (production target):** `ALTER TYPE ... ADD VALUE IF NOT EXISTS` is the recommended non-locking approach for extending a PostgreSQL enum. The `IF NOT EXISTS` guard makes the migration re-runnable safely.
- The pre-existing `uq_draft_group_pending_daily_outbound_date` partial unique index filters on `status = 'PENDING'`, so resolved `PARTIAL` groups do not interfere with the same-day PENDING singleton invariant.

---

## Commands Run

```bash
# All approvals tests
venv/bin/pytest tests/test_approvals.py -q
# → 28 passed in 0.80s

# Migration chain test (fresh SQLite upgrade-to-head) — 0 warnings after fix
venv/bin/pytest tests/test_phase2_models.py -q
# → 2 passed in 0.23s

# Full backend test suite — 0 warnings
venv/bin/pytest tests/ -q
# → 349 passed in 19.29s
```

---

## Tests

| Suite | Before | After |
|---|---|---|
| `test_approvals.py` | 22 passed | **28 passed** (+6 new) |
| `test_phase2_models.py` | 2 passed, 1 warning | **2 passed, 0 warnings** |
| Full `tests/` | 343 passed, 1 warning | **349 passed, 0 warnings** |

---

## Open Issues / Risks

- **PostgreSQL downgrade path** uses a drop-and-recreate-type approach because PostgreSQL does not support `ALTER TYPE ... DROP VALUE`. This is correct and safe, but any operator running `alembic downgrade` on a live production PostgreSQL database should first verify there are no `PARTIAL` rows that should be preserved (the downgrade intentionally coerces them back to `PENDING`).
- **`_compute_group_display_status` still exists** in the service for the detail view and internal recompute logic. This is intentional — the detail view recomputes status for correctness (e.g., after a partial re-open scenario). The function is no longer called from `get_history_draft_groups` but remains useful for `get_draft_group_detail`.

---

## Assumptions

- The `batch_alter_table` pattern used for SQLite in the new migration follows the established repo pattern from `b2c3d4e5f6a7`.
- `PARTIAL` is not expected to appear in the `Draft.status` enum — only `DraftGroup.status` gains this value. `DraftStatus` remains `DRAFT / APPROVED / REJECTED`.
- The SQLite `UNIQUE INDEX` created by the amended `a1b2c3d4e5f6` migration is functionally identical to the old named `UNIQUE CONSTRAINT` for enforcement purposes. Existing SQLite dev databases that previously ran the broken migration may lack the index and should be rebuilt from scratch (this limitation was already noted in `DEC-BE-015`).

---

## Next Recommended Step

- Frontend agent: audit `frontend/src/api/approvals.ts` type definitions and `ApprovalsPage.tsx` / `DraftGroupCard.tsx` to ensure `PARTIAL` is treated as a first-class status in all status-mapping, badge-rendering, and tab-filtering logic (see orchestrator delegation prompt).
- Testing agent: review this handoff and the new `TestPartialStatusPersistence` class as the baseline for any additional E2E or integration coverage they want to add.
