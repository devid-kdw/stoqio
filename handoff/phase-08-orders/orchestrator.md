## Phase Summary

Phase
- Phase 8 - Orders

Objective
- Deliver the Orders module end to end:
- lock the final Orders API contract before delegation
- replace the temporary Phase 7 Receiving-only Orders scaffold
- preserve Receiving compatibility explicitly
- implement backend routes, PDF generation, frontend Orders UI, and automated tests

Source Docs
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 7
- `stoqio_docs/05_DATA_MODEL.md` § 3, § 13, § 14
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-006`, `DEC-ORD-001`)
- `handoff/README.md`

Current Repo Reality
- `backend/app/api/orders/routes.py` is still the Phase 7 Receiving-only scaffold:
  - `GET /api/v1/orders?q={order_number}` exact-match summary
  - `GET /api/v1/orders/{id}` receiving-oriented filtered detail
- `frontend/src/api/orders.ts` and `frontend/src/pages/receiving/ReceivingPage.tsx` currently depend on that temporary contract.
- `frontend/src/routes.tsx` still serves `/orders` and `/orders/:id` as placeholders.
- Phase 8 must not build the Orders module on top of the old Receiving contract by assumption.

Locked Contract For Phase 8
- `GET /api/v1/orders?page=1&per_page=50` is the canonical paginated Orders list.
- `GET /api/v1/orders?q={order_number}` remains an exact-match summary mode reserved for Receiving compatibility.
- `GET /api/v1/orders/{id}` is the canonical full Orders detail contract with all lines.
- `GET /api/v1/orders/{id}?view=receiving` preserves the Receiving-oriented filtered detail contract.
- `GET /api/v1/orders/lookups/suppliers?q={query}` provides supplier lookup for the Orders form.
- `GET /api/v1/orders/lookups/articles?q={query}&supplier_id={supplier_id}` provides article lookup for the Orders form, including supplier-specific defaults when available.
- Orders UI must use the canonical Orders list/detail contract and the new lookup endpoints.
- Receiving must be updated in the same phase to request `view=receiving` explicitly instead of relying on the old default detail behavior.

Delegation Plan
- Backend:
- Replace the temporary Orders routes with the final Orders-module API, keep explicit Receiving compatibility modes, and implement PDF generation plus supporting lookup endpoints.
- Frontend:
- Replace the Orders placeholders with real Orders pages and update the Receiving API client to use the explicit compatibility detail mode.
- Testing:
- Add dedicated Orders backend coverage and re-run Receiving regressions to confirm the compatibility path still works.

Acceptance Criteria
- ADMIN can list, create, edit, extend, remove lines from, and generate PDFs for orders.
- MANAGER can view Orders list/detail and generate PDFs, but cannot mutate data.
- Orders list shows OPEN orders first and CLOSED orders below them.
- `GET /api/v1/orders/{id}` no longer behaves as an implicit Receiving-only detail endpoint.
- Receiving remains functional via `GET /api/v1/orders?q={order_number}` and `GET /api/v1/orders/{id}?view=receiving`.
- Phase 8 handoff trail is complete and explicit across orchestration, backend, frontend, and testing.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first because the frontend depends on the final Orders contract and the explicit Receiving compatibility mode.

## Delegation Prompt - Backend Agent

You are the backend agent for Phase 8 of the WMS project.

Read before coding:
- `stoqio_docs/12_UI_ORDERS.md` — full
- `stoqio_docs/11_UI_RECEIVING.md` — API compatibility note and `view=receiving` detail mode
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 7
- `stoqio_docs/05_DATA_MODEL.md` § 3, § 13, § 14, § 15
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.3, § 3.6, § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-006`, `DEC-ORD-001`)
- `handoff/README.md`
- `handoff/phase-08-orders/orchestrator.md`

Goal
- Implement the full Orders backend for Phase 8 without inheriting the temporary Phase 7 Receiving-only contract as the final Orders contract.
- Preserve Receiving compatibility explicitly via the locked Phase 8 compatibility modes.

Non-Negotiable Contract Rules
- Default `GET /api/v1/orders` is the Orders list contract.
- `GET /api/v1/orders?q={order_number}` is a Receiving-compatibility lookup mode, not a generic list search.
- Default `GET /api/v1/orders/{id}` is full Orders detail with all lines.
- `GET /api/v1/orders/{id}?view=receiving` is the Receiving-compatibility detail mode.
- Do not leave `/api/v1/orders/{id}` in its old Phase 7 filtered-detail form.

