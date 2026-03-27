# Backend Handoff — Wave 2 Phase 4: Startup/Auth Hardening

---

## Entry 1 — 2026-03-27

### Status

Complete.

### Scope

- Hardened `Production` config to fail fast on missing/blank `DATABASE_URL`.
- Centralized the timing-safe dummy hash into `app.utils.auth` and removed the hardcoded PBKDF2 literal from `app.api.auth.routes`.
- Added 9 focused backend tests covering the new config contract and the preserved hash-check path.

### Docs Read

- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (F-035, F-036)
- `stoqio_docs/07_ARCHITECTURE.md` § 3 (skimmed for auth/config scope)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` (skimmed for globals conventions)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (entries DEC-BE-001 through existing)
- `handoff/phase-04-wave-02-startup-auth-hardening/orchestrator.md`
- `backend/app/config.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_auth.py`
- `backend/tests/conftest.py`

### Files Changed

1. **`backend/app/config.py`**
   - `Production.__init__`: added `DATABASE_URL` check immediately after `super().__init__()`. Reads env var into `db_url`; raises `RuntimeError("Production requires DATABASE_URL to be set. Set it in your .env file.")` when blank or missing. Non-blank value is then assigned to `self.SQLALCHEMY_DATABASE_URI`. JWT_SECRET_KEY validation is unchanged.

2. **`backend/app/utils/auth.py`**
   - Added `from werkzeug.security import generate_password_hash` import.
   - Added module-level `_DUMMY_HASH: str = generate_password_hash("dummy-placeholder", method="pbkdf2:sha256")` — generated once at import, no per-request churn.
   - Added `get_dummy_hash() -> str` public helper that returns `_DUMMY_HASH`.
   - All existing functions (`add_to_blocklist`, `is_token_revoked`, `check_rate_limit`, RBAC decorators, `get_current_user`) are unchanged.

3. **`backend/app/api/auth/routes.py`**
   - Added `get_dummy_hash` to the import from `app.utils.auth`.
   - In `login()`: replaced the 3-line hardcoded `_dummy_hash` literal block with `candidate_hash = user.password_hash if user is not None else get_dummy_hash()`. Comment preserved. All other login logic, response shape, token lifetimes, error codes, and rate limiting are unchanged.

4. **`backend/tests/test_auth.py`**
   - Updated module docstring to reference Wave 2 Phase 4 additions.
   - Added `TestProductionConfig` (5 tests): missing DATABASE_URL raises, blank DATABASE_URL raises, valid DATABASE_URL starts cleanly, weak JWT_SECRET_KEY still raises, missing JWT_SECRET_KEY still raises.
   - Added `TestNonexistentUserLoginPath` (4 tests): nonexistent user still returns 401 INVALID_CREDENTIALS, nonexistent user still invokes `check_password_hash` (spy via monkeypatch), `get_dummy_hash()` returns a valid pbkdf2:sha256 hash, `get_dummy_hash()` returns the same object on repeated calls (no per-call churn).

### Commands Run

```
source venv/bin/activate && python -m pytest tests/test_auth.py -v
# Result: 39 passed

source venv/bin/activate && python -m pytest -q
# Result: 370 passed (baseline was 361; +9 new tests)
```

### Tests

- Pre-existing auth suite: 30 tests — all still pass.
- New `TestProductionConfig`: 5 tests — all pass.
- New `TestNonexistentUserLoginPath`: 4 tests — all pass.
- Full backend suite: 370 passed, 0 failed.

### Open Issues / Risks

None. Changes are localized to the targeted files. No shared infrastructure was modified beyond adding a single helper to `utils/auth.py`.

### Next Recommended Step

Delegate to the Testing Agent to finalize regression coverage per the orchestrator's testing delegation prompt. The backend contract is now locked and the 9 new tests already cover the core cases; the testing agent should review and add any additional coverage they deem necessary before closing the phase.
