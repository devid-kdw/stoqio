# WMS — Implementation Plan & Orchestrator Prompts

**Version**: v1
**Purpose**: Step-by-step implementation guide. Each phase contains a ready-to-use prompt for the orchestrator agent. Copy the prompt, paste it to the orchestrator, wait for completion, then move to the next phase.

---

## How to Use This Document

1. Open the phase you are currently working on.
2. Copy the **Orchestrator Prompt** exactly as written.
3. Paste it to the orchestrator agent.
4. Wait for the orchestrator to delegate to backend / frontend / testing agents and confirm completion.
5. Move to the next phase.

> **Important**: Do not skip phases. Each phase depends on the previous one being complete and stable.

---

## Phase 1 — Project Setup

**Goal**: Create the full monorepo folder structure, configure Flask application factory, connect PostgreSQL, set up Alembic migrations, scaffold React + Vite frontend, configure Vite proxy, and create the `.env.example` file.

**No database models yet. No routes yet. Just the skeleton.**

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS (Warehouse Management System) project. Your job is to delegate tasks to the backend agent and frontend agent, verify their output, and confirm when the phase is complete.

## Goal
Set up the complete project skeleton. No models, no routes, no UI pages yet — only the project structure, configuration, and tooling.

## Reference Documents
Read the following sections before delegating:
- 07_ARCHITECTURE.md § 1 (Folder structure) — full folder tree to create
- 07_ARCHITECTURE.md § 6 (Development workflow) — local setup commands, Flask + Vite dev server
- 07_ARCHITECTURE.md § 5 (Local server deployment) — .env structure, systemd (scaffold only, not deploy yet)

## Backend Agent Tasks
1. Create the monorepo folder structure exactly as specified in 07_ARCHITECTURE.md § 1.
2. Implement `backend/app/__init__.py` with Flask application factory (`create_app()`).
3. Implement `backend/app/extensions.py` — db (SQLAlchemy), jwt (Flask-JWT-Extended), migrate (Alembic) instances.
4. Implement `backend/app/config.py` — Development and Production config classes. Read DATABASE_URL and JWT_SECRET_KEY from environment variables. In Production, refuse to start if JWT_SECRET_KEY is default or weak.
5. Create `backend/requirements.txt` with all required packages: Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-Migrate (Alembic), psycopg2-binary, python-dotenv, gunicorn.
6. Create `backend/.env.example` with placeholders: FLASK_ENV, DATABASE_URL, JWT_SECRET_KEY.
7. Create `backend/run.py` as the development entry point.
8. Create `backend/tests/conftest.py` scaffold (empty fixtures, test DB config placeholder).

## Frontend Agent Tasks
1. Scaffold a new React + TypeScript project using Vite inside `frontend/`.
2. Install dependencies: react-router-dom v6, @tanstack/react-query, zustand, axios, i18next, react-i18next, @mantine/core, @mantine/hooks.
3. Configure Vite proxy: all `/api` requests proxy to `http://127.0.0.1:5000`.
4. Create `frontend/src/main.tsx` and `frontend/src/App.tsx` (minimal, just renders "WMS" for now).
5. Create `frontend/src/store/authStore.ts` — Zustand store scaffold with fields: user, accessToken, refreshToken, isAuthenticated. All null/false initially.
6. Create `frontend/src/i18n/index.ts` and locale files: `hr.json`, `en.json`, `de.json`, `hu.json` (all empty objects for now).
7. Create `frontend/src/api/client.ts` — axios instance pointed at `/api/v1/`. Add request interceptor that attaches Authorization header from Zustand store. Add response interceptor scaffold (401 handling — empty for now, will be filled in Phase 3).

## Verification
- `cd backend && flask run` starts without errors.
- `cd frontend && npm run dev` starts without errors.
- Vite dev server proxies `/api` to Flask correctly (test with a simple GET /api/v1/health endpoint — backend agent should add this).
```

---

## Phase 2 — Database Models

**Goal**: Implement all SQLAlchemy models and create the initial Alembic migration. No routes, no business logic yet.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to the backend agent only for this phase.

## Goal
Implement all SQLAlchemy database models and create the initial Alembic migration that creates all tables.

## Reference Documents
Read the following sections before delegating:
- 05_DATA_MODEL.md — full — all 26 entities with all fields and types
- 07_ARCHITECTURE.md § 1 (models/ folder structure) — one file per entity
- 02_DOMAIN_KNOWLEDGE.md § 1.3 (Audit trail), § 1.4 (Sign convention) — for Transaction model
- 02_DOMAIN_KNOWLEDGE.md § 3 (Batches) — batch_code validation, FEFO note
- 05_DATA_MODEL.md "Napomena o batch_id" — batch_id is nullable on ALL entities

## Backend Agent Tasks
1. Implement one SQLAlchemy model file per entity in `backend/app/models/`, exactly matching 05_DATA_MODEL.md.
   - All 26 entities: Supplier, Article, ArticleSupplier, ArticleAlias, Category, UomCatalog, Batch, Stock, Surplus, Draft, DraftGroup, ApprovalAction, Order, OrderLine, Receiving, Transaction, InventoryCount, InventoryCountLine, Employee, PersonalIssuance, AnnualQuota, User, Location, MissingArticleReport, SystemConfig, RoleDisplayName.
2. Apply these constraints:
   - `stock.quantity >= 0` — CHECK constraint (never negative).
   - `batch_id` is nullable on: Stock, Surplus, Draft, Transaction, Receiving, InventoryCountLine, PersonalIssuance.
   - `client_event_id` on Draft is UNIQUE.
   - `article_no` on Article is UNIQUE, stored uppercase.
   - `username` on User is UNIQUE.
   - `employee_id` on Employee is UNIQUE.
   - `role` on RoleDisplayName is UNIQUE.
   - `key` on SystemConfig is UNIQUE.
3. Create `backend/app/models/__init__.py` that imports all models so Alembic can detect them.
4. Run `alembic revision --autogenerate -m "initial"` and verify the generated migration covers all tables.
5. Run `alembic upgrade head` and confirm all tables are created without errors.
6. In `backend/migrations/env.py`, guard `fileConfig(config.config_file_name)` with a defensive `try/except` and only call it when the config file exists. This avoids observed Python 3.9/macOS `KeyError: 'formatters'` failures during `flask db upgrade`.

## Verification
- `alembic upgrade head` completes without errors.
- All 26 tables exist in the database.
- `stock.quantity` CHECK constraint is present.
```

