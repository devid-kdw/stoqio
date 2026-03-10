# Backend Handoff — Phase 03 Authentication

Reserved for backend agent entries. Append only.

## 2026-03-10 Backend Agent

Status
- completed

Scope
- Phase 3 backend: JWT auth endpoints (login / refresh / logout), RBAC decorators, in-repo rate limiter, token blocklist, idempotent seed script, and test coverage for 401 / 403 / 429 paths.

Docs Read
- `stoqio_docs/07_ARCHITECTURE.md` §2 (API conventions + error format), §3 (auth flow), §4 (frontend routing / role home map), §6 (dev workflow)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` §1 (seed data), §3.4 (password rules)
- `stoqio_docs/05_DATA_MODEL.md` §22 (User), §23 (Location), §25 (SystemConfig), §26 (RoleDisplayName)
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` §13 (security), §15 (settings persistence)
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-01-project-setup/backend.md`
- `handoff/phase-02-database-models/backend.md`

Files Changed
- `backend/app/utils/auth.py` [NEW] — in-memory token blocklist (`add_to_blocklist`, `is_token_revoked`); sliding-window rate limiter (`check_rate_limit`, 10 req/min per IP, no new dependency); `require_role(*roles)` decorator; `require_any_role` alias; `get_current_user()` helper. Uses `verify_jwt_in_request()` internally so Flask-JWT-Extended error handlers produce the standard error shape on missing/invalid tokens.
- `backend/app/api/auth/routes.py` [NEW] — `auth_bp` Flask Blueprint; JWT error handler callbacks (`expired`, `invalid`, `unauthorized`, `revoked`, `blocklist`) all returning `{"error":…,"message":…,"details":{}}` shape; `POST /login` with rate limiting + pbkdf2:sha256 verification + role-based refresh token lifetime (30 d OPERATOR, 8 h all others) + 15 min access token; `POST /refresh` (`@jwt_required(refresh=True)`); `POST /logout` (`@jwt_required(verify_type=False)`) + blocklist; `GET /me` (`@jwt_required()`) — 401 coverage; `GET /admin-only` (`@require_role("ADMIN")`) — 403 coverage.
- `backend/app/api/__init__.py` [MODIFIED] — added `from .auth.routes import auth_bp` and `app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")`.
- `backend/seed.py` [NEW] — standalone idempotent seed script. Seeds: admin user, 10 UOM entries, 12 article categories (label_en populated, label_de / label_hu = NULL), 4 SystemConfig defaults, 5 RoleDisplayName defaults. Does NOT seed Location. Each seeder uses a filter_by + skip pattern for idempotency.
- `backend/tests/conftest.py` [MODIFIED] — added `sqlalchemy.pool.StaticPool` to `_TestConfig.SQLALCHEMY_ENGINE_OPTIONS` so Flask test-client HTTP requests share the same in-memory SQLite database as fixture code; added session-scoped `auth_users` fixture that creates admin / manager / operator / inactive test users once per session.
- `backend/tests/test_auth.py` [NEW] — 26 pytest tests across 6 classes: `TestLogin` (9 tests), `TestRefresh` (3), `TestLogout` (3), `TestMe` (4), `TestAdminOnly` (5), `TestRateLimit` (2).

Commands Run
```bash
# From backend/ directory
./venv/bin/pytest tests/ -v          # 29 passed (26 new auth + 3 regression)

# Seed script verification (alembic migration run first):
DATABASE_URL=sqlite:///seed_verify2.db FLASK_ENV=development JWT_SECRET_KEY=test-secret \
  python -m alembic upgrade head
DATABASE_URL=sqlite:///seed_verify2.db FLASK_ENV=development JWT_SECRET_KEY=test-secret \
  python seed.py
# Output: all 5 seeders reported "[seed] N entries created"

# Idempotency check (re-run):
DATABASE_URL=sqlite:///seed_verify2.db FLASK_ENV=development JWT_SECRET_KEY=test-secret \
  python seed.py
# Output: all 5 seeders reported "[skip] already seeded / already exists"
```

Seed command for production use:
```bash
cd backend
alembic upgrade head
python seed.py
```

Tests
- Passed: 26 new auth tests + 3 pre-existing regression tests = 29 total
- Failed: None
- Notable assertions:
  - login → 200 + access_token + refresh_token + user object
  - wrong password → 401 INVALID_CREDENTIALS
  - inactive user → 401 ACCOUNT_INACTIVE
  - no token → 401 TOKEN_MISSING (standard shape)
  - expired/revoked token → 401 TOKEN_EXPIRED / TOKEN_REVOKED (standard shape)
  - non-ADMIN on /admin-only → 403 FORBIDDEN (standard shape)
  - ADMIN on /admin-only → 200
  - 11th login from same IP in 60 s → 429 RATE_LIMITED
  - post-logout token reuse → 401 TOKEN_REVOKED

Open Issues / Risks
- **In-memory blocklist**: `_revoked_jtis` is a module-level `set`. It does not survive server restarts. On Pi (single long-running Gunicorn process) this is acceptable for Phase 3. If logout survivability across restarts is required later, the blocklist should be moved to the database (a `revoked_token` table).
- **In-memory rate store**: `_rate_store` is also module-level and process-local. Suitable for single-process Pi deployment. Would need shared storage (Redis or DB) for multi-process Gunicorn.
- **JWT secret warning in tests**: `_TestConfig.JWT_SECRET_KEY = "test-secret"` is 11 bytes, below the PyJWT recommended 32. The warning is harmless in test context. Production config already enforces ≥ 32-character secrets via `Production._WEAK_SECRETS` guard.
- **SQLAlchemy `Session.get()` used**: Replaced deprecated `Query.get()` throughout `auth.py` to eliminate LegacyAPIWarning. The `Query.get()` form is still used in `seed.py` (filter_by, not get()) — no issue.
- **Phase 2 regression preserved**: The `conftest.py` StaticPool addition does not break Phase 2 tests (verified: 29/29 pass).

