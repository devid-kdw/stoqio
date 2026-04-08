## Phase Summary

Phase
- Wave 6 - Phase 4 - Infrastructure and Developer Practice Hardening

Objective
- Remediate infrastructure and developer-practice findings from the 2026-04-08 review:
  V-6 (password hashing upgrade from pbkdf2 to scrypt with lazy migration),
  V-10 (deploy.sh no rollback capability),
  V-11 (deploy.sh sudo restart without success verification),
  S-10 (seed.py no programmatic production guard),
  S-12 (npm audit blocks only high/critical — not moderate),
  N-7 (no security-focused ESLint plugin),
  N-9 (source maps not explicitly disabled in production Vite build).

Source Docs
- `handoff/README.md`
- `handoff/wave-06/README.md`
- `handoff/decisions/decision-log.md`
- `scripts/deploy.sh`
- `scripts/build.sh`
- `backend/seed.py`
- `backend/app/services/settings_service.py` (password hashing)
- `backend/app/utils/auth.py` (dummy hash generation)
- `frontend/vite.config.ts`
- `frontend/eslint.config.js`
- `frontend/package.json`
- `backend/requirements.txt`
- `backend/requirements.lock`

Current Repo Reality
- `settings_service.py` and `utils/auth.py` both use `method="pbkdf2:sha256"` explicitly.
  Werkzeug 3.x supports `scrypt` natively (no extra dependency). Existing password hashes
  use pbkdf2 and cannot be rehashed without the plaintext. Lazy migration (rehash on login)
  is the correct approach.
- `deploy.sh` has no rollback step. If migration or build fails mid-deploy, the system is
  left in an inconsistent state. No previous version is preserved.
- `deploy.sh` line 72: `sudo systemctl restart wms` — no verification that the service
  actually came up. Script can exit 0 even if the service crashed on start.
- `seed.py` has only a comment warning about production. No programmatic check prevents
  accidental production runs.
- `deploy.sh` runs `npm audit --audit-level=high`, allowing moderate vulnerabilities through.
- Frontend `eslint.config.js` has no security-focused plugin.
- `vite.config.ts` does not explicitly disable source maps for production builds.

Contract Locks / Clarifications
- **Password hashing**: Do NOT use argon2 (requires argon2-cffi dependency). Use
  `method="scrypt"` which is built into werkzeug 3.x / Python 3.10+. The lazy migration
  approach: in the login flow, after `check_password_hash` succeeds, check if the stored
  hash starts with `"pbkdf2:"`. If so, rehash with scrypt and update the stored hash.
  The dummy hash in `utils/auth.py` must also be updated to use scrypt.
  This requires a DEC-SEC-002 decision log entry.
- **deploy.sh rollback**: Add git stash/tag before deploy and restore on failure. Minimum:
  `set -e` at top of script so it aborts on any failure. Add `sudo systemctl is-active wms`
  check after restart. Do NOT introduce complex state machines — keep it shell-simple.
- **seed.py protection**: Add a check at the top that reads `DATABASE_URL` and aborts
  if it does NOT contain `localhost`, `127.0.0.1`, or `wms_dev` in the URL. Print a
  clear error. This is a heuristic guard, not a perfect solution, but prevents accidental
  production runs.
- **npm audit level**: Change `--audit-level=high` to `--audit-level=moderate` in deploy.sh.
  Update the surrounding comment to reflect this.
- **ESLint security plugin**: The package `eslint-plugin-security` must be MANUALLY
  installed by the user (`npm install --save-dev eslint-plugin-security` in frontend/).
  The agent should update `eslint.config.js` to add the plugin config, and add the
  install command to `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`
  under "Commands Run" so the user knows to run it manually. Per DEC-FE-001, agents
  cannot install npm packages directly.
- **Source maps**: In `vite.config.ts`, add `build: { sourcemap: false }` to explicitly
  disable source maps in the production build (development mode keeps source maps).
