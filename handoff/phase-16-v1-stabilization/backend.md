# Backend Handoff — Phase 16 V1 Stabilization

Reserved for backend agent entries. Append only.

## [2026-03-17 18:23] Codex

Status
- completed

Scope
- Replaced process-local logout revocation with a persisted DB-backed registry.
- Hardened Draft Entry so only the current `PENDING` `DAILY_OUTBOUND` group is used for the operational day.
- Added DB-backed guardrails against duplicate open daily outbound groups while preserving separate inventory shortage groups.
- Updated main documentation so future agents can see the fix history without reconstructing it from git alone.

Docs Read
- `docs/v1-recap.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Files Changed
- `backend/app/models/revoked_token.py`
- `backend/app/models/__init__.py`
- `backend/app/models/enums.py`
- `backend/app/models/draft_group.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/migrations/versions/7c2d2c6d0f4a_persist_token_revocation_and_lock_daily_.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_phase2_models.py`
- `README.md`
- `docs/v1-recap.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `handoff/decisions/decision-log.md`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_auth.py backend/tests/test_drafts.py backend/tests/test_inventory_count.py -q
backend/venv/bin/pytest backend/tests -q
cd backend && DATABASE_URL=sqlite:////tmp/stoqio_bugfixes.db venv/bin/alembic upgrade head
cd backend && DATABASE_URL=sqlite:////tmp/stoqio_bugfixes.db venv/bin/python seed.py
backend/venv/bin/python - <<'PY'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://grzzi@localhost/wms_dev', isolation_level='AUTOCOMMIT')
with engine.connect() as conn:
    conn.execute(text('DROP SCHEMA IF EXISTS public CASCADE'))
    conn.execute(text('CREATE SCHEMA public'))
PY
cd backend && DATABASE_URL=postgresql://grzzi@localhost/wms_dev FLASK_ENV=development JWT_SECRET_KEY=dev-local-jwt-secret-change-me-2026 venv/bin/alembic upgrade head
cd backend && FLASK_ENV=development DATABASE_URL=postgresql://grzzi@localhost/wms_dev JWT_SECRET_KEY=dev-local-jwt-secret-change-me-2026 venv/bin/python seed.py
```

Tests
- Passed:
- `backend/venv/bin/pytest backend/tests/test_auth.py backend/tests/test_drafts.py backend/tests/test_inventory_count.py -q` -> `83 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `255 passed`
- fresh SQLite Alembic upgrade to head -> passed
- fresh SQLite seed after upgrade -> passed
- fresh local PostgreSQL schema wipe -> passed
- fresh local PostgreSQL `alembic upgrade head` -> passed after fixing enum creation in migration `7c2d2c6d0f4a`
- fresh local PostgreSQL `seed.py` -> passed
- Failed:
- None
- Not run:
- PostgreSQL-specific migration smoke outside the sandbox

Open Issues / Risks
- Fresh SQLite Alembic upgrade emits one warning about implicit enum constraint creation during ALTER. The migration succeeds, tests are green, and the application still writes only valid `group_type` values, but anyone touching SQLite migration strictness later should re-evaluate that warning.
- This phase intentionally did not tackle frontend quantity-formatting duplication or frontend token persistence policy.

Next Recommended Step
- Use `RevokedToken` as the canonical logout-revocation mechanism for any future auth work.
- Preserve `DraftGroup.group_type` and the partial unique index semantics when extending Draft Entry, Inventory Count, or Approvals.

## [2026-03-23 18:13] Codex

Status
- completed

Scope
- Added article create/update supplier-link handling on top of the existing `ArticleSupplier` table.
- Preserved the full Warehouse article detail payload, including enriched supplier rows and preferred-first ordering.
- Added a Warehouse supplier lookup endpoint at `GET /api/v1/suppliers` without changing the Settings supplier endpoints.

Docs Read
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/decisions/decision-log.md`

Files Changed
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`

Commands Run
```bash
cd backend && venv/bin/pytest backend/tests/test_articles.py -q
cd backend && venv/bin/pytest tests/test_articles.py -q
```

Tests
- Passed:
- `cd backend && venv/bin/pytest tests/test_articles.py -q` -> `32 passed`
- Failed:
- `cd backend && venv/bin/pytest backend/tests/test_articles.py -q` -> path invalid after `cd backend` (`backend/tests/test_articles.py` not found)
- Not run:
- broader backend suite

Assumptions
- `GET /api/v1/suppliers` should follow the Warehouse lookup access pattern and be available to `ADMIN` and `MANAGER`.
- Missing per-link `is_preferred` values are normalized to `false`; `supplier_article_code` remains optional/nullable.

Spec Drift / Resolutions
- The required pytest command used a repo-root-relative test path after `cd backend`; I ran it as written, confirmed the path issue, then reran the corrected command against the same test file.
