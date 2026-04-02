## Phase Summary

Phase
- Wave 1 - Phase 9 - Search Dropdown Prefetch

Objective
- Fix the affected search dropdowns so an empty focused field shows the full available list immediately.
- Add small backend contract improvements where they materially simplify the frontend and avoid fetching unnecessary data.
- Keep the changes additive so existing Orders, Receiving, and Warehouse contracts continue to work.

Source Docs
- `stoqio_docs/12_UI_ORDERS.md` § 4, § 10
- `stoqio_docs/11_UI_RECEIVING.md` § 3, § 4, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-07-receiving/orchestrator.md`
- `handoff/implementation/phase-08-orders/orchestrator.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- `handoff/implementation/phase-09-warehouse/frontend.md`

Current Repo Reality
- `frontend/src/pages/orders/OrdersPage.tsx` currently uses debounced remote supplier search via `ordersApi.lookupSuppliers(q)`. When the field is empty, it clears the options array, so clicking into the empty field does not show the full list.
- `frontend/src/pages/receiving/ReceivingPage.tsx` currently uses a plain text input plus exact-match submit flow for linked order lookup. It is not yet implemented as a dropdown/combobox-style picker.
- `frontend/src/pages/warehouse/WarehousePage.tsx` and `frontend/src/pages/warehouse/ArticleDetailPage.tsx` already preload supplier options through `articlesApi.lookupSuppliers()`, but the shared `WarehouseArticleForm.tsx` supplier `Select` still relies on default searchable-select behaviour and does not explicitly guarantee the empty-focus full-list UX.
- Backend currently has:
  - `GET /api/v1/suppliers` -> full active supplier array
  - `GET /api/v1/orders?page=1&per_page=50` -> canonical paginated Orders list
  - `GET /api/v1/orders?q={order_number}` -> Receiving exact-match compatibility mode
  - no additive `status` filter on Orders list mode yet
  - no additive paginated preload mode on `/suppliers` yet

Locked Contract For This Wave
- This wave is additive. Do not break existing consumers of:
  - bare `GET /api/v1/suppliers`
  - `GET /api/v1/orders?q={order_number}`
- Supplier preload contract for the new dropdown UX:
  - `GET /api/v1/suppliers?per_page=200`
  - returns paginated shape `{ items, total, page, per_page }`
  - `page` defaults to `1` when omitted
  - bare `GET /api/v1/suppliers` must keep the current array contract for compatibility
- Orders preload contract for Receiving dropdown UX:
  - `GET /api/v1/orders?status=OPEN&per_page=200`
  - uses normal paginated Orders list shape
  - `status` filter applies only to list mode when `q` is absent
  - `GET /api/v1/orders?q={order_number}` remains exact-match Receiving compatibility mode and must not be repurposed into list search
- Frontend dropdown behaviour:
  - empty field on focus/click shows full prefetched list immediately
  - typing filters locally with case-insensitive matching
  - `"Nema rezultata."` appears only when the user typed a non-empty query that matches nothing
  - dropdown panel stays scrollable with a practical max-height

Affected Locations
- Backend:
  - `backend/app/api/orders/routes.py`
  - `backend/app/services/order_service.py`
  - `backend/app/api/articles/routes.py`
  - `backend/app/services/article_service.py`
  - `backend/tests/test_orders.py`
  - `backend/tests/test_articles.py`
- Frontend:
  - `frontend/src/pages/orders/OrdersPage.tsx`
  - `frontend/src/pages/receiving/ReceivingPage.tsx`
  - `frontend/src/pages/warehouse/WarehousePage.tsx`
  - `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
  - `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
  - `frontend/src/api/orders.ts`
  - `frontend/src/api/articles.ts`

Delegation Plan
- Backend:
- add the minimal additive preload/list filters needed for cleaner dropdown contracts without breaking existing compatibility paths
- Frontend:
- switch the affected controls to preload + local filtering using the new additive contracts
- Testing:
- lock backend regression coverage for the additive supplier/orders preload contracts and rerun relevant frontend verification

Acceptance Criteria
- New Order: clicking the empty Supplier field shows the full supplier list immediately.
- New Order: typing filters that supplier list locally and clearing the field restores the full list.
- Receiving: clicking the empty linked-order field shows the full list of OPEN orders immediately.
- Receiving: typing filters locally and selecting an order continues into the existing receiving-detail flow.
- New Article / Edit Article: clicking the empty Supplier field shows the full supplier list immediately.
- `GET /api/v1/orders?q={order_number}` still behaves exactly as the Receiving exact-match lookup.
- Bare `GET /api/v1/suppliers` still behaves as before for existing compatibility callers.
- None of the affected controls show `"Nema rezultata."` for an empty field.
- The phase leaves a complete orchestration, backend, frontend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the additive preload contracts are explicit before Frontend and Testing proceed.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 9 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/12_UI_ORDERS.md` § 4, § 10
- `stoqio_docs/11_UI_RECEIVING.md` § 3, § 4, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-08-orders/orchestrator.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/orchestrator.md`
- `backend/app/api/orders/routes.py`
- `backend/app/services/order_service.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_orders.py`
- `backend/tests/test_articles.py`

