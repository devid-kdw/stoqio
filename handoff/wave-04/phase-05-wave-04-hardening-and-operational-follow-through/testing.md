## 2026-04-08 08:41 CEST

### Status
Blocked on two Phase 5 contract findings after targeted testing.

### Scope
Added regression coverage for Wave 4 Phase 5 security hardening contracts across
login throttling, security headers, backend dependency lock presence, `.gitignore`
coverage, setup-status authorization, and deploy-time npm audit gating.

### Docs Read
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/__init__.py`
- `backend/app/api/setup/routes.py`
- `backend/app/models/login_attempt.py`
- `backend/migrations/versions/a9f1b2c3d4e5_add_login_attempt_table.py`
- `backend/requirements.lock`
- `scripts/deploy.sh`
- `.gitignore`
- `frontend/package.json`
- `frontend/package-lock.json`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`

### Files Changed
- `backend/tests/test_wave4_phase5_security.py`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`

### Commands Run
- `venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q`
- `bash -n scripts/build.sh`
- `bash -n scripts/deploy.sh`
- `venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q`
- `npm audit --audit-level=high`
- `npm audit --audit-level=high` with escalated network access after the sandbox run failed with `getaddrinfo ENOTFOUND registry.npmjs.org`
- `git log --all --full-history --oneline -- '.env' '.env.*' '*.pem' '*.key' '*.p12' '*.pfx' '*credentials*' '*secrets*'`
- `rg -n '"vite"|vite' frontend/package.json frontend/package-lock.json | head -n 20`
- `git status --short`
- `date '+%Y-%m-%d %H:%M %Z'`

### Tests
- `venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q` passed: `7 passed in 1.47s`.
- `bash -n scripts/build.sh` passed.
- `bash -n scripts/deploy.sh` passed.
- `venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q` passed: `87 passed in 7.72s`.

Coverage now locked:
- `F-SEC-010`: same username from different IPs is throttled; login attempts are persisted in the `login_attempt` table for IP and username buckets.
- `F-SEC-011`: API responses include CSP, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `X-Content-Type-Options: nosniff`.
- `F-SEC-012`: `backend/requirements.lock` exists, contains pinned `==` requirements, and `scripts/deploy.sh` references `requirements.lock`.
- `F-SEC-013`: `.gitignore` covers `.env.*`, key/cert containers, logs, diagnostic output, `secrets.json`, and `credentials.json`.
- `F-SEC-014`: unauthenticated `/api/v1/setup/status` returns `401`; an active authenticated user still receives the setup-status payload.
- `F-SEC-015`: `scripts/deploy.sh` includes `npm audit --audit-level=high`.

Manual/operational verification:
- Git-history secret artifact check returned no matches for the requested `.env`, key/cert, credentials, or secrets pathspecs.
- Initial sandbox `npm audit --audit-level=high` failed with `getaddrinfo ENOTFOUND registry.npmjs.org`.
- Escalated `npm audit --audit-level=high` reached the registry and failed with one high-severity vulnerability:
  - `vite 7.0.0 - 7.3.1`
  - Advisories reported: `GHSA-4w7w-66w2-5vf9`, `GHSA-v2wj-q39q-566r`, `GHSA-p9ff-h696-f583`
  - npm reported `fix available via npm audit fix`
  - current repo reference: `frontend/package.json` uses `"vite": "^7.3.1"`

### Open Issues / Risks
- Blocker: `npm audit --audit-level=high` does not pass. Phase 5 requires high/critical findings to be fixed or documented; this is an actual high finding after escalated registry access, not a sandbox-only failure.
- Blocker: `scripts/deploy.sh` still falls back to `requirements.txt` when `backend/requirements.lock` is missing. That weakens the `F-SEC-012` reproducible deploy contract that deploy should install from the lock file rather than directly from `requirements.txt`.
- Process gap: `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md` was still absent during the testing pass, so backend implementation details were verified from source and orchestrator context instead of backend handoff.
- The new tests intentionally do not auto-fail on the deploy fallback blocker because testing ownership excludes changing deploy behavior; the blocker is recorded here for backend/orchestrator follow-up.

### Next Recommended Step
Assign follow-up to the appropriate implementation owner to update the vulnerable Vite dependency/lockfile until `npm audit --audit-level=high` exits `0`, remove or hard-fail the `requirements.lock` missing fallback in `scripts/deploy.sh`, and add the missing backend handoff before orchestrator closeout.

## 2026-04-08 09:02 CEST

### Status
Accepted after final follow-up verification.

### Scope
Verified the backend/deploy and frontend dependency follow-up fixes that resolved the prior Phase 5 blockers. Added one narrow regression assertion so `scripts/deploy.sh` cannot reintroduce a fallback to `requirements.txt` when `requirements.lock` is missing.

### Docs Read
- `handoff/README.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`
- `backend/tests/test_wave4_phase5_security.py`
- `scripts/deploy.sh`
- `frontend/package.json`
- `frontend/package-lock.json`

### Files Changed
- `backend/tests/test_wave4_phase5_security.py`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`

### Commands Run
- `git status --short`
- `sed -n '1,260p' backend/tests/test_wave4_phase5_security.py`
- `sed -n '1,220p' handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`
- `sed -n '30,70p' scripts/deploy.sh`
- `venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q`
- `venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q`
- `bash -n scripts/build.sh`
- `bash -n scripts/deploy.sh`
- `npm audit --audit-level=high`
- `npm audit --audit-level=high` with escalated network access after sandbox DNS failed with `getaddrinfo ENOTFOUND registry.npmjs.org`
- `git diff --check`
- `rg -n '"vite"|node_modules/vite|"version": "7\.3\.2"' frontend/package.json frontend/package-lock.json`
- `date '+%Y-%m-%d %H:%M %Z'`

### Tests
- `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q` passed: `7 passed in 1.72s`.
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q` passed: `87 passed in 8.89s`.
- `bash -n scripts/build.sh` passed.
- `bash -n scripts/deploy.sh` passed.
- Sandbox `cd frontend && npm audit --audit-level=high` failed only because registry DNS was blocked: `getaddrinfo ENOTFOUND registry.npmjs.org`.
- Escalated `cd frontend && npm audit --audit-level=high` passed: `found 0 vulnerabilities`.
- `git diff --check` passed.

Final follow-up checks:
- `backend.md` exists and contains the required handoff sections.
- `scripts/deploy.sh` now hard-fails when `backend/requirements.lock` is missing and no longer contains a `requirements.txt` install fallback.
- `backend/tests/test_wave4_phase5_security.py` now asserts the deploy script uses `requirements.lock`, does not install `-r requirements.txt`, does not contain `falling back`, and includes the hard-fail message.
- Vite is updated to `^7.3.2` in `frontend/package.json`; `frontend/package-lock.json` resolves `node_modules/vite` to `7.3.2`.
- The prior high-severity Vite audit finding is resolved.

### Open Issues / Risks
None for Phase 5 acceptance. The only non-green sandbox result was the expected npm registry DNS block, and the escalated audit completed successfully with `found 0 vulnerabilities`.

### Next Recommended Step
Orchestrator can mark Wave 4 Phase 5 accepted.