---

## Phase 3 — Authentication

**Goal**: Implement login, token refresh, logout on the backend. Implement login page, auth store, axios interceptor, and protected routes on the frontend.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the full authentication flow: login, access token, refresh token, logout, protected routes.

## Reference Documents
- 07_ARCHITECTURE.md § 3 (Auth flow) — full section: token durations per role, storage, refresh flow, endpoints
- 07_ARCHITECTURE.md § 4 (Frontend routing) — ProtectedRoute, home route per role, RBAC routing rules
- 05_DATA_MODEL.md § 22 (User) — user fields, role enum, password_hash
- 08_SETUP_AND_GLOBALS.md § 1.1 (Seed data — Admin user) — seed admin/admin123
- 08_SETUP_AND_GLOBALS.md § 3.4 (Password validation) — min 4 characters
- 02_DOMAIN_KNOWLEDGE.md § 13 (Security) — pbkdf2:sha256, rate limiting on auth endpoints
- 03_RBAC.md — role enum values, home route per role

## Backend Agent Tasks
1. Implement `backend/app/api/auth/routes.py`:
   - POST `/api/v1/auth/login` — validate username/password, return access_token + refresh_token. Token durations: OPERATOR refresh = 30 days, all others = 8 hours. Access token always 15 minutes.
   - POST `/api/v1/auth/refresh` — accept refresh token, return new access token.
   - POST `/api/v1/auth/logout` — invalidate refresh token (server-side blacklist using a simple DB table or in-memory set).
2. Implement `backend/app/utils/auth.py` — JWT decorators and role-check helpers (`@require_role(...)`, `@require_any_role(...)`).
3. Add rate limiting on `/api/v1/auth/login` (max 10 requests/minute per IP).
4. Seed the admin user: username=`admin`, password=`admin123`, role=`ADMIN`, is_active=`true`.
5. Seed UOM catalog and article categories as defined in 08_SETUP_AND_GLOBALS.md § 1.2 and § 1.3 (including label_en for all categories).
6. Seed SystemConfig records as defined in 08_SETUP_AND_GLOBALS.md § 1.4.
7. Seed RoleDisplayName records as defined in 08_SETUP_AND_GLOBALS.md § 1.5.
8. Error format must follow 07_ARCHITECTURE.md § 2 — `{"error": "...", "message": "...", "details": {}}`.

## Frontend Agent Tasks
1. Implement `frontend/src/pages/auth/LoginPage.tsx` — username + password form, calls POST `/api/v1/auth/login`, stores tokens in Zustand authStore, redirects to home route based on role.
2. Complete `frontend/src/store/authStore.ts` — add login(), logout(), setAccessToken() actions.
3. Complete `frontend/src/api/client.ts` — fill in the 401 interceptor: on 401, call POST `/api/v1/auth/refresh`, retry original request with new token. If refresh fails, call logout() and redirect to `/login`.
4. Implement `frontend/src/api/auth.ts` — login, refresh, logout API functions.
5. Implement `ProtectedRoute` component in `frontend/src/components/layout/` — checks isAuthenticated from Zustand, redirects to `/login` if not. Checks role for route access, redirects to home route if wrong role.
6. Implement `frontend/src/routes.tsx` — full route config as specified in 07_ARCHITECTURE.md § 4. All protected routes wrapped with ProtectedRoute. Home redirect from `/` based on role.
7. Implement `frontend/src/components/layout/AppShell.tsx` and `Sidebar.tsx` — sidebar shows only modules accessible to current role, as defined in 03_RBAC.md "Prozor svake role".

## Testing Agent Tasks
1. Write `backend/tests/test_auth.py`:
   - POST /login with valid credentials → 200, returns access_token + refresh_token.
   - POST /login with invalid password → 401.
   - POST /login with inactive user → 401.
   - POST /refresh with valid refresh token → 200, returns new access_token.
   - POST /refresh with expired/invalid token → 401.
   - POST /logout → 200, refresh token invalidated.
   - Protected endpoint without token → 401.
   - Protected endpoint with wrong role → 403.

## Verification
- Admin can log in at `/login` and is redirected to `/approvals`.
- Refresh token flow works transparently (test by expiring access token manually).
- Sidebar shows only the correct modules per role.
```

---

## Phase 4 — First-Run Setup

**Goal**: Detect missing Location record on first login and redirect admin to `/setup`. After setup, normal flow resumes.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent and frontend agent.

## Goal
Implement the first-run setup flow: detect absence of Location record, redirect to /setup, create Location, then proceed normally.

## Reference Documents
- 08_SETUP_AND_GLOBALS.md § 2 (First-run setup flow) — full section
- 05_DATA_MODEL.md § 23 (Location) — location fields: name, timezone, is_active
- 07_ARCHITECTURE.md § 4 (Frontend routing) — /setup route behaviour

## Backend Agent Tasks
1. Add GET `/api/v1/setup/status` endpoint — returns `{"setup_required": true}` if no Location record exists, `{"setup_required": false}` otherwise. No auth required (called immediately after login to determine redirect).
2. Add POST `/api/v1/setup` endpoint — creates the Location record. **Requires valid ADMIN JWT token.** Fields: name (required, max 100 chars), timezone (required, default Europe/Berlin). Returns the created location. If a Location already exists, return 409.

## Frontend Agent Tasks
1. Implement `frontend/src/pages/auth/SetupPage.tsx` — form with two fields: location name and timezone dropdown. On submit calls POST `/api/v1/setup` with Authorization header (token is already in Zustand store from login). On success redirects to `/approvals`.
2. Add `/setup` route to `routes.tsx` — requires authentication (ADMIN only), but bypasses the normal Location guard.
3. After successful login, before redirecting to home route: call GET `/api/v1/setup/status`. If `setup_required: true`, redirect to `/setup` instead of home route.
4. Add a global guard: on any route load (except `/login` and `/setup`), check setup status. If setup required, redirect to `/setup`.

## Verification
- Fresh database: logging in redirects to `/setup`.
- After completing setup: redirects to `/approvals` and never shows `/setup` again.
- Existing database with location: login goes directly to home route.
- POST `/setup` without auth token → 401.
- POST `/setup` when location already exists → 409.
```

