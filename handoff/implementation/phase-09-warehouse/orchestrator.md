## Phase Summary

Phase
- Phase 9 - Warehouse

Objective
- Deliver the Warehouse module end to end:
- searchable/filterable articles list with stock + surplus visibility and reorder indicators
- article detail with full master data, FEFO batches, suppliers, aliases, and transaction history
- article create/edit/deactivate flows
- preserve the existing Draft Entry / Receiving article lookup contract while expanding the shared `/api/v1/articles` namespace

Source Docs
- `stoqio_docs/13_UI_WAREHOUSE.md` — full
- `stoqio_docs/09_UI_DRAFT_ENTRY.md` § 5, § 12, § 13
- `stoqio_docs/11_UI_RECEIVING.md` § 7, § 9
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 2, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 2, § 3, § 4, § 7, § 8, § 9, § 16
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.1, § 3.3, § 4
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-004`, `DEC-WH-001`)
- `handoff/README.md`

Current Repo Reality
- `backend/app/api/articles/routes.py` currently implements only the Draft Entry / Receiving exact-match lookup path on `GET /api/v1/articles?q={query}`:
  - one matched article object, not a paginated list
  - FEFO-ordered inline `batches[]` when `has_batch = true`
  - RBAC limited to `OPERATOR` and `ADMIN`
- `frontend/src/api/articles.ts` currently exposes only `articlesApi.lookup(q)` and is consumed by Draft Entry and Receiving ad-hoc receipt flows.
- `frontend/src/routes.tsx` still serves `/warehouse` and `/warehouse/articles/:id` as placeholders.
- `backend/tests/test_drafts.py` currently asserts the exact-match lookup contract and FEFO batch ordering for `GET /api/v1/articles?q={query}`.
- Phase 9 must not silently repurpose the existing `q` lookup into the Warehouse list contract and break active Draft / Receiving flows.

Locked Contract For Phase 9
- `GET /api/v1/articles?page=1&per_page=50&q={query}&category={key}&include_inactive={bool}` is the canonical Warehouse list contract.
- `GET /api/v1/articles?q={query}` with no pagination/filter params remains the exact-match single-article lookup mode reserved for Draft Entry and Receiving compatibility.
- That compatibility lookup continues to return FEFO-ordered inline `batches[]` for batch-tracked articles per `DEC-FE-004`.
- Warehouse list/detail responses expose `reorder_status` using `NORMAL | YELLOW | RED`, computed from `available_qty = stock_total + surplus_total` per `DEC-WH-001`.
- Warehouse form/filter data is loaded from backend lookups:
  - `GET /api/v1/articles/lookups/categories`
  - `GET /api/v1/articles/lookups/uoms`
- `GET /api/v1/articles/{id}` is full Warehouse detail with master data, totals, FEFO batches, suppliers, aliases, and paginated transactions fetched separately.
- `GET /api/v1/articles/{id}/barcode` returns `501 NOT_IMPLEMENTED` in Phase 9. Frontend must not present it as a working action.
- Warehouse UI must use the canonical list/detail/transaction endpoints and the new lookup endpoints, not the compatibility lookup mode.

Delegation Plan
- Backend:
- Expand `/api/v1/articles` into the Warehouse module API while preserving the existing exact-match compatibility mode for Draft Entry and Receiving.
- Frontend:
- Replace the Warehouse placeholders with real list/detail UI and keep the existing `articlesApi.lookup()` behavior intact for Draft Entry / Receiving.
- Testing:
- Add Warehouse backend coverage and re-run Draft Entry regressions so the expanded Articles namespace is proven not to break the live compatibility path.

Acceptance Criteria
- ADMIN can list, inspect, create, edit, and deactivate articles.
- MANAGER can view the Warehouse list, article detail, and transaction history, but cannot mutate data.
- Warehouse list shows stock, surplus, reorder threshold, and subtle reorder indicators.
- Article detail shows FEFO batch data, suppliers, aliases, and paginated transaction history.
- `GET /api/v1/articles?q={query}` remains compatible with Draft Entry and Receiving.
- Barcode endpoint returns `501 NOT_IMPLEMENTED` without creating a misleading live workflow.
- Phase 9 handoff trail is complete across orchestration, backend, frontend, and testing.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first because the frontend depends on the expanded Articles contract, the new form/filter lookup endpoints, and the preserved Draft / Receiving compatibility mode.

## Delegation Prompt - Backend Agent

You are the backend agent for Phase 9 of the WMS project.

Read before coding:
- `stoqio_docs/13_UI_WAREHOUSE.md` — full
- `stoqio_docs/09_UI_DRAFT_ENTRY.md` § 5, § 12, § 13
- `stoqio_docs/11_UI_RECEIVING.md` § 7, § 9
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 2, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 2, § 3, § 4, § 7, § 8, § 9, § 16
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.1, § 3.3, § 4
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-004`, `DEC-WH-001`)
- `handoff/README.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`

