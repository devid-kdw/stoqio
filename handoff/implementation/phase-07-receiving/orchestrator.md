## Phase Summary

Phase
- Phase 7 - Receiving

Objective
- Deliver the Receiving module end to end:
- backend service logic for stock receipts
- backend API routes for receiving submission and history
- minimal order lookup/detail API support required by the Receiving UI
- frontend Receiving screen for order-linked and ad-hoc receipts
- backend automated tests covering receiving rules and regressions

Source Docs
- `stoqio_docs/11_UI_RECEIVING.md` — full, especially § 3, § 4, § 5, § 6, § 7, § 8, § 9, § 10, § 11
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3.1, § 3.2, § 3.3
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 6.1, § 6.2
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 7.1, § 7.3, § 7.4
- `stoqio_docs/05_DATA_MODEL.md` § 7, § 8, § 13, § 14, § 15, § 16, § 23
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.3, § 3.5, § 3.6, § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`

Current Repo Reality
- `backend/app/api/receiving/` exists only as package scaffolding. No receiving service or routes are implemented yet.
- `backend/app/api/orders/` also exists only as package scaffolding. The Receiving UI spec depends on:
  - `GET /api/v1/orders?q={order_number}`
  - `GET /api/v1/orders/{id}`
- Therefore Phase 7 backend scope must include the minimal read-only order lookup/detail endpoints required by `11_UI_RECEIVING.md` § 9. This is a dependency of the Receiving module, not a full Orders module implementation.
- Frontend routing already includes `/receiving` as an ADMIN-only placeholder route in `frontend/src/routes.tsx`.

Delegation Plan
- Backend:
- Implement receiving service logic, receiving routes, receiving history, and the minimal order lookup/detail routes required by the Receiving UI.
- Frontend:
- Replace the `/receiving` placeholder with the full Receiving screen, using the exact API contracts delivered by the backend.
- Testing:
- Add backend receiving integration coverage and re-run the relevant regression suite.

Acceptance Criteria
- ADMIN can open `/receiving` and complete both standard order-linked receipts and ad-hoc receipts.
- Receiving increases stock only and never writes to surplus.
- Existing batch + different expiry date returns `409 BATCH_EXPIRY_MISMATCH`.
- Receiving history is available and ordered newest first.
- Linked receipts update `OrderLine.received_qty`, auto-close fulfilled lines, and auto-close the order when all active lines are closed.
- UI follows the global retry, loading, error, toast, inline-validation, and empty-state rules from `08_SETUP_AND_GLOBALS.md` § 4.
- Phase 7 handoff trail is complete across orchestrator, backend, frontend, and testing files.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first, because the frontend depends on new backend contracts and the minimal Orders lookup/detail endpoints.

## Delegation Prompt - Backend Agent

You are the backend agent for Phase 7 of the WMS project.

Read before coding:
- `stoqio_docs/11_UI_RECEIVING.md` — full, especially § 3, § 4, § 5, § 6, § 7, § 8, § 9, § 10, § 11
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3.1, § 3.2, § 3.3
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 6.1, § 6.2
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 7.1, § 7.3, § 7.4
- `stoqio_docs/05_DATA_MODEL.md` § 7 (Batch), § 8 (Stock), § 13 (Order), § 14 (OrderLine), § 15 (Receiving), § 16 (Transaction), § 23 (Location)
- `stoqio_docs/07_ARCHITECTURE.md` § 2 (API conventions)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.3, § 3.5, § 3.6, § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/implementation/phase-07-receiving/orchestrator.md`

Goal
- Implement the Receiving backend completely for Phase 7.
- This includes the receiving service layer, receiving API routes, receiving history, and the minimal order lookup/detail endpoints that the Receiving UI requires.
- Do not broaden scope into the full Orders module beyond the read-only endpoints needed by `11_UI_RECEIVING.md` § 9.