Tasks
1. Replace `backend/app/api/orders/routes.py` with the full Orders-module route set:
   - `GET /api/v1/orders?page=1&per_page=50`
   - `GET /api/v1/orders?q={order_number}`
   - `GET /api/v1/orders/{id}`
   - `POST /api/v1/orders`
   - `PATCH /api/v1/orders/{id}`
   - `POST /api/v1/orders/{id}/lines`
   - `PATCH /api/v1/orders/{id}/lines/{line_id}`
   - `DELETE /api/v1/orders/{id}/lines/{line_id}`
   - `GET /api/v1/orders/{id}/pdf`
   - `GET /api/v1/orders/lookups/suppliers?q={query}`
   - `GET /api/v1/orders/lookups/articles?q={query}&supplier_id={supplier_id}`
2. Keep routes thin. Put business logic and PDF generation in a dedicated service layer (`backend/app/services/order_service.py` or equivalent).
3. Orders list:
   - Paginated response shape per `07_ARCHITECTURE.md`.
   - OPEN orders first, CLOSED below them.
   - Include `order_number`, supplier summary, created date, line count, total value, and status.
4. Receiving compatibility lookup:
   - `GET /api/v1/orders?q={order_number}` returns the exact-match single summary contract already documented for Receiving.
   - `404 ORDER_NOT_FOUND` if no exact match exists.
5. Order detail:
   - Default detail returns all lines, including CLOSED and REMOVED lines, with header totals and supplier info.
   - `view=receiving` returns only OPEN, non-REMOVED receiving-eligible lines and preserves the Receiving-specific fields already documented.
6. Create order:
   - Require at least one line.
   - Auto-generate `ORD-0001` style number when `order_number` is missing/blank.
   - Manual number is allowed but must remain unique.
   - Validate supplier exists and is active.
   - Validate line quantities are positive.
   - Validate `uom` matches the article base UOM.
   - Persist `supplier_article_code` and `unit_price` snapshot values on each line.
7. Edit order header:
   - Allow only while order is OPEN.
   - Editable fields: `supplier_confirmation_number`, `note`.
8. Add/edit/remove lines:
   - Only OPEN orders can be changed.
   - Only OPEN lines can be edited or removed.
   - Remove means `status = REMOVED`, not hard delete.
   - Recalculate line and order status after every mutation.
   - Auto-close order when all active lines are CLOSED or REMOVED.
9. Lookup endpoints:
   - Supplier lookup searches active suppliers by name or internal code.
   - Article lookup searches active articles by article number or description.
   - If `supplier_id` is present and an `ArticleSupplier` record exists, return `supplier_article_code` and `last_price`.
10. PDF generation:
   - Use `reportlab` or `weasyprint`.
   - Return `application/pdf`.
   - Include the content required by `12_UI_ORDERS.md` § 8.
   - No company branding.
11. RBAC:
   - ADMIN full access.
   - MANAGER GET-only access for Orders list/detail/PDF and lookups needed by read-only detail rendering.
12. Keep `backend/tests/test_receiving.py` passing by preserving the explicit compatibility modes documented for Receiving.

Verification
- Add/update backend tests as needed.
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_orders.py -q`
  - `backend/venv/bin/pytest backend/tests/test_receiving.py -q`
  - `backend/venv/bin/pytest backend/tests -q`

Handoff Requirements
- Append your work log to `handoff/phase-08-orders/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover another contract gap with cross-agent impact, add it to `handoff/decisions/decision-log.md` before finalizing the backend work.

Done Criteria
- The Orders backend contract is fully implemented.
- Receiving compatibility is explicit and no longer implicit in the default detail route.
- PDF generation works.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Phase 8 of the WMS project.

