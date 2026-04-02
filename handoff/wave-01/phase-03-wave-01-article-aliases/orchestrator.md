## Phase Summary

Phase
- Wave 1 - Phase 3 - Article Aliases

Objective
- Allow ADMIN users to add and delete article aliases directly from the Warehouse article detail page.
- Keep Identifier search behavior aligned with alias normalization so new aliases become searchable without extra follow-up work.
- Preserve MANAGER read-only access to the alias list on article detail.

Source Docs
- `stoqio_docs/05_DATA_MODEL.md` § 4
- `stoqio_docs/14_UI_IDENTIFIER.md` § 7, § 8, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 5
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-ID-004`, `DEC-WH-008`)

Current Repo Reality
- `ArticleAlias` already exists in the data model with `alias` and `normalized` fields.
- Identifier search already resolves alias matches from `ArticleAlias.normalized` inside `backend/app/services/article_service.py`.
- `GET /api/v1/articles/{id}` already returns an `aliases[]` array in the Warehouse detail payload.
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx` currently renders aliases as a read-only table showing `alias` and `normalized`.
- No dedicated alias create/delete API endpoints exist yet.

Delegation Plan
- Backend:
- Add article-alias create/delete endpoints, keep the Warehouse detail payload compatible, and preserve Identifier alias-search behavior.
- Frontend:
- Replace the read-only alias table with inline alias management on article detail while keeping MANAGER read-only.
- Testing:
- Add dedicated backend coverage in `backend/tests/test_aliases.py` and verify alias mutations plus alias-backed Identifier discovery.

Acceptance Criteria
- `POST /api/v1/articles/{id}/aliases` creates an alias, stores original plus normalized forms, and returns `201`.
- Duplicate aliases for the same article conflict on normalized value and return `409` with message `"Alias already exists."`.
- `DELETE /api/v1/articles/{id}/aliases/{alias_id}` deletes an alias and returns `204`; missing aliases return `404`.
- `GET /api/v1/articles/{id}` includes aliases for the Warehouse detail page without regressing current detail access rules.
- Warehouse article detail shows aliases inline in read mode; ADMIN can add/delete without entering the general article edit mode.
- MANAGER can still see aliases but cannot mutate them.
- Identifier search finds an article by a newly added alias.
- The phase leaves a complete handoff trail across orchestration, backend, frontend, and testing.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first because the frontend and dedicated regression file both depend on the new alias endpoints and duplicate-handling contract.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 3 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/05_DATA_MODEL.md` § 4
- `stoqio_docs/14_UI_IDENTIFIER.md` § 7, § 8, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 5
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-ID-004`, `DEC-WH-008`)
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`
- `backend/app/models/article_alias.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`

Goal
- Add ADMIN-only article-alias create/delete endpoints under the existing Warehouse articles namespace without regressing the current Warehouse detail payload or Identifier alias search behavior.

Non-Negotiable Contract Rules
- Alias normalization for conflict detection is lowercase + strip surrounding whitespace.
- Alias uniqueness is scoped per article on the normalized value. Do not make aliases globally unique across all articles.
- `POST /api/v1/articles/{id}/aliases` returns `201` with the created alias object.
- If the same normalized alias already exists for the same article, return `409` with message `"Alias already exists."`.
- `DELETE /api/v1/articles/{id}/aliases/{alias_id}` returns `204`.
- `GET /api/v1/articles/{id}` must continue to include `aliases[]`. The current enriched shape with `id`, `alias`, and `normalized` is already live; do not narrow it.
- Identifier search must keep matching against alias normalized values after alias creation.

Tasks
1. Add backend helpers for alias normalization and alias CRUD inside the articles service layer.
2. Implement `POST /api/v1/articles/{id}/aliases`:
   - request body: `{ "alias": "string" }`
   - validate the article exists
   - normalize for duplicate detection using lowercase + trim
   - persist the display alias plus normalized value
   - return the created alias row serialized for the client
3. Implement `DELETE /api/v1/articles/{id}/aliases/{alias_id}`:
   - delete only if the alias belongs to the specified article
   - return `404` if the alias does not exist or belongs to a different article
4. Preserve `GET /api/v1/articles/{id}` alias inclusion and verify the detail response still includes aliases after your route/service changes.
5. RBAC:
   - `POST` and `DELETE` are ADMIN only
   - `GET /api/v1/articles/{id}` stays under the existing Warehouse detail access rules
6. Robustness:
   - if you add DB-level enforcement, scope it to `(article_id, normalized)` and add the required migration
   - translate duplicate conflicts into the standard error body with the exact `"Alias already exists."` message
   - reject unusable blank aliases if trimming leaves no content
7. Do not break the existing Identifier search path or Warehouse detail serialization while adding the new endpoints.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q`
- If you add or touch any other backend regression coverage during implementation, run those files too and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-03-wave-01-article-aliases/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover a contract gap with cross-agent impact, add it to `handoff/decisions/decision-log.md` before finalizing backend work.