Goal
- Add the minimal backend contract improvements needed to support efficient dropdown prefetch flows.
- Keep the changes additive and compatible with the existing Orders, Receiving, and Warehouse contracts.

Non-Negotiable Contract Rules
- Do not break `GET /api/v1/orders?q={order_number}`. It remains the Receiving exact-match compatibility mode.
- Do not break bare `GET /api/v1/suppliers`, which currently returns an active-suppliers array and is already used by Warehouse code.
- Additive supplier preload mode:
  - `GET /api/v1/suppliers?per_page=200`
  - paginated response shape `{ items, total, page, per_page }`
  - if `page` is omitted, default to `1`
  - active suppliers only
- Additive Orders list filter mode:
  - `GET /api/v1/orders?status=OPEN&per_page=200`
  - uses the canonical paginated Orders list contract
  - `status` applies only when `q` is absent
  - support at minimum `OPEN` and `CLOSED`
- Keep routes thin and business logic in services.

Tasks
1. Extend `GET /api/v1/suppliers` in the Articles/Warehouse namespace:
   - keep bare mode compatibility unchanged
   - when pagination params are present (`page` and/or `per_page`), return paginated preload mode
   - order suppliers consistently by name then id
   - return active suppliers only
2. Extend `GET /api/v1/orders` list mode with an optional `status` filter:
   - list mode stays paginated
   - `status=OPEN` returns only open orders
   - `status=CLOSED` returns only closed orders
   - if `q` is present, preserve exact-match Receiving compatibility behaviour and ignore list-only filtering logic
3. Validate query params defensively:
   - `page` and `per_page` must be positive integers
   - invalid `status` returns `400 VALIDATION_ERROR`
4. Keep existing RBAC intact:
   - `/orders` remains `ADMIN` and `MANAGER`
   - `/suppliers` remains `ADMIN` and `MANAGER`
5. Add/update backend regression coverage for:
   - paginated supplier preload mode
   - bare supplier compatibility mode unchanged
   - Orders list `status=OPEN`
   - Orders list `status=CLOSED`
   - `GET /api/v1/orders?q=...` exact-match compatibility unchanged after adding `status`
6. If this wave exposes a cross-agent contract choice that should be locked, log it in `handoff/decisions/decision-log.md` before finalizing.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_orders.py -q`
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q`
- If you touch shared behavior beyond those modules, run additional targeted tests and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and assumptions.
- If any existing caller would break under the additive contract, log that risk explicitly.

Done Criteria
- Additive supplier preload mode exists without breaking bare `/suppliers`.
- Additive Orders `status` list filter exists without breaking Receiving exact-match `q` mode.
- Backend verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 9 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/12_UI_ORDERS.md` § 4, § 10
- `stoqio_docs/11_UI_RECEIVING.md` § 3, § 4, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/implementation/phase-07-receiving/orchestrator.md`
- `handoff/implementation/phase-08-orders/orchestrator.md`
- `handoff/implementation/phase-09-warehouse/orchestrator.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/api/orders.ts`
- `frontend/src/api/articles.ts`

Goal
- Fix the affected search dropdowns so an empty focused field immediately shows the full list, then filters locally as the user types.
- Use the additive backend preload contracts from this wave instead of refetching on every keystroke.

Locked Contract Rules
- Supplier preload path for this wave:
  - `GET /api/v1/suppliers?per_page=200`
- Open-order preload path for this wave:
  - `GET /api/v1/orders?status=OPEN&per_page=200`
- `GET /api/v1/orders?q={order_number}` still exists for exact-match Receiving compatibility, but the dropdown prefetch should use the new filtered list mode first.
- Do not regress existing submit flows or payload shapes.

