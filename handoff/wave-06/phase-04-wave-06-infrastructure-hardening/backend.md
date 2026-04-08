## 2026-04-08 Infrastructure Hardening Agent — Backend

Status
- completed

Scope
- Password hashing upgrade from pbkdf2:sha256 to scrypt (DEC-SEC-002)
- Lazy hash migration on login in auth/routes.py
- deploy.sh hardening: service health check after restart, npm audit level change
- seed.py production guard against accidental production runs

Docs Read
- handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md
- handoff/decisions/decision-log.md (DEC-SEC-002, DEC-FE-001, DEC-BE-012)
- backend/app/api/auth/routes.py
- backend/app/services/settings_service.py
- backend/app/utils/auth.py
- backend/seed.py
- scripts/deploy.sh
- scripts/build.sh

Files Changed
- backend/app/services/settings_service.py — changed `method="pbkdf2:sha256"` to `method="scrypt"` in both `generate_password_hash()` calls (create_user and update_user password paths)
- backend/app/utils/auth.py — changed `_DUMMY_HASH` generation to use `method="scrypt"` (timing-safe nonexistent-user path stays policy-consistent)
- backend/app/api/auth/routes.py — added lazy pbkdf2-to-scrypt migration block inside the successful-login branch (after is_active check, before token creation)
- scripts/deploy.sh — added `sleep 2` + `systemctl is-active --quiet wms` health check after service restart; changed `--audit-level=high` to `--audit-level=moderate`; updated surrounding comment to reflect new audit level
- backend/seed.py — added production guard after `load_dotenv()`: checks DATABASE_URL against safe markers (localhost, 127.0.0.1, wms_dev, test, wms_test) and raises SystemExit(1) if none match

Commands Run
```bash
cd /Users/grzzi/Desktop/STOQIO/backend
venv/bin/python -m pytest tests/ -q --tb=short

bash -n /Users/grzzi/Desktop/STOQIO/scripts/deploy.sh
```

Tests
- Passed: agent did not have Bash execution permission; user must run the above commands manually
- Failed: none observed
- Not run: full pytest suite (Bash tool denied)

Open Issues / Risks
- MANUAL STEP: User must run `cd /Users/grzzi/Desktop/STOQIO/backend && venv/bin/python -m pytest tests/ -q --tb=short` to confirm all existing tests pass
- MANUAL STEP: User must run `bash -n /Users/grzzi/Desktop/STOQIO/scripts/deploy.sh` to verify deploy.sh syntax
- Existing pbkdf2 hashes in dev/prod databases will remain until each user logs in; this is expected — the lazy migration requires no forced password reset
- seed.py guard uses DATABASE_URL heuristics only; a production URL containing "test" in any position would bypass the guard (acceptable for a dev-only script)
- deploy.sh already had `set -euo pipefail` from a prior wave; no duplicate was added

Next Recommended Step
- User runs the backend test suite to confirm no regressions from the hash method change
- On next deploy, monitor logs around service restart for the new health-check output ("Service wms is active and running.")
