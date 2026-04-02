# STOQIO Project Memory

## Project Overview
WMS (Warehouse Management System) — Flask backend + React frontend. Designed as a local host/server application running inside the customer network (mini PC, local Linux server, local Windows server, or similar local hardware). Raspberry Pi was the original reference target and remains a valid deployment option.
Single PostgreSQL database; tests use SQLite in-memory with StaticPool.

## Key Architecture
- Backend: Flask, SQLAlchemy, Flask-JWT-Extended
- Frontend: React + Vite + Mantine + TanStack Query + Zustand
- All API endpoints: `/api/v1/`
- Standard paginated response: `{items, total, page, per_page}`
- Standard error: `{error, message, details}`
- Auth: Access token (15 min, memory-only in Zustand) + Refresh token (persisted in browser localStorage under key `stoqio_refresh_token`). On app bootstrap, stored refresh token → silent POST /auth/refresh → GET /auth/me → hydrate Zustand before protected routes render. Bootstrap failure clears persisted token and redirects to /login. Access token must never be written to localStorage. See DEC-FE-006.

## Phases Completed
- Phase 1–10: Setup, DB models, Auth, Setup wizard, Drafts, Approvals, Receiving, Orders, Warehouse, Identifier
- Phase 11: Employees backend + frontend — full employee CRUD, quota overview, issuance history/create/check, article lookup; EmployeesPage + EmployeeDetailPage with issuance form

## Backend Test Pattern
- Test file: `backend/tests/test_<module>.py`
- Use `scope="module"` fixture for seeding data
- Use `_token_cache` dict + `environ_base={"REMOTE_ADDR": "127.0.X.1"}` to avoid rate limiting (10 req/60s per IP)
- Each module uses a unique REMOTE_ADDR so login calls don't collide
- Quotas/state created in one test affect later tests in same session — use employee-specific quotas (highest priority) to prevent pollution

## Key Models
- `Employee`: employee_id (unique str), first_name, last_name, department, job_title, is_active
- `PersonalIssuance`: employee_id FK, article_id FK, batch_id FK (nullable), quantity, uom, issued_by FK (User), issued_at, note
- `AnnualQuota`: job_title, category_id FK, article_id FK, employee_id FK (all nullable for priority logic), quantity, uom, reset_month, enforcement (WARN/BLOCK)
- `Location.id = 1` is the canonical v1 location (DEC-BE-003)
- `Transaction.quantity` is negative for outbound operations

## Quota Priority (locked)
1. employee_id + article_id override
2. article_id only (global)
3. job_title + category_id default

## RBAC (Employees module)
- ADMIN: full access
- WAREHOUSE_STAFF: GET-only (list, detail, quotas, issuances)
- Issuance check/create + article lookup: ADMIN only

## Service Layer Pattern
- `app/services/<module>_service.py` — business logic
- Raises `<Module>ServiceError(error, message, status_code, details)` for all errors
- Routes catch and return `jsonify({error, message, details}), status_code`
- Routes call `db.session.rollback()` on mutation errors

## Decisions Logged
- DEC-EMP-001: PersonalIssuance decrements Stock (batch-specific or non-batch row)
- DEC-EMP-002: Category-level quotas → one row per category in overview (not per article)
- See `handoff/decisions/decision-log.md` for all prior decisions (DEC-BE-*, DEC-FE-*, DEC-ORD-*, DEC-WH-*, DEC-ID-*)
