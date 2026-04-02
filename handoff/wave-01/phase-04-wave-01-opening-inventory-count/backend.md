# Backend Handoff — Wave 1 Phase 4 Opening Inventory Count

Reserved for backend agent entries. Append only.

---

## Entry — 2026-03-23

### Status
Complete. All tasks implemented and verified.

### Scope
- Added `InventoryCountType` enum (`REGULAR`, `OPENING`) to `backend/app/models/enums.py`.
- Extended `InventoryCount` model with a non-null `type` column defaulting to `REGULAR`.
- Added Alembic migration `b2c3d4e5f6a7` with PostgreSQL explicit enum create and SQLite batch-mode support.
- Extended `start_count` service to accept `count_type` parameter and enforce the opening-count singleton rule with exact error message `"Opening stock count already exists."`.
- Added `type` to all count-shaped responses: start, active, history items, count detail.
- Added `opening_count_exists: boolean` to `GET /api/v1/inventory` response.
- Extended `POST /api/v1/inventory` route to parse optional `{ "type": "REGULAR" | "OPENING" }` body, validate against enum, and pass to service.
- Completion path (`complete_count`) unchanged — OPENING and REGULAR use identical surplus/shortage-draft logic.

### Docs Read
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-INV-001 through DEC-INV-007, DEC-BE-014)
- `backend/app/models/enums.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_phase2_models.py`

### Files Changed
- `backend/app/models/enums.py` — added `InventoryCountType` enum
- `backend/app/models/inventory_count.py` — added `type` column to `InventoryCount`
- `backend/app/services/inventory_service.py` — extended `start_count`, `list_counts`, `get_active_count`, `get_count_detail` with type support and `opening_count_exists`
- `backend/app/api/inventory_count/routes.py` — extended `start_count` route to parse and validate optional `type` body param
- `backend/migrations/versions/b2c3d4e5f6a7_add_inventory_count_type.py` — new migration (PostgreSQL + SQLite safe)
- `backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py` — **pre-existing bug fix**: added SQLite batch mode for the unique constraint ALTER; this migration was breaking `test_phase2_models.py` on SQLite before my changes

### Commands Run
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q`

### Tests
- 22 passed, 1 warning (SQLite batch mode implicit constraint warning — benign, from `a1b2c3d4e5f6` migration)
- Migration chain runs cleanly to head on SQLite: `733fdf937291 → e692013166e4 → f3a590393799 → 9b3c4d5e6f70 → 7c2d2c6d0f4a → a1b2c3d4e5f6 → b2c3d4e5f6a7`

### Open Issues / Risks
- **Pre-existing migration bug fixed**: `a1b2c3d4e5f6` previously lacked SQLite batch mode for `op.create_unique_constraint`. This was silently causing `test_phase2_models.py` to fail before this phase. Fixed as a prerequisite — no new functional risk.
- The `server_default` removal step in my migration (removing `"REGULAR"` after backfill) is safe because all existing rows already have the default applied. Future rows must supply `type` explicitly via the model default.

### Next Recommended Step
- Frontend agent: wire `type`, `opening_count_exists` from the updated API contract into the Inventory Count page per the frontend delegation prompt.