- Do NOT change CI/CD pipelines or add new system services.

Delegation Plan
- Backend:
  - Update `settings_service.py` password hashing to scrypt with lazy migration on login
  - Update `utils/auth.py` dummy hash to use scrypt
  - Update `scripts/deploy.sh`: add `set -e`, service health check, rollback on failure,
    and change npm audit level to moderate
  - Update `backend/seed.py` with programmatic production guard
  - Update `backend/requirements.txt` and `requirements.lock` if any change needed
  - Add DEC-SEC-002 to decision log
  - Document in `backend.md`
- Frontend:
  - Update `frontend/vite.config.ts` to disable production source maps
  - Update `frontend/eslint.config.js` to include eslint-plugin-security config
    (note: user must install the package manually)
  - Document in `frontend.md` including the manual npm install command

Acceptance Criteria
- New passwords are hashed with scrypt (stored hash starts with `"scrypt:"`)
- Existing pbkdf2 hashes still validate correctly via `check_password_hash`
- A user whose pbkdf2 hash is rehashed on login: subsequent logins also succeed
- `deploy.sh` has `set -e` and exits non-zero on any step failure
- `deploy.sh` verifies service is active after restart (`systemctl is-active`)
- `seed.py` refuses to run if DATABASE_URL does not look like a dev database
- `npm audit --audit-level=moderate` in deploy.sh (not high)
- `vite.config.ts` has `sourcemap: false` under `build`
- `eslint.config.js` imports and applies `eslint-plugin-security` (or documents manual step)
- All pre-existing backend tests pass
- `npm run build` passes
- DEC-SEC-002 added to decision log
- Handoff files follow the required section shape

Validation Notes
- 2026-04-08: Orchestrator created Wave 6 Phase 4 handoff. Runs in parallel with Phases 1-3.
- 2026-04-08 10:45 CEST: Backend + frontend agents completed all fixes. Backend: scrypt upgrade, deploy.sh hardening (health check + moderate audit), seed.py guard. Frontend: sourcemap: false in vite.config.ts, eslint-plugin-security commented config (manual install required per DEC-FE-001). Full backend suite: 567 passed. Frontend build ✓, 41/41 tests ✓. Phase 4 closed (pending user running: npm install --save-dev eslint-plugin-security + uncommenting 2 lines in eslint.config.js).

Next Action
- Backend and frontend agents implement in parallel. Can run simultaneously with Phases 1, 2, 3.


---

## Delegation Prompt — Backend Agent

You are the infrastructure and backend hardening agent for Wave 6 Phase 4 of the STOQIO WMS
project. This phase runs in parallel with other Wave 6 phases.

Read before coding:
- `handoff/README.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`
- `handoff/decisions/decision-log.md`
- `backend/app/services/settings_service.py` (find password hash calls)
- `backend/app/utils/auth.py` (find dummy hash and check_password_hash usage)
- `backend/app/api/auth/routes.py` (find login flow to add lazy rehash)
- `backend/seed.py`
- `scripts/deploy.sh`
- `backend/requirements.txt`

Your fixes (implement all of them):