Goal
- Implement the Warehouse backend under the shared `/api/v1/articles` namespace without breaking the existing Draft Entry / Receiving exact-match lookup contract.

Non-Negotiable Contract Rules
- Do not repurpose `GET /api/v1/articles?q={query}` into the Warehouse list contract when it is called without pagination/filter params.
- Preserve the current exact-match single-article lookup mode for Draft Entry / Receiving:
  - exact article-number or barcode match
  - `404 ARTICLE_NOT_FOUND` on miss
  - inline FEFO `batches[]` for batch-tracked articles
- Canonical Warehouse list mode is paginated and supports `q`, `category`, and `include_inactive`.
- `reorder_status` uses `NORMAL | YELLOW | RED` and is computed from `stock_total + surplus_total`.
- Barcode is Phase 15 scope; `GET /api/v1/articles/{id}/barcode` returns `501 NOT_IMPLEMENTED` in this phase.
- Keep routes thin. Put Warehouse business logic in a dedicated service layer (`backend/app/services/article_service.py` or equivalent).

Tasks
1. Replace `backend/app/api/articles/routes.py` with the full Phase 9 route set:
   - `GET /api/v1/articles?page=1&per_page=50&q={query}&category={key}&include_inactive={bool}`
   - `GET /api/v1/articles?q={query}` compatibility mode
   - `GET /api/v1/articles/{id}`
   - `POST /api/v1/articles`
   - `PUT /api/v1/articles/{id}`
   - `PATCH /api/v1/articles/{id}/deactivate`
   - `GET /api/v1/articles/{id}/transactions?page=1&per_page=50`
   - `GET /api/v1/articles/{id}/barcode`
   - `GET /api/v1/articles/lookups/categories`
   - `GET /api/v1/articles/lookups/uoms`
2. Warehouse list response:
   - paginated shape per `07_ARCHITECTURE.md`
   - search by article number or description
   - optional category filter by `Category.key`
   - inactive articles excluded by default
   - each item must include at minimum:
     - `id`
     - `article_no`
     - `description`
     - `category_id`
     - `category_key`
     - `category_label_hr`
     - `base_uom`
     - `stock_total`
     - `surplus_total`
     - `reorder_threshold`
     - `reorder_status`
     - `is_active`
3. Warehouse detail response:
   - return full article master data
   - include current `stock_total` and `surplus_total`
   - if `has_batch = true`, include FEFO-ordered `batches[]` with per-batch stock/surplus quantities
   - include `suppliers[]` from `ArticleSupplier`
   - include `aliases[]` from `ArticleAlias`
4. Create / edit article:
   - normalize `article_no` to uppercase
   - validate allowed chars, max length, uniqueness
   - validate referenced category and UOM records exist and are active where appropriate
   - keep create/edit responses consistent with the Warehouse detail contract unless you discover a blocking reason and log it first
5. Deactivate article:
   - soft deactivate only (`is_active = false`)
   - allow deactivation even with stock or pending drafts
   - do not delete history or dependent records
6. Transactions endpoint:
   - paginated, newest first
   - return type, quantity, uom, batch code, reference, user, and timestamp fields required by the Warehouse spec
7. Reorder logic:
   - `RED` when `available_qty <= threshold`
   - `YELLOW` when `threshold < available_qty <= threshold * 1.10`
   - `NORMAL` otherwise
   - if no threshold is configured, return `NORMAL`
8. Lookup endpoints:
   - `GET /api/v1/articles/lookups/categories` returns active categories with at minimum `id`, `key`, `label_hr`
   - `GET /api/v1/articles/lookups/uoms` returns active UOM catalog rows with at minimum `code`, `label_hr`, `decimal_display`
9. RBAC:
   - ADMIN full access
   - MANAGER GET-only on Warehouse list/detail/transactions/lookups
   - preserve OPERATOR/ADMIN access to the exact-match compatibility lookup used by Draft Entry