---

## Phase 5 — Draft Entry

**Goal**: Implement the Draft Entry module — backend routes, frontend page, and integration tests.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Draft Entry module completely: backend API, frontend UI, and tests.

## Reference Documents
- 09_UI_DRAFT_ENTRY.md — full — all sections (layout, form fields, table, edit, delete, edge cases, request/response shapes)
- 05_DATA_MODEL.md § 10 (Draft), § 11 (DraftGroup) — entity fields
- 02_DOMAIN_KNOWLEDGE.md § 5 (Draft → Approval workflow) — lifecycle, rules, idempotency
- 08_SETUP_AND_GLOBALS.md § 3 (Validation rules) — quantities, article_no
- 08_SETUP_AND_GLOBALS.md § 4 (Global UI rules) — errors, toasts, loading states, empty states
- 07_ARCHITECTURE.md § 2 (API conventions) — error format, pagination, HTTP status codes
- 03_RBAC.md — OPERATOR and ADMIN can access this module

## Backend Agent Tasks
1. Implement `backend/app/api/drafts/routes.py`:
   - GET `/api/v1/drafts?date=today` — returns all draft lines for today's draft (current operational date based on location timezone).
   - POST `/api/v1/drafts` — create a new draft line. Auto-creates DraftGroup for today if one doesn't exist. Idempotent via client_event_id.
   - PATCH `/api/v1/drafts/{id}` — update quantity only. Only DRAFT status lines can be edited.
   - DELETE `/api/v1/drafts/{id}` — delete a draft line. Only DRAFT status lines can be deleted.
2. Implement `backend/app/utils/validators.py` — batch code regex validation.
3. Article lookup: GET `/api/v1/articles?q={query}` — search by article_no or barcode. Returns article_no, description, base_uom, has_batch.
4. Batch lookup: include available batches in article detail response when has_batch=true, ordered by expiry_date ascending (FEFO).
5. All endpoints require OPERATOR or ADMIN role.

## Frontend Agent Tasks
Implement `frontend/src/pages/drafts/DraftEntryPage.tsx` following 09_UI_DRAFT_ENTRY.md exactly:
1. Entry form: article number input with debounced lookup, auto-populated description + UOM, conditional batch dropdown (FEFO order), optional employee ID, optional note.
2. Submit button "Add" — POST to /api/v1/drafts, clear form on success, keep article field focused.
3. Today's lines table — newest first, columns as specified, edit (quantity only) and delete per row.
4. Edit: inline or modal, PATCH on save, success toast "Entry updated."
5. Delete: inline confirmation, DELETE on confirm, success toast "Entry deleted."
6. Approved lines: edit and delete buttons hidden/disabled.
7. Empty state: "No entries for today yet."
8. Follow all global UI rules: inline validation, toast for server errors and success, loading spinner on submit button, full-page error on network failure after 1 retry.

## Testing Agent Tasks
Write `backend/tests/test_drafts.py`:
- POST draft with valid data → 201.
- POST draft with same client_event_id → idempotent, returns same record.
- POST draft with invalid article_id → 404.
- POST draft with quantity = 0 → 400.
- POST draft with negative quantity → 400.
- PATCH draft quantity → 200.
- PATCH approved draft → 400 or 403.
- DELETE draft → 200.
- DELETE approved draft → 400 or 403.
- GET today's drafts → 200, correct lines returned.
- OPERATOR role can create drafts → 201.
- MANAGER role cannot create drafts → 403.