1. **Password hashing upgrade to scrypt** (multiple files)
   a. In `backend/app/services/settings_service.py`: change `method="pbkdf2:sha256"` to
      `method="scrypt"` in `generate_password_hash()` calls.
   b. In `backend/app/utils/auth.py`: change the `_DUMMY_HASH` generation to use scrypt:
      `_DUMMY_HASH = generate_password_hash("dummy-placeholder", method="scrypt")`
   c. In `backend/app/api/auth/routes.py` login function: after `check_password_hash`
      succeeds and user is verified, add lazy rehash:
      ```python
      # Lazy migration: upgrade pbkdf2 hashes to scrypt on successful login
      if user.password_hash.startswith("pbkdf2:"):
          user.password_hash = generate_password_hash(password, method="scrypt")
          db.session.commit()
      ```
      Import `generate_password_hash` from werkzeug.security if not already imported.
   d. Add DEC-SEC-002 to `handoff/decisions/decision-log.md` (append at end):
      ```
      ## DEC-SEC-002
      - Date: 2026-04-08
      - Phase: phase-04-wave-06-infrastructure-hardening
      - Source: 2026-04-08 security code review finding V-6
      - Decision: Password hashing is upgraded from pbkdf2:sha256 to scrypt (werkzeug built-in,
        no new dependency). New passwords are hashed with scrypt immediately. Existing pbkdf2
        hashes are lazily migrated to scrypt on first successful login. The dummy hash for
        timing-safe nonexistent-user checks also uses scrypt. argon2-cffi is not introduced
        because it requires an additional dependency and scrypt meets the memory-hard requirement.
      - Impact: Future password changes and new user creation use scrypt. Agents must not
        reintroduce method="pbkdf2:sha256" in any password hashing call.
      - Docs update required: no
      ```

2. **deploy.sh hardening** (`scripts/deploy.sh`)
   a. Add `set -euo pipefail` as the FIRST non-comment line of the script.
   b. After `sudo systemctl restart wms`, add:
      ```bash
      sleep 2
      if ! sudo systemctl is-active --quiet wms; then
          echo "ERROR: wms service failed to start after restart. Check: sudo journalctl -u wms -n 50"
          exit 1
      fi
      echo "Service wms is active."
      ```
   c. Change `--audit-level=high` to `--audit-level=moderate` in the npm audit command.
   d. Keep all existing deploy logic intact. Do NOT add complex rollback state machines.

3. **seed.py production guard** (`backend/seed.py`)
   At the very top of the script (after imports, before any DB operations), add:
   ```python
   import os
   _db_url = os.environ.get("DATABASE_URL", "")
   _safe_patterns = ("localhost", "127.0.0.1", "wms_dev", "test")
   if not any(p in _db_url for p in _safe_patterns):
       print("ERROR: seed.py is for LOCAL DEVELOPMENT ONLY.")
       print(f"DATABASE_URL does not look like a dev database: {_db_url[:50]}...")
       print("Aborting to prevent accidental production data corruption.")
       raise SystemExit(1)
   ```
   Place this check BEFORE the Flask app context is used (but after imports and env loading).

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Verify: `bash -n scripts/deploy.sh` (syntax check)
- Write your entry in `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`


---

## Delegation Prompt — Frontend Agent

You are the frontend hardening agent for Wave 6 Phase 4 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`
- `handoff/decisions/decision-log.md` (DEC-FE-001 about npm install restriction)
- `frontend/vite.config.ts`
- `frontend/eslint.config.js`
- `frontend/package.json`

Your fixes:

1. **Disable production source maps** (`frontend/vite.config.ts`)
   In the `defineConfig` export, add or update the `build` object:
   ```typescript
   build: {
     sourcemap: false,
     // ... keep any existing build options
   }
   ```
   Source maps remain available in development mode (they are off by default in prod builds,
   but this makes it explicit and protects against future config changes).

2. **ESLint security plugin** (`frontend/eslint.config.js`)
   Add `eslint-plugin-security` configuration. Because agents cannot install npm packages
   (DEC-FE-001), you MUST:
   a. Add the import and config to `eslint.config.js` using `// @ts-ignore` or conditional
      require so the file does not crash if the package is not yet installed.
   b. In `frontend.md` under "Commands Run", add the instruction:
      ```
      # User must run manually (agents cannot install npm packages):
      cd frontend && npm install --save-dev eslint-plugin-security
      ```
   The eslint.config.js update should look like:
   ```typescript
   import security from 'eslint-plugin-security'
   // ... in the config array:
   security.configs.recommended,
   ```
   Use the flat config format (this project uses ESLint 9 flat config).

After all changes:
- Run: `cd frontend && npm run build`
- Run: `cd frontend && npm run lint` (may fail if package not installed — document this)
- Write your entry in `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
