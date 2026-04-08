## 2026-04-08 08:45 CEST

### Status
Completed backend/deploy follow-up for the Phase 5 `F-SEC-012` blocker. Backend handoff gap is now filled.

### Scope
Removed the non-reproducible deploy fallback from `scripts/deploy.sh` and documented the observable backend Phase 5 implementation that had already landed in the worktree.

Observable Phase 5 backend/deploy implementation already present:
- `F-SEC-010`: login throttling is DB-backed through `LoginAttempt`, with per-IP and per-normalized-username buckets.
- `F-SEC-011`: Flask responses receive CSP, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Content-Type-Options: nosniff`.
- `F-SEC-012`: `backend/requirements.lock` exists and deploy now installs from it.
- `F-SEC-013`: `.gitignore` includes broader env, key/cert, log, diagnostic output, and common credential artifact patterns.
- `F-SEC-014`: `GET /api/v1/setup/status` is auth-guarded with the standard active-user role path while preserving the same response payload.
- `F-SEC-015`: `scripts/deploy.sh` includes `npm audit --audit-level=high`; frontend dependency follow-up still owns clearing the current Vite audit finding.

Follow-up change in this pass:
- `scripts/deploy.sh` now hard-fails if `backend/requirements.lock` is missing instead of falling back to `requirements.txt`.

### Docs Read
- `handoff/README.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`
- `scripts/deploy.sh`
- `backend/requirements.lock`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/__init__.py`
- `backend/app/api/setup/routes.py`
- `backend/app/models/login_attempt.py`
- `backend/migrations/versions/a9f1b2c3d4e5_add_login_attempt_table.py`

### Files Changed
- `scripts/deploy.sh`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`

### Commands Run
- `sed -n '1,120p' scripts/deploy.sh`
- `sed -n '1,220p' handoff/README.md`
- `test -f handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md && sed -n '1,220p' handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md || true`
- `git status --short`
- `date '+%Y-%m-%d %H:%M %Z'`
- `bash -n scripts/deploy.sh`
- `venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q`
- `git diff -- scripts/deploy.sh`
- `git status --short -- scripts/deploy.sh handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`

### Tests
- `bash -n scripts/deploy.sh` passed.
- `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q` passed: `7 passed in 1.76s`.

### Open Issues / Risks
- `npm audit --audit-level=high` was not fixed in this backend/deploy pass. The frontend dependency follow-up owns the Vite audit blocker.
- Final testing should verify that the deploy fallback is gone with an explicit assertion if needed.

### Next Recommended Step
Run the frontend dependency follow-up for the Vite audit finding, then run final testing for Phase 5 acceptance.