10. Barcode scaffold:
   - `GET /api/v1/articles/{id}/barcode` returns a standard error body with `501 NOT_IMPLEMENTED`
   - do not start implementing barcode generation in this phase
11. Preserve `backend/tests/test_drafts.py` expectations for article lookup compatibility.

Verification
- Add/update backend tests as needed.
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q`
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q`
  - `backend/venv/bin/pytest backend/tests -q`

Handoff Requirements
- Append your work log to `handoff/implementation/phase-09-warehouse/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover another contract gap with cross-agent impact, add it to `handoff/decisions/decision-log.md` before finalizing backend work.

Done Criteria
- Warehouse backend contract is implemented.
- Draft Entry / Receiving compatibility lookup still works.
- Reorder status, detail data, deactivate flow, transactions, and lookups behave as specified.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Phase 9 of the WMS project.

Read before coding:
- `stoqio_docs/13_UI_WAREHOUSE.md` — full
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.1, § 4, § 5
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-WH-001`)
- `handoff/README.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- Backend handoff for Phase 9 after the backend agent finishes

Goal
- Implement the Warehouse UI for ADMIN and MANAGER without breaking the existing Draft Entry / Receiving article lookup helper behavior.

Non-Negotiable Contract Rules
- Warehouse list must use the canonical paginated `/api/v1/articles` list mode, not the exact-match compatibility lookup mode.
- Existing `articlesApi.lookup()` behavior used by Draft Entry / Receiving must remain intact.
- MANAGER is read-only everywhere in the Warehouse module.
- Barcode printing is not live in Phase 9. Do not present it as a working action.

Tasks
1. Replace the Warehouse placeholders in `frontend/src/routes.tsx` with real lazy-loaded pages:
   - `frontend/src/pages/warehouse/WarehousePage.tsx`
   - `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
2. Expand the frontend API surface for Warehouse articles:
   - canonical list
   - detail
   - create
   - update
   - deactivate
   - transactions
   - category lookup
   - UOM lookup
   - keep the existing exact-match `articlesApi.lookup()` contract working for Draft Entry / Receiving
3. Warehouse list page:
   - debounced search by article number / description
   - category dropdown filter
   - show deactivated toggle
   - subtle reorder indicator per row (`NORMAL` / `YELLOW` / `RED`)
   - columns per the Warehouse spec
   - ADMIN sees `New Article`
   - MANAGER does not
   - empty state: `No articles found.`
4. Create article flow:
   - modal or separate page is your choice
   - fields must cover the article data model required by the spec
   - category and UOM options must come from backend lookup endpoints, not hardcoded constants
   - success toast: `Article created.`
   - redirect or refresh into article detail on success
5. Article detail page:
   - show master data in read-only mode by default
   - inline edit mode for ADMIN with Save / Cancel
   - show stock + surplus summary
   - FEFO batch table when `has_batch = true`
   - suppliers section
   - aliases section
   - paginated transaction history
6. Deactivate flow:
   - confirmation copy must follow the Warehouse spec
   - on success, reflect `is_active = false` in the UI
7. MANAGER behavior:
   - hide create/edit/deactivate actions
   - keep list/detail/transactions readable
8. Barcode action:
   - do not wire a live barcode-print flow in Phase 9
   - if you render the control, it must be clearly disabled/unavailable rather than triggering the `501` endpoint as if it were a finished feature
9. Apply global UI rules:
   - Croatian client-rendered copy by default
   - inline validation for form errors
   - toast success/server errors
   - one automatic retry on network/server failure
   - full-page error state after repeated failure
   - loading indicators for async work

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/implementation/phase-09-warehouse/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record explicitly how you preserved the existing Draft Entry / Receiving article lookup path while adding Warehouse-specific article APIs.

Done Criteria
- Warehouse list/detail/create/edit/deactivate UI is implemented.
- MANAGER read-only behavior is correct.
- Existing Draft Entry / Receiving article lookup behavior is not regressed.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Phase 9 of the WMS project.

Read before coding:
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md` § 12, § 13
- `handoff/decisions/decision-log.md` (`DEC-FE-004`, `DEC-WH-001`)
- `handoff/README.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- Backend handoff for Phase 9 after the backend agent finishes
- Frontend handoff for Phase 9 after the frontend agent finishes

Goal
- Verify that the Warehouse backend contract is covered and that expanding `/api/v1/articles` did not break the existing Draft Entry compatibility lookup.