Assumptions
- Location record is assumed to exist for auth verification (per Phase 3 boundary doc). No Location is seeded here. Auth routes themselves do not check for Location — the Phase 4 setup guard is out of scope.
- The `GET /admin-only` and `GET /me` endpoints are added to `auth_bp` explicitly for 401/403 test coverage. `GET /me` is also useful for the frontend to validate a stored token after in-memory session restore.
- Token blocklist is checked on ALL token types (both access and refresh) via `@jwt.token_in_blocklist_loader`. This means logging out with an access token also revokes that access token (not just the refresh token). This is more conservative than the spec's "invalidacija refresh tokena" language, but safer.

Next Recommended Step
- Phase 3 frontend agent: implement login form, auth store (Zustand), axios refresh interceptor, protected routes, and RBAC-aware sidebar.
- Phase 3 testing agent: end-to-end browser verification of login → token refresh → logout flow.

---

## 2026-03-10 Backend Agent — Review-driven fixes

Status
- completed

Scope
- Fix two auth-flow bugs identified in review. Add test coverage for the two previously-untested phase-critical behaviors.

Findings Addressed
1. **High: Logout did not invalidate the refresh token.** `POST /logout` used `@jwt_required(verify_type=False)` so callers could log out with their access token, leaving the refresh token fully valid. Fixed by changing to `@jwt_required(refresh=True)`. The endpoint now requires the refresh token and blocklists its JTI.
2. **High: Refresh trusted stale JWT claims.** `POST /refresh` used embedded `role`/`username` claims from the token without re-checking the user record. A deactivated user could keep minting access tokens until their refresh token expired. Fixed: `/refresh` now calls `db.session.get(User, identity)`, checks `is_active`, and builds new access-token claims from the current DB record.
3. **Medium: Missing test coverage.** The test suite did not cover either behavior above.

Files Changed
- `backend/app/api/auth/routes.py` — added `from app.extensions import db`; rewrote `refresh()` to do DB lookup + is_active check + use live role/username; changed `logout()` decorator from `@jwt_required(verify_type=False)` to `@jwt_required(refresh=True)` and updated docstring.
- `backend/tests/test_auth.py` — replaced `TestLogout` tests (now use refresh token, add explicit rejection test for access-token-at-logout); added `TestRefresh.test_refresh_fails_for_deactivated_user` and `TestRefresh.test_refresh_uses_current_db_role`.

Commands Run
```bash
./venv/bin/pytest tests/ -q   # 32 passed (3 new tests + 29 existing)
rm -f backend/seed_verify.db backend/seed_verify2.db
```

Tests
- Passed: 32 total — no regressions
- New: `test_logout_revokes_refresh_token`, `test_logout_with_access_token_is_rejected`, `test_refresh_fails_for_deactivated_user`, `test_refresh_uses_current_db_role`
- Failed: None

Open Issues / Risks
- None introduced. Previous open issues (in-memory blocklist / rate store process-locality) remain noted above and are acceptable for Phase 3 scope.

## 2026-03-10 Orchestrator Follow-up Note — Seed Reliability & Closure Verification

Status
- completed

Scope
- Fix the remaining Phase 3 closure blocker around bootstrap/admin verification.
- Ensure seed and diagnostic helpers read `.env` consistently with the development entrypoint.

Docs Read
- `handoff/phase-03-authentication/backend.md`
- `handoff/phase-03-authentication/testing.md`
- `backend/run.py`

Files Changed
- `backend/seed.py` — added `load_dotenv()` so `python seed.py` targets the configured database from `.env`.
- `backend/diagnostic.py` — added `load_dotenv()` so credential checks inspect the same DB as the app.
- `backend/seed_location.py` — added `load_dotenv()` for consistent initialized-installation verification.

Commands Run
```bash
backend/venv/bin/pytest backend/tests -q
cd backend && DATABASE_URL=sqlite:////tmp/phase3_closure.db FLASK_ENV=development JWT_SECRET_KEY=test-secret ./venv/bin/python -m alembic upgrade head
cd backend && DATABASE_URL=sqlite:////tmp/phase3_closure.db FLASK_ENV=development JWT_SECRET_KEY=test-secret ./venv/bin/python seed.py
cd backend && DATABASE_URL=sqlite:////tmp/phase3_closure.db FLASK_ENV=development JWT_SECRET_KEY=test-secret ./venv/bin/python seed_location.py
cd backend && DATABASE_URL=sqlite:////tmp/phase3_closure.db FLASK_ENV=development JWT_SECRET_KEY=test-secret ./venv/bin/python diagnostic.py
```

Tests
- Passed: `backend/venv/bin/pytest backend/tests -q` → `32 passed`
- Passed: temp SQLite verification DB migrates and seeds successfully
- Passed: `diagnostic.py` confirms `admin` exists in the same DB and `admin123` matches
- Failed: None
- Not run: live PostgreSQL verification in sandbox

Open Issues / Risks
- In-memory logout blocklist and rate limiter remain process-local by design for Phase 3.

Next Recommended Step
- Backend Phase 3 is acceptable for closure.
