## Phase Summary

Phase
- Phase 16 - V1 Stabilization

Objective
- Close the two confirmed post-V1 backend defects from bug review:
- make logout revocation survive process restarts
- stop same-day Draft Entry from reusing closed groups or racing into duplicate open daily groups
- leave a durable documentation and handoff trail for later agents

Source Docs
- `docs/v1-recap.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Delegation Plan
- Backend:
- replace process-local auth revocation with a persisted store, harden DraftGroup semantics, add migrations, and extend regression coverage
- Frontend:
- no UI code change expected; document whether any route or contract change is required
- Testing:
- run targeted regressions, full backend suite, and fresh-db migration/seed verification

Acceptance Criteria
- Logged-out refresh tokens stay revoked after Flask/systemd restart because revocation is persisted
- Draft Entry uses only the current `PENDING` `DAILY_OUTBOUND` group for the operational day
- Approved/rejected same-day outbound groups are not reused for new operator draft lines
- Database enforces at most one open daily-outbound group per operational date without blocking separate inventory shortage groups
- Main docs and handoff trail record what changed and when

Validation Notes
- Backend/auth hardening accepted:
- `revoked_token` table added; JWT blocklist callback now checks persisted revocation rows
- logout persists `jti`, token type, user, and expiry metadata
- DraftGroup hardening accepted:
- `group_type = DAILY_OUTBOUND | INVENTORY_SHORTAGE` added
- partial unique index `uq_draft_group_pending_daily_outbound_date` added for one open daily-outbound group per date
- Draft Entry routes now target only `PENDING` `DAILY_OUTBOUND`
- inventory shortage groups remain separate and still use the shared Approvals flow
- Documentation accepted:
- root `README.md`, `docs/v1-recap.md`, core architecture/data-model docs, decision log, and this Phase 16 handoff folder were updated

Verification
- `backend/venv/bin/pytest backend/tests/test_auth.py backend/tests/test_drafts.py backend/tests/test_inventory_count.py -q` -> `83 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `255 passed`
- `cd backend && DATABASE_URL=sqlite:////tmp/stoqio_bugfixes.db venv/bin/alembic upgrade head` -> passed
- `cd backend && DATABASE_URL=sqlite:////tmp/stoqio_bugfixes.db venv/bin/python seed.py` -> passed
- `cd backend && DATABASE_URL=postgresql://grzzi@localhost/wms_dev venv/bin/alembic upgrade head` on a wiped local PostgreSQL DB -> passed after explicit enum-create fix in migration `7c2d2c6d0f4a`
- `cd backend && FLASK_ENV=development DATABASE_URL=postgresql://grzzi@localhost/wms_dev venv/bin/python seed.py` -> passed on the rebuilt local PostgreSQL DB

Residual Risks
- Fresh SQLite Alembic upgrade still emits one warning about implicit enum constraint creation on SQLite ALTER during this migration path. Upgrade succeeds and runtime/test coverage is green, but agents touching SQLite migration ergonomics later should keep that warning in mind.
- Frontend integer/decimal UOM formatting duplication remains a separate cleanup item; this phase did not change UI code.

Next Action
- Treat these fixes as the new baseline for post-V1 work. Future bugfix or feature phases should build on `revoked_token` and `DraftGroup.group_type`, not reintroduce date-only DraftGroup lookup or process-local logout revocation.

## [2026-03-23 18:02] Orchestrator Validation - Frontend Auth Reload Persistence

Status
- accepted

Scope
- Reviewed the frontend-only auth persistence implementation added under the Phase 16 stabilization handoff trail.
- Validated that refresh-token persistence, silent bootstrap, and reload behavior match the delegated scope without requiring backend changes.

Docs Read
- `stoqio_docs/07_ARCHITECTURE.md`
- `frontend/src/main.tsx`
- `frontend/src/store/authStore.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/client.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `handoff/implementation/phase-16-v1-stabilization/frontend.md`
- `handoff/decisions/decision-log.md`

Files Reviewed
- `frontend/src/main.tsx`
- `frontend/src/store/authStore.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/client.ts`
- `handoff/implementation/phase-16-v1-stabilization/frontend.md`
- `handoff/decisions/decision-log.md`

Commands Run
```bash
git status --short
git diff --stat
git diff -- frontend/src/api/auth.ts frontend/src/api/client.ts frontend/src/main.tsx frontend/src/store/authStore.ts handoff/decisions/decision-log.md handoff/implementation/phase-16-v1-stabilization/frontend.md
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- No functional review findings were identified in the final frontend implementation.
- Accepted storage split:
- refresh token persists only under `stoqio_refresh_token`
- access token remains memory-only in Zustand
- Accepted bootstrap flow:
- app bootstrap runs before route rendering in `frontend/src/main.tsx`
- bootstrap calls `POST /api/v1/auth/refresh` and then `GET /api/v1/auth/me`
- Zustand is hydrated with `user`, `accessToken`, `refreshToken`, and `isAuthenticated` before protected routes render
- Accepted 401 recovery hardening:
- axios refresh fallback can recover from a persisted refresh token after reload even before the store is fully hydrated
- Accepted documentation trace:
- `DEC-FE-006` records the new persisted-refresh-token policy and the fact that the older architecture doc is now stale