Read before coding:
- `stoqio_docs/12_UI_ORDERS.md` — full
- `stoqio_docs/11_UI_RECEIVING.md` — compatibility detail mode
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/decisions/decision-log.md` (`DEC-BE-006`, `DEC-ORD-001`)
- `handoff/README.md`
- `handoff/phase-08-orders/orchestrator.md`
- Backend handoff for Phase 8 after the backend agent finishes

Goal
- Implement the Orders UI for ADMIN and MANAGER without relying on the temporary Phase 7 Receiving contract.
- Update the Receiving client to use the explicit compatibility detail mode introduced for Phase 8.

Non-Negotiable Contract Rules
- Orders list page must use the canonical paginated Orders list contract.
- Orders detail page must use the canonical full Orders detail contract.
- Receiving compatibility must be explicit; do not keep calling the default detail route as if it were Receiving-only.
- MANAGER is read-only everywhere except PDF download.

Tasks
1. Replace the Orders placeholders in `frontend/src/routes.tsx` with real lazy-loaded pages:
   - `frontend/src/pages/orders/OrdersPage.tsx`
   - `frontend/src/pages/orders/OrderDetailPage.tsx`
2. Replace the current minimal `frontend/src/api/orders.ts` with a Phase 8 API surface that includes:
   - orders list
   - order detail
   - create order
   - edit header
   - add line
   - edit line
   - remove line
   - generate/download PDF
   - supplier lookup
   - article lookup
   - Receiving compatibility helpers:
     - exact-match lookup by `q`
     - detail fetch using `view=receiving`
3. Orders list page:
   - OPEN orders at the top, visually prominent.
   - CLOSED orders below, visually muted.
   - Row click navigates to detail.
   - Empty state: `No orders found.`
   - ADMIN sees `New Order`.
   - MANAGER does not.
4. New order flow:
   - Header fields: order number, supplier, supplier confirmation number, note.
   - Dynamic line rows before submit.
   - Article lookup by article number or description.
   - Supplier article code auto-populated when available, editable.
   - UOM display-only.
   - Submit button label: `Create Order`.
   - Success toast: `Order created.`
5. Order detail page:
   - Header section with total value and status.
   - Lines table with all columns from the Orders spec.
   - ADMIN can edit header, add line, edit open lines, remove open lines, generate PDF.
   - MANAGER sees no mutation actions, but PDF remains visible.
6. Receiving compatibility update:
   - Update the Receiving client path so order detail fetches use the explicit compatibility mode (`view=receiving`).
   - Do not visually regress `/receiving`.
7. Apply global UI rules:
   - Croatian client-rendered copy by default.
   - Inline validation for form errors.
   - Toasts for success/server errors.
   - one automatic retry on network/server failure
   - full-page error state after repeated failure
   - loading indicators for async work

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/phase-08-orders/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record any Receiving compatibility UI/API updates explicitly in your handoff entry.

Done Criteria
- Orders list/detail/create/edit/remove/PDF UI is implemented.
- MANAGER read-only behavior is correct.
- Receiving now calls the explicit compatibility detail mode.
- Frontend verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Phase 8 of the WMS project.

Read before coding:
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-006`, `DEC-ORD-001`)
- `handoff/README.md`
- `handoff/phase-08-orders/orchestrator.md`
- Backend and frontend Phase 8 handoff entries after those agents finish

Goal
- Add backend Orders integration coverage and verify that the explicit Receiving compatibility path still works after the Orders API contract expansion.

Tasks
1. Write `backend/tests/test_orders.py` covering at minimum:
   - Create order -> 201, auto-generated order number.
   - Create order with manual number -> 201.
   - Duplicate order number -> 409.
   - Orders list -> 200, OPEN orders first.
   - Order detail -> 200, full line set returned.
   - Add line to open order -> 200.
   - Edit line -> 200.
   - Remove line -> 200, line status becomes REMOVED.
   - Remove last active line -> order auto-closes.
   - Edit closed order -> 400 or 403.
   - MANAGER GET detail -> 200.
   - MANAGER POST/PATCH/DELETE -> 403.
   - PDF endpoint -> 200, `application/pdf`.
   - Supplier lookup -> 200.
   - Article lookup -> 200.
2. Re-run Receiving compatibility coverage:
   - `GET /api/v1/orders?q={order_number}` still returns the expected exact-match summary.
   - `GET /api/v1/orders/{id}?view=receiving` still returns Receiving-oriented filtered detail.
   - Existing `backend/tests/test_receiving.py` remains green.
3. Re-run the full backend suite after Orders tests are added.
4. If frontend verification was not fully covered by the frontend agent, repeat:
   - `cd frontend && npm run lint -- --max-warnings=0`
   - `cd frontend && npm run build`

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_orders.py -q`
  - `backend/venv/bin/pytest backend/tests/test_receiving.py -q`
  - `backend/venv/bin/pytest backend/tests -q`

Handoff Requirements
- Append your work log to `handoff/phase-08-orders/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Call out any mismatch between the canonical Orders contract and the explicit Receiving compatibility contract immediately.

Done Criteria
- Orders backend coverage exists.
- Receiving compatibility regressions are checked.
- Verification is recorded in handoff.

## Validation Note - 2026-03-13 14:15:56 CET

Status
- In review; not closed yet.