Tasks
1. Update the affected frontend controls so they all follow the same empty-focus pattern:
   - New Order supplier field in `frontend/src/pages/orders/OrdersPage.tsx`
   - linked-order picker in `frontend/src/pages/receiving/ReceivingPage.tsx`
   - supplier selects inside `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
2. Use the additive preload contracts from this wave:
   - suppliers from `GET /api/v1/suppliers?per_page=200`
   - open orders from `GET /api/v1/orders?status=OPEN&per_page=200`
3. Keep the full prefetched list in local state after load. Lazy-load on first focus/open if you prefer, but do not keep refetching on every keystroke once the list is available.
4. On focus/click of an empty field, show the full prefetched list immediately.
5. As the user types, filter locally with case-insensitive matching:
   - supplier fields: supplier name and internal code
   - receiving order field: order number, and supplier name too if that stays simple
6. `"Nema rezultata."` handling:
   - do not show it when the search field is empty
   - only show it when `query.trim() !== ''` and the filtered list is empty
7. Make the dropdown panel scrollable with a max-height so a longer prefetched list remains usable.
8. Preserve existing workflow outcomes:
   - New Order still validates and submits the selected supplier id
   - Receiving still resolves one selected order and then loads receiving detail for that order
   - Clearing a receiving selection clears stale linked-order detail state
   - Warehouse supplier rows still submit the same payload shape as before
9. Keep existing retry and fatal-error patterns already used on these pages. A failed preload should not silently leave the control in a misleading empty state.
10. A small shared helper for local filtering is fine if it reduces duplication across these controls, but do not broaden this into a large new abstraction unless it clearly pays off.

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Manually verify and record:
  - New Order -> click empty Supplier -> full supplier list appears immediately
  - New Order -> type partial supplier -> list filters locally
  - Receiving -> click empty order field -> all OPEN orders appear immediately
  - Receiving -> type partial order number -> list filters locally
  - New Article -> click empty Supplier -> full supplier list appears immediately
  - Edit Article -> click empty Supplier -> full supplier list appears immediately
  - Empty field never shows `"Nema rezultata."` in these controls

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests/build verification, manual verification notes, open issues, and assumptions.
- If the backend contract differs from this brief, log the mismatch in handoff before finalizing.

Done Criteria
- All three affected frontend flows show the full list on empty focus and filter locally while typing.
- Empty fields no longer show `"Nema rezultata."`.
- Existing Orders, Receiving, and Warehouse submit flows remain intact.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 9 of the STOQIO WMS project.

Read before testing:
- `stoqio_docs/12_UI_ORDERS.md` § 4, § 10
- `stoqio_docs/11_UI_RECEIVING.md` § 3, § 4, § 9, § 10
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `handoff/README.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- frontend handoff for this phase after the frontend agent finishes
- `backend/tests/test_orders.py`
- `backend/tests/test_articles.py`
- `backend/app/services/order_service.py`
- `backend/app/services/article_service.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/articles/routes.py`

Goal
- Lock regression coverage for the additive backend preload contracts and verify the frontend wave did not drift from the intended dropdown behaviour.

Tasks
1. Extend backend coverage where needed so the wave protects at minimum:
   - `GET /api/v1/orders?status=OPEN&per_page=200` returns only open orders in paginated list mode
   - `GET /api/v1/orders?status=CLOSED&per_page=200` returns only closed orders in paginated list mode
   - `GET /api/v1/orders?q={order_number}` still behaves as the exact-match Receiving compatibility path
   - `GET /api/v1/suppliers?per_page=200` returns paginated preload shape
   - bare `GET /api/v1/suppliers` still preserves the existing compatibility shape
2. If the backend implementation has edge cases around omitted `page`, invalid `status`, or inactive suppliers, add explicit coverage for those too.
3. Reuse existing Orders/Articles fixture/setup patterns where practical; do not rewrite unrelated scaffolding.
4. Re-run relevant backend tests and record the results.
5. Re-run frontend static verification and record it:
   - `cd frontend && npm run lint -- --max-warnings=0`
   - `cd frontend && npm run build`
6. If you can do a quick manual UI smoke check, record what was validated. If not, say so explicitly.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_orders.py -q`
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q`
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and assumptions.
- If you find a contract mismatch, log it immediately in handoff with the precise failing behaviour.

Done Criteria
- Backend regression coverage exists for the additive supplier/orders preload contracts and their compatibility paths.
- Frontend verification is recorded.
- Any residual manual verification gap is stated explicitly.

## [2026-03-24 21:37 CET] Orchestrator Validation - Wave 1 Phase 9 Search Dropdown Prefetch

Status
- accepted

Scope
- Reviewed backend, frontend, and testing delivery for Wave 1 Phase 9.
- Confirmed the wave was expanded in agreement with the user from the original frontend-only brief to include additive backend contract support plus matching testing coverage.

Docs Read
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/orchestrator.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/backend.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/frontend.md`
- `handoff/wave-01/phase-09-wave-01-search-dropdown-prefetch/testing.md`
- `handoff/decisions/decision-log.md`

Accepted Work
- Backend added additive preload support without breaking compatibility:
  - paginated preload mode on `GET /api/v1/suppliers?per_page=...`
  - optional `status=OPEN|CLOSED` filter on `GET /api/v1/orders` list mode
  - preserved bare `GET /api/v1/suppliers` flat-array compatibility
  - preserved `GET /api/v1/orders?q={order_number}` exact-match Receiving compatibility
- Frontend updated all three targeted flows to preload options and filter locally:
  - Orders supplier select
  - Receiving open-order picker
  - Warehouse supplier selects in create/edit form
- Testing locked the additive backend contracts and re-ran frontend static verification.
- `handoff/decisions/decision-log.md` records the additive supplier/orders contract choice in `DEC-WH-009`.

Rejected / Missing Items
- None.

Verification
- Orchestrator reran:
  - `backend/venv/bin/pytest backend/tests/test_orders.py -q` -> `14 passed`
  - `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `35 passed`
  - `cd frontend && npm run lint -- --max-warnings=0` -> passed
  - `cd frontend && npm run build` -> passed

Residual Risks
- No code-level blockers found.
- Manual browser smoke validation of the dropdown UX was not executed in this session, so the UX behaviour is accepted based on code review plus automated verification.
- Receiving preload currently caps the open-order dropdown at `per_page=200`; acceptable for the current project scale, but it remains the practical upper bound of the prefetched list.

Closeout Decision
- Wave 1 Phase 9 is accepted and closed.