## Verification
- Operator can enter a draft line end-to-end.
- Article lookup works (type article number → description appears).
- Batch dropdown appears only for has_batch articles.
- All tests pass.
```

---

## Phase 6 — Approvals

**Goal**: Implement the Approvals module — backend routes with surplus-first logic, frontend page, and integration tests.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Approvals module completely: backend API with surplus-first stock logic, frontend UI, and tests.

## Reference Documents
- 10_UI_APPROVALS.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 1 (Core inventory principles) — surplus-first consumption, stock never below zero, audit trail, sign convention
- 02_DOMAIN_KNOWLEDGE.md § 5 (Draft → Approval workflow) — lifecycle, aggregation rules
- 05_DATA_MODEL.md § 8 (Stock), § 9 (Surplus), § 10 (Draft), § 12 (ApprovalAction), § 16 (Transaction) — entity fields
- 07_ARCHITECTURE.md § 2 (API conventions) — error format, HTTP status codes
- 08_SETUP_AND_GLOBALS.md § 4 (Global UI rules)
- 03_RBAC.md — ADMIN only

## Backend Agent Tasks
1. Implement `backend/app/services/approval_service.py` — core business logic:
   - Surplus-first consumption: consume surplus first, then stock.
   - Row-level locking (SELECT FOR UPDATE) to prevent concurrent approval conflicts.
   - Stock never goes below zero — validate before writing.
   - Create Transaction records for every stock change (SURPLUS_CONSUMED, STOCK_CONSUMED).
   - Reorder threshold check after approval — return warning flag if stock falls below threshold.
2. Implement `backend/app/api/approvals/routes.py`:
   - GET `/api/v1/approvals?status=pending` — pending draft groups, lines aggregated by article+batch.
   - GET `/api/v1/approvals?status=history` — all past draft groups.
   - GET `/api/v1/approvals/{draft_group_id}` — full detail with aggregated lines and expandable individual entries.
   - PATCH `/api/v1/approvals/{draft_group_id}/lines/{line_id}` — edit aggregated quantity before approval.
   - POST `/api/v1/approvals/{draft_group_id}/lines/{line_id}/approve` — approve single line.
   - POST `/api/v1/approvals/{draft_group_id}/approve` — approve all lines (skip insufficient stock lines, report them).
   - POST `/api/v1/approvals/{draft_group_id}/lines/{line_id}/reject` — reject single line, reason required.
   - POST `/api/v1/approvals/{draft_group_id}/reject` — reject entire draft group, reason required.
3. All endpoints: ADMIN role only.

## Frontend Agent Tasks
Implement `frontend/src/pages/approvals/ApprovalsPage.tsx` following 10_UI_APPROVALS.md exactly:
1. Two tabs: Pending (default) and History.
2. Pending: one card/section per day, expandable aggregated lines table.
3. Expandable rows show individual operator entries.
4. Approve single, approve all, edit quantity, reject single, reject all.
5. Insufficient stock: inline error on that row.
6. Reorder threshold warning: toast after approval.
7. Reject flow: modal with required reason field.
8. History: read-only, ordered newest first.
9. Empty state: "No pending drafts."

## Testing Agent Tasks
Write `backend/tests/test_approvals.py`:
- Approve line with sufficient stock → 200, stock decreases, transaction created.
- Approve line — surplus consumed first, then stock.
- Approve line with insufficient stock → 409 with INSUFFICIENT_STOCK error.
- Approve all — insufficient stock lines skipped, others approved.
- Edit aggregated quantity before approval → 200.
- Reject line with reason → 200, stock unchanged.
- Reject without reason → 400.
- Approve already-approved line → 409.
- Transaction records created with correct sign (negative for outbound).
- MANAGER cannot approve → 403.

## Verification
- Full approve flow works end-to-end.
- Surplus is consumed before stock.
- Stock never goes below zero.
- All tests pass.
```

---

## Phase 7 — Receiving

**Goal**: Implement the Receiving module — backend routes, frontend page, and integration tests.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Receiving module completely: backend API, frontend UI, and tests.

## Reference Documents
- 11_UI_RECEIVING.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 6 (Receiving) — rules: stock only, delivery note required, ad-hoc rules
- 02_DOMAIN_KNOWLEDGE.md § 3 (Batches) — batch expiry mismatch → 409
- 05_DATA_MODEL.md § 7 (Batch), § 8 (Stock), § 15 (Receiving), § 16 (Transaction) — entity fields
- 07_ARCHITECTURE.md § 2 (API conventions)
- 08_SETUP_AND_GLOBALS.md § 3 (Validation) — batch code regex, delivery note max length
- 03_RBAC.md — ADMIN only

## Backend Agent Tasks
1. Implement `backend/app/services/receiving_service.py`:
   - Increase stock only (never surplus).
   - Weighted average price calculation: `(current_stock × current_avg + received_qty × unit_price) / (current_stock + received_qty)`.
   - Batch handling: create batch if new, match if exists. If batch exists with different expiry_date → 409 BATCH_EXPIRY_MISMATCH.
   - Create STOCK_RECEIPT Transaction record.
   - If linked to order_line: update received_qty on order line, auto-close line if received_qty >= ordered_qty, auto-close order if all active lines closed.
2. Implement `backend/app/api/receiving/routes.py`:
   - POST `/api/v1/receiving` — submit receipt (order-linked or ad-hoc). Request/response shapes as in 11_UI_RECEIVING.md § 10.
   - GET `/api/v1/receiving?page=1&per_page=50` — receipt history.
3. ADMIN role only.

## Frontend Agent Tasks
Implement `frontend/src/pages/receiving/ReceivingPage.tsx` following 11_UI_RECEIVING.md exactly:
1. Two tabs: New Receipt and History.
2. New Receipt: order search field → displays open lines → received qty input per line + batch/expiry if has_batch → delivery note number → submit.
3. Ad-hoc receipt option: separate tab or button, article search, all fields, note required.
4. Skip line checkbox per order line.
5. Batch expiry mismatch: inline error on that line.
6. History tab: read-only list, newest first.
7. All global UI rules applied.

## Testing Agent Tasks
Write `backend/tests/test_receiving.py`:
- Receive against order line → stock increases, order line received_qty updated.
- Receive with batch → batch created, stock increases.
- Receive with existing batch same expiry → stock increases.
- Receive with existing batch different expiry → 409 BATCH_EXPIRY_MISMATCH.
- Ad-hoc receive without note → 400.
- Ad-hoc receive with note → 201.
- All lines received → order auto-closed.
- Delivery note missing → 400.
- Weighted average price calculated correctly.
- STOCK_RECEIPT transaction created.