Accepted Work
- Backend replaced the Phase 7 Receiving-only scaffold with the canonical Orders list/detail contract, explicit Receiving compatibility modes, lookup endpoints, mutation routes, and PDF generation.
- Frontend replaced `/orders` and `/orders/:id` placeholders with real Orders pages and updated the Receiving client to call `GET /api/v1/orders/{id}?view=receiving` explicitly.
- Testing added dedicated Orders backend coverage, re-ran Receiving compatibility coverage, and re-ran the full backend suite.
- Cross-agent docs were updated for the locked Phase 8 contract and `DEC-ORD-002` mutation response shape.

Rejected / Missing Items
- `POST /api/v1/orders/{id}/lines` currently returns `201`, but the delegated testing contract required `200`. The backend tests were updated to assert `201` instead of flagging the mismatch.
- Editing a closed order currently returns `409 ORDER_CLOSED`, but the delegated testing contract required `400` or `403`. The backend tests were updated to assert `409` instead of flagging the mismatch.
- Orders client-rendered copy is still mixed-language in `frontend/src/pages/orders/OrdersPage.tsx` (`New Order`, `Create Order`, `No orders found.`, `Order created.`), which does not satisfy the Croatian UI default required by `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4 and the Phase 8 frontend prompt.

Verification
- `backend/venv/bin/pytest backend/tests/test_orders.py -q` -> `8 passed, 10 warnings`
- `backend/venv/bin/pytest backend/tests/test_receiving.py -q` -> `14 passed, 16 warnings`
- `backend/venv/bin/pytest backend/tests -q` -> `115 passed, 128 warnings`
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass

Next Action
- Run a short Phase 8 follow-up lane for backend, frontend, and testing to close the three remaining contract/spec mismatches above, then append a final closeout note here.

## Validation Note - 2026-03-13 14:22:52 CET

Status
- Closed.

Accepted Work
- Orchestrator applied the final Phase 8 corrective pass directly in runtime code, tests, and docs to close the three review findings from the previous validation note.
- Backend Orders contract now matches the delegated Phase 8 semantics:
  - `POST /api/v1/orders/{id}/lines` returns `200`.
  - closed-order mutations return `400 ORDER_CLOSED`.
- Orders frontend client-rendered copy is now aligned with the Croatian UI default for the previously flagged create/list strings.
- `DEC-ORD-003` records the final locked semantics so later agents do not reintroduce the rejected behavior.

Files Changed By Orchestrator
- `backend/app/api/orders/routes.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_orders.py`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-08-orders/orchestrator.md`

Verification
- `backend/venv/bin/pytest backend/tests/test_orders.py -q` -> `8 passed, 10 warnings`
- `backend/venv/bin/pytest backend/tests/test_receiving.py -q` -> `14 passed, 16 warnings`
- `backend/venv/bin/pytest backend/tests -q` -> `115 passed, 128 warnings`
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass

Residual Notes
- Remaining warnings are unchanged JWT key-length warnings already present elsewhere in the repo; no new Phase 8 blocker remains.

Next Action
- Treat Phase 8 as complete on the current codebase baseline.

## Validation Note - 2026-03-13 14:28:39 CET

Status
- Closed; post-closeout backend/dev baseline cleanup applied.

Accepted Work
- Orchestrator removed the remaining short-JWT-secret baseline that was generating PyJWT `InsecureKeyLengthWarning` during backend tests and local development.
- Test config now uses a deterministic 32+ character secret.
- Development default and `backend/.env.example` now use a 32+ character placeholder secret, while production still rejects that placeholder as weak/default.
- The local `backend/.env` on this workspace was updated to match the stronger dev placeholder so manual local runs use the same baseline immediately.
- `DEC-BE-009` records this as the current backend/dev expectation for future agents.

Files Changed By Orchestrator
- `backend/tests/conftest.py`
- `backend/tests/test_phase2_models.py`
- `backend/app/config.py`
- `backend/.env.example`
- `backend/.env` (local workspace file; not repo-tracked)
- `handoff/decisions/decision-log.md`
- `handoff/phase-08-orders/orchestrator.md`

Verification
- `backend/venv/bin/pytest backend/tests -q` -> `115 passed`

Residual Notes
- Historical handoff entries from earlier phases still mention the old short `test-secret` warning as a point-in-time fact. Current baseline is defined by `DEC-BE-009` and this validation note.

Next Action
- Keep using 32+ character JWT secrets in dev/test/prod paths; treat short HS256 secrets as an avoidable regression.