Tasks
1. Add `backend/tests/test_articles.py` covering at minimum:
   - create article returns `201`
   - stored `article_no` is uppercase
   - duplicate `article_no` returns `409`
   - invalid `article_no` chars return `400`
   - list returns `200` and includes stock totals
   - detail returns `200` and FEFO batch ordering
   - deactivate returns `200` and sets `is_active = false`
   - inactive articles excluded by default
   - MANAGER `GET` returns `200`
   - MANAGER `POST` returns `403`
   - reorder status is correct for `RED`, `YELLOW`, and `NORMAL`
   - barcode scaffold returns `501 NOT_IMPLEMENTED`
2. Re-run the existing Draft Entry article lookup regression coverage:
   - `backend/tests/test_drafts.py`
   - ensure exact-match `GET /api/v1/articles?q={query}` still returns the current compatibility contract with FEFO inline batches
3. If backend/frontend handoffs claim additional critical behavior not covered yet, add the minimum necessary assertions instead of relying on prose alone.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q`
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q`
  - `backend/venv/bin/pytest backend/tests -q`
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/implementation/phase-09-warehouse/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Call out any mismatch between the canonical Warehouse contract and the preserved Draft Entry / Receiving compatibility lookup immediately.

Done Criteria
- Warehouse backend coverage exists.
- Draft Entry compatibility lookup regressions are checked.
- Verification is recorded in handoff.

## Validation Note - 2026-03-13 17:19:31 CET

Status
- In review; not closed yet.

Accepted Work
- Backend implemented the shared `/api/v1/articles` Warehouse contract with preserved Draft Entry / Receiving exact-match lookup compatibility, new Warehouse detail/transactions/lookups routes, and the Phase 9 barcode scaffold.
- Frontend replaced the `/warehouse` placeholders with real Warehouse list/detail screens and kept the existing `articlesApi.lookup(q)` compatibility helper intact for Draft Entry / Receiving.
- Testing added dedicated Warehouse backend coverage, re-ran the Draft Entry article lookup regressions, and re-ran the broader backend/frontend verification suite.
- Declared verification is reproducible on the current worktree:
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `14 passed`
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q` -> `30 passed`
  - `backend/venv/bin/pytest backend/tests -q` -> `131 passed`
  - `cd frontend && npm run lint -- --max-warnings=0` -> pass
  - `cd frontend && npm run build` -> pass

Rejected / Missing Items
- Deactivate flow does not implement the Warehouse-spec warning for articles with open drafts. The detail payload currently exposes no pending-draft indicator, and the frontend confirmation logic only adds the stock-on-hand warning:
  - spec requires `"This article has pending drafts. Deactivating will not affect existing drafts."`
  - current frontend only conditionally adds `"This article still has stock on hand."`
  - refs: `stoqio_docs/13_UI_WAREHOUSE.md` § 11 edge cases, `frontend/src/pages/warehouse/ArticleDetailPage.tsx`, `backend/app/services/article_service.py`
- Warehouse frontend still contains mixed English client-rendered copy (`New Article`, `Article created.`, `Article updated.`, `Article deactivated.`, `No articles found.`, `No transactions found.`), which does not satisfy the Croatian-by-default global UI rule applied elsewhere in v1:
  - refs: `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1, `frontend/src/pages/warehouse/WarehousePage.tsx`, `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Next Action
- Run a short Phase 9 follow-up lane for backend, frontend, and testing to:
  - add the missing open-drafts deactivation warning support
  - normalize the remaining Warehouse client-rendered copy to Croatian
  - re-verify the Warehouse + Draft Entry compatibility paths
- Append a final closeout note here only after those two items are resolved.

## Final Closeout - 2026-03-13 17:42:03 CET

Status
- Phase 9 formally closed on the current baseline.

Accepted Work
- Backend/frontend/testing Phase 9 deliveries remain accepted, and the two review blockers were remediated directly by the orchestrator instead of reopening a new agent lane.
- Warehouse article detail now exposes `has_pending_drafts` and `pending_draft_count`, so the deactivate confirmation can warn about open drafts without an extra request.
- Warehouse UI now keeps client-rendered and surfaced article-API copy in Croatian on the reviewed paths.
- Reviewed Croatian paths now include create/update/deactivate success and error states.
- Reviewed Croatian paths now include list/detail full-page fallback messages.
- Reviewed Croatian paths now include transaction and empty states.
- Reviewed Croatian paths now include reorder labels.
- Reviewed Croatian paths now include alias section labels.
- Reviewed Croatian paths now include open-drafts + stock-on-hand deactivate confirmation copy.
- Shared sidebar navigation was localized to Croatian so the Warehouse module entrypoint no longer reintroduces mixed-language UI around the module.
- `frontend/dist` was copied into `backend/static` after the successful production build, so the Flask-served UI in this workspace reflects the same Warehouse fixes.
- `DEC-WH-004` and the Warehouse spec now document the post-review baseline for future agents.

Files Changed By Orchestrator
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- `frontend/dist/` (generated build output refreshed by `npm run build`)
- `backend/static/` (generated Flask-served frontend synced from `frontend/dist`)

Verification
- `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `14 passed`
- `backend/venv/bin/pytest backend/tests/test_drafts.py -q` -> `30 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `131 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- `cp -R frontend/dist/. backend/static/` -> pass