Tasks
1. Implement `backend/app/services/receiving_service.py`.
   - Increase stock only; never create or modify surplus.
   - Use the v1 single-location assumption already used elsewhere in the codebase.
   - Apply weighted average price exactly as:
     - `(current_stock × current_avg + received_qty × unit_price) / (current_stock + received_qty)`
   - If `unit_price` is missing on the receipt line:
     - for order-linked receipts, use `OrderLine.unit_price`
     - for ad-hoc receipts, allow `unit_price` to remain `NULL` and preserve the current stock average if stock already exists; if no stock exists yet, keep `average_price` as `0` or `NULL` consistently with the existing model usage and log the chosen behavior in handoff
   - Batch handling:
     - if the article has `has_batch = true`, require `batch_code` and `expiry_date`
     - validate `batch_code` with the documented regex
     - if the batch does not exist for the article, create it
     - if the batch already exists for the article and the expiry date matches, reuse it
     - if the batch already exists for the article and the expiry date differs, return `409 BATCH_EXPIRY_MISMATCH`
   - Create one `Receiving` record per submitted line that is actually received.
   - Create one `Transaction` record per stored receipt line with:
     - `tx_type = STOCK_RECEIPT`
     - positive quantity
     - `reference_type = "receiving"`
     - `reference_id = <receiving.id>`
     - `delivery_note_number`
     - `order_number` when linked to an order line
   - If linked to `order_line_id`:
     - validate the line exists
     - validate it is not `REMOVED`
     - validate it belongs to an `OPEN` order
     - increment `OrderLine.received_qty`
     - auto-close the line when cumulative `received_qty >= ordered_qty`
     - auto-close the order when all active lines (`status != REMOVED`) are `CLOSED`
2. Implement `backend/app/api/receiving/routes.py`.
   - `POST /api/v1/receiving`
   - `GET /api/v1/receiving?page=1&per_page=50`
   - ADMIN only.
   - Request and response shapes must follow `stoqio_docs/11_UI_RECEIVING.md` § 10.
   - History must return newest first and use the project-standard paginated list shape from `07_ARCHITECTURE.md` § 2.
3. Implement the minimal order lookup/detail endpoints required by the Receiving UI.
   - `GET /api/v1/orders?q={order_number}`
   - `GET /api/v1/orders/{id}`
   - ADMIN only.
   - Scope these endpoints strictly to what `11_UI_RECEIVING.md` needs:
     - search by order number
     - return enough order and open-line detail for the receiving form
     - include article metadata needed by the frontend per line (`article_id`, `article_no`, `description`, `has_batch`, ordered qty, received qty, remaining/open state, UOM, unit price if present, delivery date if present)
   - Do not implement order create/edit/delete flows in this phase.
4. Register the new receiving and order blueprints in `backend/app/api/__init__.py`.
5. Keep all endpoints ADMIN-only per `03_RBAC.md`.
6. Follow the standard API error shape from `07_ARCHITECTURE.md` § 2:
   - `{"error": "...", "message": "...", "details": {}}`

Required Validation Rules
- `delivery_note_number` is required and max 100 characters.
- `note` is required for ad-hoc receipts and max 1000 characters.
- At least one line must actually be received; “all skipped” is a validation error.
- Receipt quantities must be positive.
- `uom` must match the authoritative source:
  - linked receipt: `OrderLine.uom`
  - ad-hoc receipt: `Article.base_uom` resolved to the UOM code string used by the existing APIs
- For batch-tracked articles, `batch_code` and `expiry_date` are required.
- For non-batch articles, ignore any incoming batch fields and persist `NULL batch_id`.
- Order-linked receipts must reject:
  - missing or invalid `order_line_id`
  - closed orders
  - removed lines
- Preserve Phase 7 scope: do not add speculative inventory conversion logic or barcode-printing logic.

Implementation Notes
- Reuse the existing project patterns from:
  - `backend/app/api/drafts/routes.py`
  - `backend/app/api/approvals/routes.py`
  - `backend/app/services/approval_service.py`
- Be explicit about Decimal handling so quantity and price math stays deterministic.
- If you need to choose between route thinness and correctness, keep routes thin and put business logic in the service layer.

Verification
- Add or update backend tests as needed while implementing.
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_receiving.py -q`
  - `backend/venv/bin/pytest backend/tests -q`
- If you add new order lookup/detail coverage in a separate test file, run that file explicitly too and record it.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-07-receiving/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record all files changed, commands run, tests run, open issues, and assumptions.
- If you discover a spec gap or need to lock an implementation choice with cross-agent impact, add it to `handoff/decisions/decision-log.md` and reference it.

Done Criteria
- Receiving service and routes are implemented.
- Minimal order lookup/detail routes required by the Receiving UI are implemented.
- Receiving history works.
- Stock, batch, transaction, order-line, and order status updates follow the documented rules.
- Backend verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Phase 7 of the WMS project.

Read before coding:
- `stoqio_docs/11_UI_RECEIVING.md` — full, especially § 2, § 3, § 4, § 5, § 6, § 7, § 8, § 9, § 10, § 11
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.3, § 3.5, § 3.6, § 4, § 5
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/decisions/decision-log.md` (`DEC-BE-006`, `DEC-BE-007`)
- `handoff/README.md`
- `handoff/implementation/phase-07-receiving/orchestrator.md`
- Backend handoff for Phase 7 after the backend agent finishes

