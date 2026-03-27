## 2026-03-27 18:52:15 CET

Status
- Complete

Scope
- Added explicit nullable `Draft.inventory_count_id` linkage for inventory shortage drafts.
- Replaced inventory shortage summary lookup logic to use the explicit FK instead of `client_event_id LIKE ...`.
- Centralized duplicated route query parsers into `backend/app/utils/validators.py` for the six scoped route modules.
- Verified fresh SQLite and fresh PostgreSQL `alembic upgrade head`, including a PostgreSQL enum-migration fix required to keep the repo's fresh-db path working.

Docs Read
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-026`, `F-034`)
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` §10, §17, §18
- `stoqio_docs/07_ARCHITECTURE.md` §2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-014`, `DEC-INV-005`)
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/orchestrator.md`

Files Changed
- `backend/app/api/articles/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/api/settings/routes.py`
- `backend/app/models/draft.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/utils/validators.py`
- `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py`
- `backend/migrations/versions/d4e5f6a7b8c9_add_draft_inventory_count_link.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_phase2_models.py`
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/backend.md`

Commands Run
- `git status --short`
- `rg -n "F-026|F-034|DEC-BE-014|inventory count|inventory-count|shortage|parse_positive_int|parse_bool_query|_get_shortage_drafts_summary|client_event_id" stoqio_docs handoff backend/app backend/tests -g '!backend/venv/**'`
- `venv/bin/python -m alembic heads`
- `venv/bin/python -m pytest tests/test_inventory_count.py tests/test_phase2_models.py tests/test_i18n.py -q`
- `FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_phase5_sqlite_upgrade.db JWT_SECRET_KEY=test-jwt-secret-key-suite-2026-0001 venv/bin/python -m alembic upgrade head`
- `venv/bin/python - <<'PY' ... command.upgrade(config, 'head') ... PY` against a fresh temporary PostgreSQL database on `localhost`
- `git diff --check`
- `git diff --stat`

Tests
- `venv/bin/python -m pytest tests/test_inventory_count.py tests/test_phase2_models.py tests/test_i18n.py -q` → `63 passed`
- Fresh SQLite upgrade: `alembic upgrade head` on `/tmp/stoqio_phase5_sqlite_upgrade.db` succeeded.
- Fresh PostgreSQL upgrade: clean temporary database `stoqio_phase5_35dbbb6a` upgraded to `head` successfully after patching `c3d4e5f6a7b8` to use a PostgreSQL autocommit block for the enum add-value step.

Open Issues / Risks
- Existing shortage drafts from pre-phase databases remain `inventory_count_id = NULL` by contract; this phase is fresh-db only and does not backfill them.
- `Draft.client_event_id` remains populated for inventory shortages but is now inert metadata for summary linkage.

Next Recommended Step
- Frontend/testing follow-up can rely on `inventory_count_id` as the authoritative shortage linkage and should stop asserting the old `client_event_id LIKE ...` convention anywhere else.