## Verification
- Full receive flow works end-to-end (order-linked and ad-hoc).
- Batch expiry mismatch is correctly blocked.
- All tests pass.
```

---

## Phase 8 — Orders

**Goal**: Implement the Orders module — backend routes, frontend pages, and integration tests.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Orders module completely: backend API, frontend UI, and tests.

## Reference Documents
- 12_UI_ORDERS.md — full — all sections (list, detail, create, edit, PDF, MANAGER read-only)
- 02_DOMAIN_KNOWLEDGE.md § 7 (Orders) — lifecycle, order number format, line statuses
- 05_DATA_MODEL.md § 13 (Order), § 14 (OrderLine), § 3 (ArticleSupplier) — entity fields
- 07_ARCHITECTURE.md § 2 (API conventions) — pagination, error format
- 03_RBAC.md — ADMIN full, MANAGER read-only

## Backend Agent Tasks
1. Implement `backend/app/api/orders/routes.py`:
   - GET `/api/v1/orders?page=1&per_page=50` — paginated list, open orders first.
   - GET `/api/v1/orders/{id}` — full order detail with lines.
   - POST `/api/v1/orders` — create order with lines. Auto-generate order number (ORD-0001 sequence) if not provided. Validate uniqueness.
   - PATCH `/api/v1/orders/{id}` — edit header fields (supplier_confirmation_number, note).
   - POST `/api/v1/orders/{id}/lines` — add line to existing open order.
   - PATCH `/api/v1/orders/{id}/lines/{line_id}` — edit open line.
   - DELETE `/api/v1/orders/{id}/lines/{line_id}` — remove line (status → REMOVED). Recalculate order status.
   - GET `/api/v1/orders/{id}/pdf` — generate and return PDF of the order.
2. Auto-close order when all active lines are CLOSED.
3. PDF generation: use reportlab or weasyprint. Content as specified in 12_UI_ORDERS.md § 8. No company branding.
4. ADMIN full access, MANAGER GET only.

## Frontend Agent Tasks
1. Implement `frontend/src/pages/orders/OrdersPage.tsx` — list with open orders on top (prominent), closed below (greyed). "New Order" button.
2. Implement `frontend/src/pages/orders/OrderDetailPage.tsx` — header, lines table, edit header, add line, remove line, generate PDF button.
3. New order form: header fields + dynamic lines (add/remove lines before submit).
4. MANAGER view: all actions hidden, PDF button visible.
5. All global UI rules applied.

## Testing Agent Tasks
Write `backend/tests/test_orders.py`:
- Create order → 201, order number auto-generated.
- Create order with manual number → 201.
- Duplicate order number → 409.
- Add line to open order → 200.
- Edit line → 200.
- Remove line → line status REMOVED, order status recalculated.
- Remove last active line → order auto-closed.
- Edit closed order → 403 or 400.
- MANAGER GET order → 200.
- MANAGER POST order → 403.

## Verification
- Full order creation flow works.
- PDF downloads correctly.
- MANAGER can view but not edit.
- All tests pass.
```

---

## Phase 9 — Warehouse

**Goal**: Implement the Warehouse module — articles list, article detail, stock/batch view, transaction history, barcode print scaffold.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Warehouse module: articles list with stock levels, article detail with full data, create/edit/deactivate articles, transaction history per article.

## Reference Documents
- 13_UI_WAREHOUSE.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 2 (Articles) — fields, categories, aliases, barcodes
- 02_DOMAIN_KNOWLEDGE.md § 11 (Reorder threshold) — red/yellow zone logic
- 05_DATA_MODEL.md § 2 (Article), § 4 (ArticleAlias), § 7 (Batch), § 8 (Stock), § 9 (Surplus), § 16 (Transaction) — entity fields
- 08_SETUP_AND_GLOBALS.md § 3.1 (Article number validation) — uppercase, allowed chars, max length
- 07_ARCHITECTURE.md § 2 (API conventions) — pagination
- 03_RBAC.md — ADMIN full, MANAGER read-only

## Backend Agent Tasks
1. Implement `backend/app/api/articles/routes.py`:
   - GET `/api/v1/articles?page=1&per_page=50&q={}&category={}&include_inactive={}` — paginated, with stock + surplus totals, reorder_status per article.
   - GET `/api/v1/articles/{id}` — full detail: article fields, stock, surplus, batches (FEFO order), suppliers, aliases.
   - POST `/api/v1/articles` — create article. Normalize article_no to uppercase. Validate: allowed chars, max length, uniqueness.
   - PUT `/api/v1/articles/{id}` — edit article.
   - PATCH `/api/v1/articles/{id}/deactivate` — deactivate article.
   - GET `/api/v1/articles/{id}/transactions?page=1&per_page=50` — paginated transaction history for article.
   - GET `/api/v1/articles/{id}/barcode` — scaffold only (returns 501 Not Implemented for now — implemented in Phase 15).
2. Reorder status logic: red = qty <= threshold, yellow = threshold < qty <= threshold × 1.10, normal = above.
3. ADMIN full, MANAGER GET only.

## Frontend Agent Tasks
1. Implement `frontend/src/pages/warehouse/WarehousePage.tsx` — searchable/filterable articles list, reorder status colour indicators (subtle), "New Article" button.
2. Implement `frontend/src/pages/warehouse/ArticleDetailPage.tsx` — master data (inline editable), stock+surplus section, batch table (FEFO), suppliers section, transaction history (paginated).
3. Create article form (modal or page).
4. Deactivate: confirmation modal.
5. MANAGER: all edit actions hidden.
6. All global UI rules applied.

## Testing Agent Tasks
Write `backend/tests/test_articles.py`:
- Create article → 201, article_no stored uppercase.
- Duplicate article_no → 409.
- Invalid article_no chars → 400.
- GET articles list → 200, stock totals included.
- GET article detail → 200, batches in FEFO order.
- Deactivate article → 200, is_active false.
- GET articles excludes inactive by default.
- MANAGER GET → 200.
- MANAGER POST → 403.
- Reorder status correct for red/yellow/normal zones.