Verification
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed
- User manual browser verification accepted:
- refresh on an authenticated page keeps the user logged in and on the same page

Residual Risks
- `stoqio_docs/07_ARCHITECTURE.md` still documents the older "both tokens are memory-only" policy. Until that doc is revised, `DEC-FE-006` is the accepted source of truth for auth persistence behavior.
- This review did not reproduce the full manual matrix locally (expired-access reload, manual localStorage clearing, logout cleanup), so those checks remain manual-only evidence for now.

Next Action
- Keep this implementation as the active frontend auth bootstrap baseline.
- When the locked architecture docs are next revised, replace the obsolete token-storage note with the `DEC-FE-006` policy.

## [2026-03-23 18:31] Orchestrator Validation - Warehouse Supplier Linkage

Status
- accepted pending manual browser verification

Scope
- Reviewed the backend and frontend implementation for article supplier linkage in the Warehouse create/edit flow.
- Verified the targeted backend tests plus frontend lint/build signal.
- Prepared manual browser verification steps instead of delegating to the testing agent.

Docs Read
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-16-v1-stabilization/backend.md`
- `handoff/implementation/phase-16-v1-stabilization/frontend.md`

Files Reviewed
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-16-v1-stabilization/backend.md`
- `handoff/implementation/phase-16-v1-stabilization/frontend.md`

Commands Run
```bash
git status --short
git diff --stat
git diff -- backend/app/api/articles/routes.py backend/app/services/article_service.py backend/tests/test_articles.py frontend/src/api/articles.ts frontend/src/pages/warehouse/WarehouseArticleForm.tsx frontend/src/pages/warehouse/WarehousePage.tsx frontend/src/pages/warehouse/ArticleDetailPage.tsx frontend/src/pages/warehouse/warehouseUtils.ts handoff/decisions/decision-log.md handoff/implementation/phase-16-v1-stabilization/backend.md handoff/implementation/phase-16-v1-stabilization/frontend.md
cd backend && venv/bin/pytest tests/test_articles.py -q
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- No functional review findings were identified in the current backend/frontend implementation.
- Accepted backend behavior:
- `POST /api/v1/articles` accepts `suppliers[]` and creates `ArticleSupplier` rows
- `PUT /api/v1/articles/{id}` preserves links when `suppliers` is omitted and fully synchronizes links when `suppliers` is provided
- `GET /api/v1/articles/{id}` still returns the enriched `suppliers` list
- `GET /api/v1/suppliers` returns active suppliers only
- Accepted frontend behavior:
- shared Warehouse create/edit form now manages `suppliers[]`
- `manufacturer_art_number` is no longer editable from the shared Warehouse form
- detail Suppliers table is reduced to supplier name, supplier article code, and preferred indicator
- Accepted documentation trace:
- `DEC-WH-008` records the Warehouse form/detail drift from the older Warehouse doc

Verification
- `cd backend && venv/bin/pytest tests/test_articles.py -q` -> `32 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- `stoqio_docs/13_UI_WAREHOUSE.md` still reflects the older Warehouse baseline and is stale versus `DEC-WH-008`.
- No open functional risk remains from implementation review after successful user-side browser validation of the backend-served build.

Next Action
- Treat the Warehouse supplier-linkage implementation as the accepted baseline for this phase.
- Update `stoqio_docs/13_UI_WAREHOUSE.md` in a later docs pass so the written spec matches `DEC-WH-008`.

## Frontend Build Refresh
Date
- 2026-03-23

Context
- User observed unchanged Warehouse UI while testing through the backend-served app.

Action
- Re-ran `./scripts/build.sh` from repo root.
- Confirmed the production frontend bundle was rebuilt and copied into `backend/static`.

Result
- Latest Warehouse supplier-linkage frontend changes are now present in the backend-served build.
- If stale UI still appears in browser, the next likely cause is client-side asset caching rather than a missing production build copy.

## Manual Acceptance
Date
- 2026-03-23

Tester
- User

Outcome
- User confirmed the backend-served application now reflects the latest changes and the phase works correctly in browser testing.
- Warehouse supplier-linkage changes are accepted as working in the live UI.