Residual Notes
- The initial Phase 9 backend/frontend/testing handoffs stay valid; this closeout records targeted orchestrator remediation after review rather than a separate delegated mini-phase.
- Broader project-wide localization outside the Phase 9 Warehouse surface and the shared sidebar remains separate work if you want a full Croatian sweep later.

Next Action
- Start Phase 10 on top of the closed Warehouse baseline and treat `DEC-WH-001` through `DEC-WH-004` as the active contract.

## Validation Note - 2026-03-13 18:01:15 CET (Density Hidden In UI)

Status
- Phase 9 remains closed; post-closeout UI simplification applied.

Accepted Work
- Orchestrator removed `density` from the visible Warehouse create/edit form and from the Warehouse article detail screen.
- Warehouse frontend now treats `density` as a hidden technical field and always submits `1.0` in create/edit payloads.
- Backend/schema behavior is unchanged: `Article.density` still exists in the model/API for compatibility and future use.
- `DEC-WH-005` and `stoqio_docs/13_UI_WAREHOUSE.md` now document that `density` exists but is not displayed in the v1 Warehouse UI.

Files Changed By Orchestrator
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`

Verification
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- `cp -R frontend/dist/. backend/static/` -> pass

Residual Notes
- Existing articles with non-`1.0` stored density values remain in the database unless edited through the Warehouse UI. Once saved through the current UI, they are normalized to `1.0`.

Next Action
- Keep using the hidden-`density` Warehouse baseline from `DEC-WH-005` unless the product requirement changes.

## Validation Note - 2026-03-13 18:22:45 CET (Coverage Days Hidden In UI)

Status
- Phase 9 remains closed; post-closeout UI simplification applied.

Accepted Work
- Orchestrator removed `reorder_coverage_days` from the visible Warehouse create/edit form and from the Warehouse article detail screen.
- Backend/schema behavior is unchanged: `Article.reorder_coverage_days` still exists in the model/API for compatibility and future planning use.
- Current Warehouse reorder behavior remains unchanged and still depends only on `reorder_threshold`.
- `DEC-WH-006` and `stoqio_docs/13_UI_WAREHOUSE.md` now document that `reorder_coverage_days` exists but is not displayed in the v1 Warehouse UI.

Files Changed By Orchestrator
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`

Verification
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- `cp -R frontend/dist/. backend/static/` -> pass

Residual Notes
- Existing `reorder_coverage_days` values remain stored in the database and continue to round-trip through the backend API, but the current Warehouse UI no longer exposes them.

Next Action
- Keep using the hidden-`reorder_coverage_days` Warehouse baseline from `DEC-WH-006` unless the future reorder-automation feature is explicitly scheduled.

## Validation Note - 2026-03-13 18:36:56 CET (Batch Tracking Label Clarified)

Status
- Phase 9 remains closed; post-closeout terminology clarification applied.

Accepted Work
- Orchestrator renamed the visible Warehouse UI label for `has_batch` from `"Praćenje po šaržama"` to `"Artikl sa šaržom"` in the create/edit form, article detail screen, and shared Warehouse API/error label mapping.
- Backend/API naming and behavior are unchanged: the stored field remains `has_batch`.
- `DEC-WH-007` and `stoqio_docs/13_UI_WAREHOUSE.md` now document the revised Croatian wording as the canonical Warehouse UI label.

Files Changed By Orchestrator
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`

Verification
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- `cp -R frontend/dist/. backend/static/` -> pass

Residual Notes
- This is a terminology/UI-only adjustment. No backend schema, API contract, or test behavior changed.

Next Action
- Use the `DEC-WH-007` terminology baseline in future Warehouse work unless product wording changes again.