## Verification
- Articles list loads with stock levels and colour indicators.
- Article detail shows batches in FEFO order.
- Create and edit article works end-to-end.
- All tests pass.
```

---

## Phase 10 — Identifier

**Goal**: Implement the Identifier module — article search, missing article reports, admin report queue.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Identifier module: fast article search across all identifiers, missing article report submission, admin report queue.

## Reference Documents
- 14_UI_IDENTIFIER.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 14 (Identifier module) — search fields, deduplication, report lifecycle
- 05_DATA_MODEL.md § 4 (ArticleAlias), § 24 (MissingArticleReport) — entity fields
- 03_RBAC.md — ADMIN, MANAGER, WAREHOUSE_STAFF, VIEWER access; VIEWER sees availability only

## Backend Agent Tasks
1. Implement `backend/app/api/articles/routes.py` (extend existing):
   - GET `/api/v1/identifier?q={query}` — search articles by article_no, description, alias (normalized), barcode. Min 2 chars. Return stock/surplus for non-VIEWER roles; return in_stock boolean only for VIEWER.
2. Implement `backend/app/api/articles/routes.py` (missing reports):
   - POST `/api/v1/identifier/reports` — submit missing article report. Normalize search_term. If same normalized term exists as OPEN report → increment counter, do not create duplicate.
   - GET `/api/v1/identifier/reports?status=open` — ADMIN only, list open reports.
   - POST `/api/v1/identifier/reports/{id}/resolve` — ADMIN only, resolve report with optional note.
3. Alias normalization: lowercase + trim.

## Frontend Agent Tasks
Implement `frontend/src/pages/identifier/IdentifierPage.tsx` following 14_UI_IDENTIFIER.md exactly:
1. Large auto-focused search field, real-time debounced search (min 2 chars).
2. Result cards per matching article — show matched alias if found via alias.
3. Stock display depends on role (VIEWER: In stock / Out of stock only).
4. Not found state: "No articles found for '[term]'." + "Report missing article" button.
5. Report flow: pre-filled term, editable, submit, success toast.
6. Admin report queue: separate section/tab within Identifier, list of OPEN reports, resolve action with optional note.

## Testing Agent Tasks
Write tests in `backend/tests/test_articles.py` (extend):
- Search by article_no → returns correct article.
- Search by alias → returns article, matched_via = "alias".
- Search by barcode → returns correct article.
- Search with less than 2 chars → empty result (or 400).
- VIEWER role: stock replaced with in_stock boolean.
- Submit missing report → 201.
- Submit same term again → counter incremented, no duplicate.
- Resolve report → status RESOLVED.
- MANAGER cannot resolve report → 403.

## Verification
- Search finds articles by all identifier types.
- VIEWER sees availability only.
- Missing report flow works end-to-end.
- All tests pass.
```

---

## Phase 11 — Employees

**Goal**: Implement the Employees module — employee master data, personal issuances, quota enforcement.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Employees module: employee list and detail, personal issuance workflow with quota checking.

## Reference Documents
- 15_UI_EMPLOYEES.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 8 (Employees and personal issuances) — rules, quota logic
- 05_DATA_MODEL.md § 19 (Employee), § 20 (PersonalIssuance), § 21 (AnnualQuota) — entity fields
- 05_DATA_MODEL.md § 5 (Category) — is_personal_issue flag
- 03_RBAC.md — ADMIN full, WAREHOUSE_STAFF read-only

## Backend Agent Tasks
1. Implement `backend/app/api/employees/routes.py`:
   - GET `/api/v1/employees?page=1&per_page=50&q={}&include_inactive={}` — paginated list.
   - GET `/api/v1/employees/{id}` — employee detail.
   - POST `/api/v1/employees` — create employee. Validate unique employee_id.
   - PUT `/api/v1/employees/{id}` — edit employee.
   - PATCH `/api/v1/employees/{id}/deactivate` — deactivate employee.
   - GET `/api/v1/employees/{id}/quotas` — quota overview for current year: per article/category, quota, received, remaining, status (OK/Warning/Exceeded).
   - GET `/api/v1/employees/{id}/issuances?page=1&per_page=50` — issuance history.
   - POST `/api/v1/employees/{id}/issuances` — issue article. Only articles with is_personal_issue=true category. Quota check before issuing: WARN returns warning in response but allows proceed, BLOCK returns 400. Create PERSONAL_ISSUE Transaction.
2. Quota priority: employee+article override > article override > job_title+category default.
3. Warning threshold: received >= quota × 0.80 → status = Warning.
4. ADMIN full, WAREHOUSE_STAFF GET only.

## Frontend Agent Tasks
1. Implement `frontend/src/pages/employees/EmployeesPage.tsx` — searchable list, show inactive toggle, "New Employee" button (ADMIN only).
2. Implement `frontend/src/pages/employees/EmployeeDetailPage.tsx`:
   - Header: employee data, Edit + Deactivate buttons (ADMIN only).
   - Annual quota overview section (top, prominent): table with quota/received/remaining/status.
   - "Issue article" button (ADMIN only).
   - Issuance history section (below, paginated).
3. Issuance form: article search (personal-issue only), quantity, conditional batch, note. Quota check warning inline before submit.
4. WAREHOUSE_STAFF: no edit/issue actions visible.

## Testing Agent Tasks
Write `backend/tests/test_employees.py`:
- Create employee → 201.
- Duplicate employee_id → 409.
- Issue article (personal-issue category) → 201, transaction created.
- Issue non-personal-issue article → 400.
- Issue within quota → 201.
- Issue exceeding quota, enforcement WARN → 201 with warning.
- Issue exceeding quota, enforcement BLOCK → 400.
- Quota overview returns correct received/remaining values.
- WAREHOUSE_STAFF GET employee → 200.
- WAREHOUSE_STAFF POST issuance → 403.