Done Criteria
- Alias create/delete endpoints are implemented and documented in handoff.
- Duplicate handling, article scoping, and RBAC match the orchestrator contract.
- Warehouse detail still returns aliases and Identifier alias matching still works.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 3 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/13_UI_WAREHOUSE.md` § 5
- `stoqio_docs/14_UI_IDENTIFIER.md` § 7
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-ID-004`, `DEC-WH-008`)
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/api/articles.ts`

Goal
- Update the Warehouse article detail page so aliases are managed inline in the existing read-mode detail view.

Non-Negotiable Contract Rules
- The alias section stays visible in read mode; do not hide it behind the general article edit mode toggle.
- ADMIN can add and delete aliases inline.
- MANAGER remains read-only and can only view the alias list.
- On duplicate add (`409`), show an inline error: `"This alias already exists."`.
- On successful add/delete, refresh the displayed alias list without a full page reload.
- Keep the rest of the article detail screen behavior unchanged.

Tasks
1. Expand `frontend/src/api/articles.ts` with alias mutation helpers for:
   - `POST /api/v1/articles/{id}/aliases`
   - `DELETE /api/v1/articles/{id}/aliases/{alias_id}`
2. Replace the current read-only alias table in `frontend/src/pages/warehouse/ArticleDetailPage.tsx` with an inline alias-management section:
   - existing aliases rendered as Mantine badges/chips/pills
   - ADMIN view includes a delete affordance per alias
   - MANAGER view renders the same aliases without delete controls
3. Add an inline ADMIN-only add form below the alias list:
   - text input
   - add button
   - clear input after success
4. Mutation behavior:
   - on add success: refresh alias state, clear input, clear inline errors
   - on delete success: refresh alias state
   - on `409`: show the required inline duplicate error instead of a toast-only failure
   - on retryable network/server failures: follow the page's existing fatal-error pattern rather than inventing a new error mode
5. Keep the alias section available even when the article is not in edit mode. This is a dedicated inline action area, not part of the broader Warehouse article form editing flow.

Verification
- Run at minimum:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-03-wave-01-article-aliases/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If backend contract details differ from the orchestrator brief, log the gap before finalizing.

Done Criteria
- Alias section on article detail supports ADMIN add/delete inline.
- MANAGER remains read-only.
- Duplicate add errors are shown inline.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 3 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `backend/tests/test_articles.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`

Goal
- Add targeted backend regression coverage for article alias management and verify the new contract end to end.

Tasks
1. Create `backend/tests/test_aliases.py`.
2. Cover at minimum:
   - add alias -> `201`, alias saved with normalized form
   - add duplicate alias -> `409`
   - add alias with different casing of existing alias -> `409`
   - delete alias -> `204`, alias removed
   - delete non-existent alias -> `404`
   - `GET /api/v1/articles/{id}` includes aliases list
   - non-admin cannot `POST` or `DELETE` -> `403`
   - after creating an alias, Identifier search for that alias finds the article
3. Reuse existing backend fixture patterns where practical; do not rewrite unrelated warehouse coverage.
4. Keep assertions aligned with the standard API error shape and the exact duplicate message `"Alias already exists."`.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_aliases.py -q`
- Also run any additional targeted regressions you touch or depend on, and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-03-wave-01-article-aliases/testing.md`.
- Use the section shape required by `handoff/README.md`.
- If you find a spec or contract mismatch, log it immediately in your handoff and reference the blocking behavior precisely.

Done Criteria
- `backend/tests/test_aliases.py` exists and covers the required alias flows.
- Targeted verification is green and recorded in handoff.

## [2026-03-23 19:44] Orchestrator Validation - Wave 1 Phase 3 Article Aliases

Status
- backend and testing accepted; frontend follow-up required before full closeout

Scope
- Reviewed the delivered backend, frontend, and testing changes for inline alias management on the Warehouse article detail screen.
- Corrected the mistaken sequential-phase naming to the Wave 1 / Phase 3 naming scheme across the active handoff trail and decision log.

Docs Read
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-01/phase-03-wave-01-article-aliases/backend.md`
- `handoff/wave-01/phase-03-wave-01-article-aliases/frontend.md`
- `handoff/wave-01/phase-03-wave-01-article-aliases/testing.md`
- `backend/app/api/articles/routes.py`
- `backend/app/models/article_alias.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_aliases.py`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Commands Run
```bash
git status --short
git diff -- backend/app/models/article_alias.py backend/app/api/articles/routes.py backend/app/services/article_service.py backend/tests/test_aliases.py frontend/src/api/articles.ts frontend/src/pages/warehouse/ArticleDetailPage.tsx handoff/decisions/decision-log.md handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md handoff/wave-01/phase-03-wave-01-article-aliases/backend.md handoff/wave-01/phase-03-wave-01-article-aliases/frontend.md handoff/wave-01/phase-03-wave-01-article-aliases/testing.md
backend/venv/bin/pytest backend/tests/test_aliases.py -q
backend/venv/bin/pytest backend/tests/test_articles.py -q
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- Accepted backend behavior:
- `POST /api/v1/articles/{id}/aliases` and `DELETE /api/v1/articles/{id}/aliases/{alias_id}` match the requested RBAC and per-article normalized-duplicate contract.
- `GET /api/v1/articles/{id}` still exposes aliases and Identifier search still resolves alias hits.
- Accepted testing coverage:
- `backend/tests/test_aliases.py` covers create, duplicate rejection, delete, missing delete, detail inclusion, RBAC, and Identifier discovery through alias search.
- Review finding:
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx` alias add/delete mutations do not use `runWithRetry`, unlike the rest of this page's mutation pattern. Retryable network/server failures therefore escalate immediately to the fatal page state instead of following the established retry-then-fatal behavior required by the phase brief.
- Documentation note:
- the backend/frontend/testing handoff entries do not fully match the required section shape from `handoff/README.md`; this validation entry is the canonical review record for acceptance status.