Goal
- Implement the Receiving UI exactly for the Phase 7 scope:
  - order-linked receipt flow
  - ad-hoc receipt flow
  - receipt history
- Use the backend API contracts delivered in Phase 7.
- Do not broaden scope into the full Orders module UI.

Locked Backend Contracts
- Do not treat `GET /api/v1/orders?q={order_number}` as a list search endpoint. It returns a single exact-match summary object or `404 ORDER_NOT_FOUND`.
- Use `GET /api/v1/orders/{id}` to fetch the form detail. It returns only OPEN, non-removed receiving-eligible lines.
- Use the exact response shapes now documented in `stoqio_docs/11_UI_RECEIVING.md` § 10.
- `DEC-BE-007` is backend-only valuation behavior. The frontend must not invent a fallback `unit_price` for ad-hoc receipts when the user leaves pricing blank.

Tasks
1. Replace the `/receiving` placeholder with a real page at `frontend/src/pages/receiving/ReceivingPage.tsx`.
2. Add any new frontend API modules needed for:
   - order search
   - order detail
   - submit receiving
   - receiving history
3. Implement the screen from `11_UI_RECEIVING.md` exactly:
   - Two tabs: `New Receipt` and `History`
   - Within `New Receipt`, support both:
     - standard order-linked receipt
     - ad-hoc receipt
   - A separate tab, sub-tab, or clearly separated mode switch for ad-hoc receipt is acceptable as long as the UX is explicit and faithful to the spec
4. Order-linked receipt flow:
  - order search field
  - inline “Order not found.” handling
  - show open lines on successful match
  - on successful `GET /api/v1/orders?q=...`, store the returned `id` and then fetch `GET /api/v1/orders/{id}` for line detail
  - per line:
    - received quantity input
    - display-only UOM
    - batch code and expiry inputs when `has_batch = true`
    - skip line checkbox
   - receipt header fields:
     - delivery note number
     - note (optional for linked receipts)
5. Ad-hoc receipt flow:
   - article lookup using the existing article lookup API pattern already used by Draft Entry
   - quantity input
   - UOM display
   - batch code and expiry inputs when `has_batch = true`
   - delivery note number
   - note required
6. History tab:
   - fetch from `GET /api/v1/receiving?page=1&per_page=50`
   - render newest first
   - read-only rows showing the fields from `11_UI_RECEIVING.md` § 8
7. Apply global UI rules from `08_SETUP_AND_GLOBALS.md` § 4:
   - inline validation errors for form issues
   - success/error toasts
   - one automatic retry on network/server failure
   - full-page error state after repeated failure
   - loading indicators on async work
   - human-readable empty states
8. Keep the route ADMIN-only and preserve the existing app shell/RBAC patterns.

Required UI Behavior
- Submit button label must be `Confirm Receipt`.
- Disable the submit action and show a spinner while submission is in flight.
- On success:
  - show success toast `Receipt recorded.`
  - clear the relevant form state
  - refresh history
  - refresh the current order detail if the receipt was order-linked so the remaining open lines are accurate
- On `409 BATCH_EXPIRY_MISMATCH`:
  - show the error inline on the affected line, not only as a toast
- All-skipped submission must be blocked with inline validation.
- Order already closed must show a warning and prevent receipt.
- Respect UOM display rules using the same project conventions already present in Draft Entry.

Implementation Notes
- Reuse the project’s existing patterns from:
  - `frontend/src/pages/drafts/DraftEntryPage.tsx`
  - `frontend/src/pages/approvals/ApprovalsPage.tsx`
  - `frontend/src/api/drafts.ts`
  - `frontend/src/api/approvals.ts`