## Verification
- Employee detail shows quota overview prominently.
- Issuance flow works with quota check.
- All tests pass.
```

---

## Phase 12 — Inventory Count

**Goal**: Implement the Inventory Count module — start count, enter quantities, complete count with automatic discrepancy processing.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Inventory Count module: start count, enter counted quantities per article, complete count with automatic surplus/shortage processing.

## Reference Documents
- 16_UI_INVENTORY_COUNT.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 4 (Stock and Surplus) — surplus handling
- 05_DATA_MODEL.md § 17 (InventoryCount), § 18 (InventoryCountLine) — entity fields
- 03_RBAC.md — ADMIN only

## Backend Agent Tasks
1. Implement `backend/app/services/inventory_service.py`:
   - On count start: snapshot system_quantity for all active articles (and per batch if has_batch).
   - On count complete: process all lines — counted > system → add to Surplus; counted < system → create INVENTORY_SHORTAGE Draft; counted = system → NO_CHANGE.
   - Create Transaction records for surplus additions (INVENTORY_ADJUSTMENT).
2. Implement `backend/app/api/inventory_count/routes.py`:
   - GET `/api/v1/inventory?page=1&per_page=50` — count history.
   - POST `/api/v1/inventory` — start new count. Block if one already IN_PROGRESS.
   - GET `/api/v1/inventory/active` — get active count with all lines.
   - GET `/api/v1/inventory/{id}` — count detail (completed, read-only).
   - PATCH `/api/v1/inventory/{id}/lines/{line_id}` — update counted_quantity. Save on each call (auto-save on blur).
   - POST `/api/v1/inventory/{id}/complete` — complete count. Block if any line has NULL counted_quantity.
3. ADMIN only.

## Frontend Agent Tasks
Implement `frontend/src/pages/inventory/InventoryCountPage.tsx` following 16_UI_INVENTORY_COUNT.md exactly:
1. No active count: show "Start New Count" button + history list.
2. Active count: header with progress indicator, lines table with counted qty input per row.
3. Counted qty field: auto-save on blur (PATCH), real-time difference calculation.
4. Row colour indicators: green (match), blue (surplus), yellow (shortage), neutral (uncounted).
5. Filters: "show only discrepancies" and "show only uncounted" toggles.
6. "Complete Count" button: disabled until all lines have counted_qty. Confirmation prompt.
7. Completed count detail: read-only, summary widget, filter by resolution.
8. History list: click row → completed count detail.

## Testing Agent Tasks
Write `backend/tests/test_inventory_count.py`:
- Start count → 201, lines generated for all active articles.
- Start count while one IN_PROGRESS → 400.
- Update counted_qty → 200, difference calculated.
- Complete count with uncounted lines → 400.
- Complete count — surplus added where counted > system.
- Complete count — INVENTORY_SHORTAGE draft created where counted < system.
- Complete count — NO_CHANGE where counted = system.
- Completed count is read-only (PATCH returns 400).

## Verification
- Full inventory count flow works end-to-end.
- Surplus added automatically, shortage creates draft in Approvals.
- All tests pass.
```

---

## Phase 13 — Reports

**Goal**: Implement the Reports module — stock overview, surplus list, transaction log, statistics.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Reports module: three data reports (stock overview, surplus list, transaction log) and a statistics tab with charts.

## Reference Documents
- 17_UI_REPORTS.md — full — all sections
- 02_DOMAIN_KNOWLEDGE.md § 11 (Reorder threshold) — red/yellow zone logic
- 05_DATA_MODEL.md § 16 (Transaction) — transaction types and fields
- 03_RBAC.md — ADMIN full (with export), MANAGER read-only (no export)

## Backend Agent Tasks
1. Implement `backend/app/api/reports/routes.py`:
   - GET `/api/v1/reports/stock-overview?date_from={}&date_to={}&category={}&reorder_only={}` — per article: stock, surplus, total_available, inbound in period, outbound in period, avg_monthly_consumption, coverage_months, reorder_status.
   - GET `/api/v1/reports/surplus` — all current surplus records.
   - GET `/api/v1/reports/transactions?article_id={}&date_from={}&date_to={}&tx_type={}&page=1&per_page=50` — paginated transaction log with filters.
   - GET `/api/v1/reports/stock-overview/export?format=xlsx|pdf` — export full stock overview.
   - GET `/api/v1/reports/surplus/export?format=xlsx|pdf` — export surplus list.
   - GET `/api/v1/reports/transactions/export?format=xlsx|pdf&...filters` — export transaction log.
2. Coverage calculation: `(stock + surplus) / (outbound / months_in_period)`. If outbound = 0 → coverage = null (frontend shows "∞").
3. Months in period: `(date_to - date_from).days / 30.44`.
4. Export: Excel via openpyxl, PDF via reportlab. Filenames as specified in 17_UI_REPORTS.md § 8. No branding.
5. MANAGER: all GETs allowed, export endpoints return 403.

## Frontend Agent Tasks
Implement `frontend/src/pages/reports/ReportsPage.tsx` with four tabs:
1. **Stock Overview**: date range inputs, category filter, reorder-only toggle, table with all columns, export buttons (ADMIN only). Coverage "∞" when null.
2. **Surplus List**: table, export buttons (ADMIN only).
3. **Transaction Log**: article search, date range, tx type multi-select, paginated table, export buttons (ADMIN only).
4. **Statistics**: four sections — top 10 by consumption (bar chart), inbound/outbound over time (line chart), reorder zone summary widget (clickable), personal issuances table (de-emphasised, current year).
   - Use recharts for charts.
   - Mixed UOM note below inbound/outbound chart.
   - Reorder zone counts link to Stock Overview tab with pre-applied filter.

## Testing Agent Tasks
Write `backend/tests/test_reports.py`:
- Stock overview returns correct inbound/outbound for period.
- Coverage calculated correctly (test with known data).
- Coverage null when outbound = 0.
- Surplus list returns all current surplus.
- Transaction log filtered by article → correct transactions.
- Transaction log filtered by date range → correct transactions.
- Export endpoints return file (200 with correct content-type).
- MANAGER export → 403.