Verification
- `backend/venv/bin/pytest backend/tests/test_aliases.py -q` -> `8 passed`
- `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `32 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- Frontend alias mutation flows still need a retry pass to match the Warehouse page's established network/server failure handling.

Next Action
- Apply a small frontend follow-up so alias add/delete use the same retry semantics as the rest of `ArticleDetailPage`, then re-run frontend lint/build and close Wave 1 Phase 3.

## [2026-03-23 19:50] Orchestrator Follow-Up - Alias Retry Remediation

Status
- completed

Scope
- Applied the frontend-only follow-up directly as orchestrator to resolve the accepted retry-handling review finding on alias mutations.
- Refreshed the production frontend bundle so backend-served browser testing uses the remediated build.

Files Changed
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`

What Changed
- `handleAddAlias` now wraps `articlesApi.createAlias(...)` in `runWithRetry(...)`.
- `handleDeleteAlias` now wraps `articlesApi.deleteAlias(...)` in `runWithRetry(...)`.
- Alias add/delete flows now match the established retry-then-fatal mutation behavior already used elsewhere on `ArticleDetailPage`.
- Rebuilt the frontend and copied the fresh bundle into `backend/static` via `./scripts/build.sh`.

Verification
- `cd frontend && npm run lint`
- `./scripts/build.sh`

Result
- The previously accepted frontend behavior remains intact, and retryable network/server failures on alias add/delete now follow the same mutation policy as the rest of the page.
- Backend-served UI assets are refreshed for browser verification.

Next Action
- Wave 1 Phase 3 can now proceed to browser re-test on the backend-served app using the refreshed static bundle.

## [2026-03-23 20:28] Orchestrator Repo-Health Follow-Up - Alias Test Isolation

Status
- completed

Scope
- Fixed the backend test isolation issue discovered later during Wave 1 Phase 4 validation, where alias-suite mutations leaked into Warehouse article-detail assertions.

Files Changed
- `backend/tests/test_aliases.py`
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`

What Changed
- Added per-test alias cleanup in `backend/tests/test_aliases.py` so aliases created by alias tests do not persist into later backend modules.
- Made the casing-duplicate alias test self-contained instead of depending on another alias test having already created `"Duplicate Test"`.

Verification
- `backend/venv/bin/pytest backend/tests/test_aliases.py backend/tests/test_articles.py -q` -> `40 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `277 passed, 1 warning`

Result
- The previously observed alias-fixture contamination is resolved.
- The backend suite is now clean again, aside from the known SQLite Alembic warning unrelated to Phase 3 behavior.

Next Action
- No additional Phase 3 follow-up remains open from this test-isolation issue.