- Do not infer additional order fields beyond the documented Phase 7 Receiving contracts. If backend and docs differ, report the mismatch in handoff instead of inventing a client-side interpretation.
- Keep copy in Croatian for normal UI text and in English for backend-driven error messages, consistent with `08_SETUP_AND_GLOBALS.md` § 4.1.
- Keep the page tablet/desktop oriented and consistent with the existing app shell.

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Record any bundle warnings, but do not treat the existing large-chunk warning as a new functional blocker by itself.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-07-receiving/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests/build verification, open issues, and assumptions.
- If you discover a cross-agent spec gap, add it to `handoff/decisions/decision-log.md` and reference it.

Done Criteria
- `/receiving` is a real ADMIN-only page.
- Order-linked receipt, ad-hoc receipt, and receiving history are implemented.
- Global UI rules are applied consistently.
- Frontend verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Phase 7 of the WMS project.

Read before testing:
- `stoqio_docs/11_UI_RECEIVING.md` — full, especially § 5, § 6, § 7, § 8, § 10, § 11
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3.3, § 6.1, § 6.2, § 7.1, § 7.3, § 7.4
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.3, § 3.5, § 3.6, § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/implementation/phase-07-receiving/orchestrator.md`
- Backend and frontend Phase 7 handoff entries after those agents finish

Goal
- Verify the Phase 7 Receiving implementation with backend automated coverage as the primary gate.
- Focus on behavioural correctness, regressions, and contract compliance.
- Do not silently fix product code unless explicitly asked by the orchestrator; report failures precisely first.

Tasks
1. Write or finish `backend/tests/test_receiving.py` with coverage for at least these cases:
   - receive against order line → stock increases, `OrderLine.received_qty` updates
   - receive with batch → batch created, stock increases
   - receive with existing batch and same expiry → stock increases
   - receive with existing batch and different expiry → `409 BATCH_EXPIRY_MISMATCH`
   - ad-hoc receive without note → `400`
   - ad-hoc receive with note → `201`
   - all lines received → order auto-closed
   - delivery note missing → `400`
   - weighted average price calculated correctly
   - `STOCK_RECEIPT` transaction created
2. Add coverage for the minimal order lookup/detail endpoints introduced for Receiving if the backend agent did not already cover them sufficiently.
3. Run the relevant backend tests and the full backend suite.
4. Run frontend verification commands:
   - `cd frontend && npm run lint -- --max-warnings=0`
   - `cd frontend && npm run build`
5. Record exact outcomes and residual risks.

Verification Requirements
- Minimum command set:
  - `backend/venv/bin/pytest backend/tests/test_receiving.py -q`
  - `backend/venv/bin/pytest backend/tests -q`
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- If you discover a failing scenario not listed above but clearly required by the docs, record it as a finding with file and behavior detail.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-07-receiving/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record commands run, tests added/updated, exact pass/fail results, blockers, and residual risks.

Done Criteria
- Receiving backend coverage exists and exercises the documented rules.
- Full verification results are recorded clearly.
- Any failure is actionable and attributed to backend, frontend, integration, or environment.

## Orchestrator Closeout - 2026-03-13 10:36 CET

Validation Notes
- Backend implementation was reviewed against the Phase 7 docs and the delivered handoff/contracts.
- Phase 7 docs were updated during review to capture the minimal Receiving-only Orders API contract (`DEC-BE-006`) and the ad-hoc `average_price = 0.0000` fallback decision (`DEC-BE-007`).
- Receiving frontend received a final orchestrator follow-up to align client-side validation and connection-state copy with the Croatian UI-copy rule while preserving English backend-driven errors.
- Final verification on the current workspace:
  - `backend/venv/bin/pytest backend/tests -q` -> `106 passed`
  - `cd frontend && npm run lint -- --max-warnings=0` -> pass
  - `cd frontend && npm run build` -> pass
- Remaining warnings are non-blocking:
  - backend JWT test-fixture warning for short secret
  - existing Vite large-chunk build warning

Accepted Outcome
- Phase 7 Receiving is accepted on the current codebase baseline.
- Backend API, frontend UI, docs, decision log, and handoff trail are now aligned.

Residual Notes
- Manual browser smoke testing is still recommended before release/deployment, especially linked receipt success/error flows and history refresh behavior.
- If the app is served from Flask static assets, sync the latest frontend build into the backend static output before browser verification.

Next Action
- Treat Phase 7 as closed unless manual browser smoke testing reveals a runtime integration issue.
