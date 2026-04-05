# Backend Handoff — Wave 4 Phase 1: Bootstrap, JWT, and Startup Hardening

## Entry 1 — 2026-04-05

### Status

Complete. All three security findings (F-SEC-001, F-SEC-002, F-SEC-003) implemented and verified.

### Scope

- `backend/seed.py` — bootstrap credential hardening (F-SEC-001)
- `backend/app/config.py` — JWT fallback removal and production-as-default (F-SEC-002)
- `backend/run.py` — debug mode hardening (F-SEC-003)
- `README.md` — local-dev-only seed warning

### Docs Read

- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (F-SEC-001, F-SEC-002, F-SEC-003)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-009, DEC-BE-017)
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `README.md`
- `backend/.env.example`
- `backend/seed.py`
- `backend/app/config.py`
- `backend/run.py`
- `backend/tests/test_auth.py`
- `backend/tests/conftest.py`

### Files Changed

| File | Change summary |
|---|---|
| `backend/seed.py` | Removed `admin123`; replaced with `secrets.token_urlsafe(16)`; password printed once on first creation only; updated module docstring with LOCAL DEVELOPMENT ONLY warning and explicit `FLASK_ENV=development` invocation example |
| `backend/app/config.py` | Removed runtime JWT fallback from `_Base.__init__` (now defaults to `""`); changed `get_config()` default from `"development"` to `"production"`; fallback class changed from `Development` to `Production`; updated module docstring; added comment clarifying that `_DEV_DEFAULT_JWT_SECRET` is a constant for `_WEAK_SECRETS`, not a runtime fallback |
| `backend/run.py` | Removed hardcoded `debug=True`; derived debug mode from `os.getenv("FLASK_ENV", "production").lower() == "development"`; updated docstring to reflect production-default behavior |
| `README.md` | Added explicit local-dev-only blockquote warning after the seed step; updated seed command to include `FLASK_ENV=development` prefix |
| `backend/.env.example` | No change needed — already contains `FLASK_ENV=development` and the placeholder JWT value; `Production._WEAK_SECRETS` already rejects that placeholder |

### Commands Run

```
# Verification ripgrep scan
rg -n "admin123|debug=True|dev-local-jwt-secret-change-me-2026" backend README.md

# Test suite
cd backend && venv/bin/python -m pytest tests/test_auth.py -q

# Git diff review
git diff -- backend/seed.py backend/app/config.py backend/run.py backend/.env.example README.md
```

### Tests

- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q` — **49 passed** in 4.98s
- No regressions. All existing `TestProductionConfig` tests (missing/blank DATABASE_URL, weak/missing JWT) continue to pass.

### Bootstrap Credential Path

- `backend/seed.py:_seed_admin()` now generates a password with `secrets.token_urlsafe(16)` on each fresh run.
- The password is passed directly to `generate_password_hash()` and is never stored in code, config, or any file.
- The password is printed once: `[seed] admin user created — password: <value>`.
- On skip/re-run (user already exists): prints `[skip] admin user already exists` — no password emitted.

### What Happens When FLASK_ENV Is Unset

- `get_config()` now resolves to `Production` (was `Development`).
- `Production.__init__()` validates `DATABASE_URL` (must be set and non-blank) and `JWT_SECRET_KEY` (must be present, ≥ 32 characters, not a member of `_WEAK_SECRETS`).
- App startup raises `RuntimeError` before the Flask app finishes initializing if either check fails.
- This means an unattended deployment without env vars now fails loudly rather than silently booting in a permissive development configuration.

### How the Checked-In/Example JWT Placeholder Is Treated in Production

- `backend/.env.example` still contains `JWT_SECRET_KEY=dev-local-jwt-secret-change-me-2026` for local developer convenience.
- `Production._WEAK_SECRETS` explicitly includes `_Base._DEV_DEFAULT_JWT_SECRET` (`"dev-local-jwt-secret-change-me-2026"`), so any production startup that accidentally copies `.env.example` verbatim will immediately raise:
  ```
  RuntimeError: Production requires a strong JWT_SECRET_KEY ...
  ```
- The constant is not used as a runtime fallback anywhere; it exists solely to enable this rejection.

### How Debug Mode Is Now Derived

- `backend/run.py`: `_debug = os.getenv("FLASK_ENV", "production").lower() == "development"`
- Debug is `True` only when `FLASK_ENV` is explicitly `"development"`.
- `Development.DEBUG = True` (class attribute, unchanged).
- `Production.DEBUG = False` (class attribute, unchanged).
- No other config class sets `DEBUG = True`.

### Residual Docs Drift / Out-of-Scope Items

- `stoqio_docs/08_SETUP_AND_GLOBALS.md` and `stoqio_docs/19_IMPLEMENTATION_PLAN.md` still reference `admin123` in historical/instructional text. The orchestrator explicitly scoped this phase to backend + README only; those docs are out of scope for this phase.
- `backend/tests/test_phase9_ops.py` lines 83 and 114 contain `assert "admin123" not in output` — these are correct security-lock assertions, not credential references.
- `backend/app/config.py` line 17 retains the string `"dev-local-jwt-secret-change-me-2026"` as a named constant for `_WEAK_SECRETS`. This is intentional and documented with a comment.
- Testing agent should add regression coverage for: production-as-default env selection, seed output not emitting a known static password, and debug mode off by default.

### Next Recommended Step

Delegate to Testing agent to add regression locks for:
1. `FLASK_ENV` absent → `Production` config is selected (not `Development`)
2. Seed output contains a random token (not `admin123`) on first creation; no password on skip
3. Debug mode is `False` when `FLASK_ENV` is not `development`