## Verification
- All three report tabs load with correct data.
- Charts render in Statistics tab.
- Export downloads correct files.
- All tests pass.
```

---

## Phase 14 — Settings

**Goal**: Implement the Settings module — all configuration sections and user management.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent, frontend agent, and testing agent.

## Goal
Implement the Settings module: all configuration sections (general, roles, UOM, categories, quotas, barcode, export) and user management.

## Reference Documents
- 18_UI_SETTINGS.md — full — all sections
- 08_SETUP_AND_GLOBALS.md § 1 (Seed data) — seeded UOM and categories
- 05_DATA_MODEL.md § 5 (Category), § 6 (UomCatalog), § 21 (AnnualQuota), § 22 (User) — entity fields
- 03_RBAC.md — ADMIN only

## Backend Agent Tasks
1. Implement `backend/app/api/settings/routes.py`:
   - GET/PUT `/api/v1/settings/general` — location name, language, timezone.
   - GET/PUT `/api/v1/settings/roles` — display names for all 5 system roles.
   - GET `/api/v1/settings/uom` — list all UOM catalog entries.
   - POST `/api/v1/settings/uom` — add new UOM. Code must be unique.
   - GET `/api/v1/settings/categories` — list all categories.
   - PUT `/api/v1/settings/categories/{id}` — edit labels and personal_issue flag.
   - GET/POST `/api/v1/settings/quotas` — list and create quotas.
   - PUT/DELETE `/api/v1/settings/quotas/{id}` — edit and delete quotas.
   - GET/PUT `/api/v1/settings/barcode` — barcode format and printer name.
   - GET/PUT `/api/v1/settings/export` — export format config.
   - GET `/api/v1/settings/users` — list all system users.
   - POST `/api/v1/settings/users` — create user. Unique username, min 4 char password.
   - PUT `/api/v1/settings/users/{id}` — edit role, reset password.
   - PATCH `/api/v1/settings/users/{id}/deactivate` — deactivate user. Cannot deactivate self.
   - GET `/api/v1/settings/suppliers` — list all suppliers (paginated).
   - POST `/api/v1/settings/suppliers` — create supplier.
   - PUT `/api/v1/settings/suppliers/{id}` — edit supplier.
   - PATCH `/api/v1/settings/suppliers/{id}/deactivate` — deactivate supplier.
2. All endpoints: ADMIN only.

## Frontend Agent Tasks
Implement `frontend/src/pages/settings/SettingsPage.tsx` following 18_UI_SETTINGS.md exactly:
1. Nine clearly separated sections, each with its own Save button.
2. General: location name, language dropdown, timezone dropdown. Reads/writes Location + SystemConfig (`default_language`).
3. Roles: display name input per system role. Reads/writes RoleDisplayName table.
4. UOM Catalog: table of existing UOMs, "Add unit" inline form.
5. Article Categories: table with editable labels and personal issue toggle.
6. Quotas: table with edit/delete per row, "Add quota" form.
7. Barcode: format dropdown, printer name text input. Reads/writes SystemConfig (`barcode_format`, `barcode_printer`).
8. Export: format dropdown. Reads/writes SystemConfig (`export_format`).
9. Suppliers: searchable table of all suppliers, "New supplier" form, edit/deactivate per row.
10. Users: table with edit/deactivate actions, "New user" form.

## Testing Agent Tasks
Write `backend/tests/test_settings.py` (basic coverage):
- Save general settings → 200.
- Save general settings with empty location name → 400.
- Add UOM with unique code → 201.
- Add UOM with duplicate code → 409.
- Update category labels → 200.
- Add quota → 201.
- Delete quota → 200.
- Create supplier → 201.
- Create user → 201.
- Create user with duplicate username → 409.
- Deactivate user → 200.
- Admin cannot deactivate own account → 400.

## Verification
- All settings sections save correctly.
- User management works end-to-end.
- All tests pass.
```

---

## Phase 15 — Barcodes & Export

**Goal**: Implement barcode generation and printing (articles and batches), and verify all Excel/PDF exports work correctly end-to-end.

---

### Orchestrator Prompt

```
You are the orchestrator for a WMS project. Delegate to backend agent only.

## Goal
Implement barcode generation for articles and batches. Verify all export functionality (Excel and PDF) works correctly across all modules.

## Reference Documents
- 02_DOMAIN_KNOWLEDGE.md § 2.4 (Barcodes) — EAN-13 or Code128, generate + print
- 02_DOMAIN_KNOWLEDGE.md § 3 (Batches) — batch barcode generated at receiving, barcodes_printed count
- 05_DATA_MODEL.md § 2 (Article barcode field), § 7 (Batch barcode field), § 15 (Receiving — barcodes_printed)
- 13_UI_WAREHOUSE.md § 7 (Barcode printing) — article barcode from detail screen, batch barcode from batch table
- 17_UI_REPORTS.md § 6 (Export format) — filenames, layout, no branding

## Backend Agent Tasks
1. Implement `backend/app/services/barcode_service.py`:
   - Generate barcode for article: use python-barcode library. Format configurable (EAN-13 / Code128) from settings. Return PDF with barcode label.
   - Generate barcode for batch: same logic. Number of labels = barcodes_printed count from Receiving record.
2. Complete `backend/app/api/articles/routes.py`:
   - GET `/api/v1/articles/{id}/barcode` — generate and return PDF barcode label for article.
   - GET `/api/v1/batches/{id}/barcode` — generate and return PDF barcode label(s) for batch.
3. Verify all export endpoints implemented in Phase 13 work correctly:
   - Excel exports: correct columns, data, auto-fitted widths, correct filename.
   - PDF exports: A4 landscape, header with report name + date + timestamp, no branding, correct filename.
4. Run all existing tests to confirm nothing is broken.

## Verification
- Article barcode PDF downloads correctly from Warehouse detail screen.
- Batch barcode PDF downloads correctly.
- All report exports (Excel + PDF) download with correct content.
- All existing tests still pass.
```

---

## Final Checklist

Before considering the project complete, verify:

- [ ] All 15 phases completed and verified
- [ ] `alembic upgrade head` runs cleanly on fresh database
- [ ] Seed script runs cleanly (admin user, UOM catalog, categories)
- [ ] First-run setup flow works on fresh database
- [ ] All backend tests pass (`pytest tests/ -v`)
- [ ] All modules accessible by correct roles only
- [ ] Frontend builds without errors (`npm run build`)
- [ ] Flask serves React build correctly (production mode test)
- [ ] `deploy.sh` script runs successfully on target local server
