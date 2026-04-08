## Phase Summary

Phase
- Wave 4 - Phase 5 - Hardening and Operational Follow-Through

Objective
- Close the remaining medium- and low-severity security hardening gaps from the security review without changing core warehouse product behavior.
- This phase covers:
- `F-SEC-010` — durable login throttling
- `F-SEC-011` — browser security headers for the deliberate `localStorage` refresh-token design
- `F-SEC-012` — pinned backend Python deploy lock file
- `F-SEC-013` — expanded repository secret/artifact ignore coverage
- `F-SEC-014` — setup-state disclosure decision or restriction
- `F-SEC-015` — deploy-time `npm audit` high/critical gate

Source Docs
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-010`, `F-SEC-011`, `F-SEC-012`, `F-SEC-013`, `F-SEC-014`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-001`, `DEC-FE-006`)
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/orchestrator.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/__init__.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/api/setup/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_setup.py`
- `backend/tests/test_phase9_ops.py`
- `frontend/src/store/authStore.ts`
- `frontend/src/api/setup.ts`
- `frontend/src/utils/setup.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `backend/requirements.txt`
- `scripts/build.sh`
- `scripts/deploy.sh`
- `.gitignore`
- `frontend/package.json`
- `frontend/package-lock.json`

Current Repo Reality
- Wave 4 Phase 4 is accepted and is the current baseline.
- `F-SEC-010` current state:
- `backend/app/utils/auth.py` still uses an in-memory sliding-window limiter keyed only by IP address.
- `backend/app/api/auth/routes.py` still calls `check_rate_limit(ip)` before login processing, so throttle state does not survive process restarts and does not aggregate by username/account.
- Existing auth tests already lock the current same-IP `429 RATE_LIMITED` behavior in `backend/tests/test_auth.py`.
- `F-SEC-011` current state:
- `frontend/src/store/authStore.ts` still deliberately persists the refresh token in `localStorage` under `stoqio_refresh_token` (accepted baseline from `DEC-FE-006`).
- `backend/app/__init__.py` does not currently attach response-hardening headers such as CSP, `X-Frame-Options`, `Referrer-Policy`, or `X-Content-Type-Options`.
- There is no nearby code comment linking the `localStorage` decision to compensating server-side controls.
- `F-SEC-012` current state:
- `backend/requirements.txt` remains version-ranged only.
- No pinned backend lock file exists today.
- `scripts/deploy.sh` still installs backend dependencies directly from `requirements.txt`.
- `F-SEC-013` current state:
- `.gitignore` ignores `backend/.env` and a few runtime/build directories, but not broader secret-bearing patterns such as `.env.*`, `*.pem`, or common credential dump files.
- No current repo artifact records a one-time secret-history check result.
- `F-SEC-014` current state:
- `backend/app/api/setup/routes.py` still exposes `GET /api/v1/setup/status` without authentication.
- Frontend callsites appear to be post-auth only:
- `LoginPage.tsx` calls `fetchSetupStatus()` only after successful login and auth-store hydration
- `SetupGuard.tsx` runs inside protected routing
- `SetupPage.tsx` redirects to `/login` unless auth is already present
- That means restricting `/setup/status` to authenticated users looks likely feasible, but it still needs real verification.
- `F-SEC-015` current state:
- `scripts/build.sh` runs `npm ci --no-audit --no-fund` before the frontend build.
- `scripts/deploy.sh` does not run `npm audit` at all today.
- `frontend/package-lock.json` already exists, so the missing piece is the audit/review/gate rather than lockfile generation.
- Known environment constraint from `DEC-FE-001` still applies:
- npm registry/network-backed commands may fail in the agent sandbox with DNS/network errors.
- If `npm audit` cannot run in sandbox, agents must not fake a green result; they must record the exact failure and use the approved escalation/manual-terminal path if needed.

Contract Locks / Clarifications
- Do not change auth route URLs, auth response shapes, JWT lifetimes, refresh semantics, or the deliberate choice to keep refresh tokens in `localStorage` in this phase.
- Do not migrate to `HttpOnly` cookies in this phase.
- Do not introduce Redis or other new infrastructure requirements for throttling; the existing database is acceptable.
- Keep throttle behavior in the same general product shape:
- still return the existing `RATE_LIMITED` API error contract
- do not add new user-facing lockout flows or password-reset side effects
- `requirements.txt` remains the human-readable source file. The new pinned lock file is the deploy-time artifact, not a replacement for `requirements.txt`.
- Do not rewrite git history in this phase.
- If the history check reveals genuine credential material:
- do not guess about rotating external/live secrets you cannot control from the repo
- record the exact finding in handoff
- only rotate repo-controlled development placeholders if that can be done safely and explicitly
- For `npm audit`, high and critical findings should block deploy. Low and moderate findings should not.
- No broad frontend redesign is in scope. Frontend changes should stay narrow to auth-storage commentary and any truly necessary setup-status compatibility adjustment.

Delegation Plan
- Backend:
- own the throttle, headers, lockfile, deploy-script, `.gitignore`, history-check, and setup-status decision/implementation work
- Frontend:
- own the `authStore.ts` security-awareness comment and only any minimal setup-status compatibility tweak if backend restriction reveals a real frontend dependency
- Testing:
- lock the backend/frontend/deploy contracts with targeted regression coverage and verification

Acceptance Criteria
- Login throttling is no longer process-local IP-only; it is persisted/shared and also enforces an account/username bucket.
- Throttle limit/window values are easy to find as named constants.
- API responses include at minimum:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Content-Type-Options: nosniff`
- The localStorage refresh-token design is explicitly documented in code as a deliberate tradeoff with compensating headers.
- A pinned backend Python lock file exists and `scripts/deploy.sh` installs from it instead of directly from `requirements.txt`.
- `scripts/deploy.sh` documents that the lock file must be regenerated and committed whenever backend dependencies change.
- `.gitignore` covers the requested secret-bearing and operational artifact patterns.
- A one-time git-history secret/artifact check has been performed and documented in handoff.
- `GET /api/v1/setup/status` is either:
- auth-guarded with the frontend still working correctly
- or left public with an explicit decision comment documenting that accepted tradeoff
- `scripts/deploy.sh` runs `npm audit --audit-level=high` and fails deploy on high/critical frontend vulnerabilities.
- `npm audit` findings are either fixed or explicitly documented if the environment blocked execution.
- New or updated tests pass and the phase leaves complete backend + frontend + testing + orchestrator handoff trail.

Validation Notes
- Orchestrator backend review after backend delivery on 2026-04-08:
- `git status --short` showed backend/deploy/repo-hygiene changes plus `backend/requirements.lock`, `backend/app/models/login_attempt.py`, and `backend/migrations/versions/a9f1b2c3d4e5_add_login_attempt_table.py`.
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md` was not present at review time. Treat this as a handoff/process gap until backend records the required work log.
- Source review confirmed DB-backed `LoginAttempt` throttle state, per-IP plus per-normalized-username login buckets, response security headers, `/setup/status` auth guard, expanded `.gitignore`, `requirements.lock`, and an `npm audit --audit-level=high` deploy step.
- Targeted verification run by orchestrator:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py -q` -> `71 passed`
- `bash -n scripts/deploy.sh` -> passed
- `git diff --check` -> passed
- `git log --all --full-history --oneline -- '.env' '.env.*' '*.pem' '*.key' '*.p12' '*.pfx' '*credentials*' '*secrets*'` -> no matches
- Caveat: `scripts/deploy.sh` installs from `requirements.lock` when present but falls back to `requirements.txt` if the lock file is missing. Testing should validate this against the `F-SEC-012` reproducible deploy contract and record a blocker if this is judged non-compliant.
- Frontend agent spawned as `Mill` for the `authStore.ts` localStorage comment and setup-status compatibility audit.
- Testing agent spawned as `Kuhn` for regression coverage and operational verification, with the backend handoff gap and deploy fallback caveat called out explicitly.
- Frontend handoff completed on 2026-04-08: only `frontend/src/store/authStore.ts` was changed with the required refresh-token storage comment. No setup/auth runtime change was needed because the existing authenticated flow remains compatible with the backend-authenticated `/setup/status`.
- Testing handoff completed on 2026-04-08: new `backend/tests/test_wave4_phase5_security.py` coverage was added for username throttling across IPs, persisted login attempts, security headers, lock-file/deploy reference, `.gitignore` secret coverage, `/setup/status` auth guard, and deploy `npm audit --audit-level=high` presence.
- Testing verification passed:
- `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q` -> `7 passed`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q` -> `87 passed`
- `bash -n scripts/build.sh` -> passed
- `bash -n scripts/deploy.sh` -> passed
- Phase 5 remains blocked, not accepted:
- `npm audit --audit-level=high` reached the registry after escalation and failed with one high-severity Vite finding for `vite 7.0.0 - 7.3.1`; this repo currently uses `"vite": "^7.3.1"`.
- `scripts/deploy.sh` still falls back to `requirements.txt` when `requirements.lock` is missing, which weakens the `F-SEC-012` reproducible deploy contract.
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md` is still missing.

Next Action
- Assign follow-up to the appropriate implementation owner before closeout:
- update the vulnerable Vite dependency/lockfile until `npm audit --audit-level=high` exits `0`
- remove or hard-fail the deploy fallback to `requirements.txt` when `requirements.lock` is missing
- add the missing backend handoff for this phase

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-010`, `F-SEC-011`, `F-SEC-012`, `F-SEC-013`, `F-SEC-014`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-001`, `DEC-FE-006`)
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/orchestrator.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/__init__.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/api/setup/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_setup.py`
- `backend/tests/test_phase9_ops.py`
- `frontend/src/store/authStore.ts`
- `frontend/src/api/setup.ts`
- `frontend/src/utils/setup.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `backend/requirements.txt`
- `scripts/build.sh`
- `scripts/deploy.sh`
- `.gitignore`
- `frontend/package.json`
- `frontend/package-lock.json`

Goal
- Close the remaining backend/deploy/repo-hygiene hardening gaps from `F-SEC-010` through `F-SEC-015` without changing accepted auth/session product behavior.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend/deploy/repo-hygiene files plus `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`.
- Do not edit frontend product files unless a truly unavoidable compatibility fix is required for the `/setup/status` decision; if that happens, document it clearly and keep the write set minimal.
- Prefer leaving test-file changes to the testing agent unless a tiny backend-owned regression test is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- `check_rate_limit(...)` is still process-local and IP-only in `backend/app/utils/auth.py`.
- `frontend/src/store/authStore.ts` still deliberately persists the refresh token in `localStorage`; this phase adds compensating controls and commentary, not a storage migration.
- No response-hardening header layer exists in `backend/app/__init__.py`.
- No backend dependency lock file exists yet.
- `.gitignore` is intentionally narrow today.
- `/setup/status` is still public, but current frontend callsites look post-auth, so auth-guarding appears feasible if verified carefully.
- `scripts/deploy.sh` currently installs from `requirements.txt` and does not run `npm audit`.
- npm/network-backed commands may hit the known sandbox limitation from `DEC-FE-001`; if that happens, do not claim success you did not observe.

Non-Negotiable Contract Rules
- Do not change login route URLs, response bodies, or the existing `RATE_LIMITED` error code/message shape unless absolutely required to preserve compatibility.
- Do not change refresh-token storage mechanics in this phase.
- Do not introduce Redis or other new infrastructure requirements.
- Do not remove `requirements.txt`.
- Do not rewrite git history.
- Keep the implementation readable and operationally practical for local-host deploys.

Tasks
1. `F-SEC-010` — login throttling hardening:
- Replace the current process-local IP-only throttle with a durable/shared design backed by the existing database (or an equivalent shared store already present in the repo).
- Enforce both:
- per-IP throttling
- per-normalized-username/account throttling
- Keep throttle tuning values as clearly named constants.
- Keep the existing login contract and error shape; this is hardening of backing store/scope, not a UX redesign.
- If schema changes are needed, add a migration from the current head revision.
2. `F-SEC-011` — browser security headers:
- Add a response-hardening layer in `backend/app/__init__.py` that sets at minimum:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Content-Type-Options: nosniff`
- Use a practical CSP baseline that does not break the current Vite/React/Mantine SPA. If a narrowly scoped allowance such as style `'unsafe-inline'` is required for compatibility, document why.
- Add a short code comment in `backend/app/__init__.py` or another tightly related touched file stating that the persisted refresh-token-in-`localStorage` design is deliberate in the current baseline and that these headers are the compensating browser hardening control for now.
3. `F-SEC-012` — Python dependency locking:
- Create a pinned backend lock file for deploy use. Prefer `backend/requirements.lock`.
- `requirements.txt` remains the source file; the lock file is the deploy artifact.
- Use `pip-compile` if it is already available or another equivalent method that produces a fully pinned lock from the current dependency set without inventing new product dependencies just to create the lock.
- Update `scripts/deploy.sh` to install backend dependencies from the lock file instead of directly from `requirements.txt`.
- Add a concise comment in `scripts/deploy.sh` explaining that the lock file must be regenerated and committed whenever backend dependencies change.
4. `F-SEC-013` — `.gitignore` and history check:
- Expand `.gitignore` to cover at minimum:
- `.env.*`
- `*.key`, `*.pem`, `*.p12`, `*.pfx`
- diagnostic output files such as `*.log`, `diagnostic_output*.txt`
- common secret file names such as `secrets.json`, `credentials.json`
- Perform a one-time git-history check for previously committed env/credential artifacts.
- Do not rewrite history.
- Record the exact result in handoff.
- If you find actual committed secret material you cannot safely rotate from within the repo, record it clearly as a finding/blocker rather than guessing.
5. `F-SEC-014` — setup-state disclosure:
- Audit the frontend callsites listed above.
- Prefer restricting `GET /api/v1/setup/status` to authenticated users if the current frontend flow still works correctly.
- If you restrict it, keep the response payload unchanged and verify the frontend flow remains compatible.
- If you determine it must remain public, leave the runtime behavior unchanged but add an explicit decision comment in `backend/app/api/setup/routes.py` explaining why that public disclosure is currently accepted for STOQIO's deployment model.
6. `F-SEC-015` — npm audit deploy gate:
- Run `npm audit --audit-level=high` in `frontend/` and review the result.
- Fix or document any high/critical findings.
- Update `scripts/deploy.sh` so deploy runs `npm audit --audit-level=high` and fails on high/critical findings.
- Low/moderate findings must not block deploy.
- If `npm audit` fails only because of the known sandbox/DNS/network limitation, record the exact failure and use the approved manual/escalated path instead of claiming a green audit result.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py -q`
- `bash -n scripts/build.sh && bash -n scripts/deploy.sh`
- `rg -n "check_rate_limit|RATE_LIMITED|Content-Security-Policy|X-Frame-Options|Referrer-Policy|requirements.lock|npm audit|setup/status|LOCAL SUPPORT TOOL ONLY" backend scripts frontend .gitignore`
- `git diff -- backend/app/__init__.py backend/app/utils/auth.py backend/app/api/auth/routes.py backend/app/api/setup/routes.py backend/migrations/versions scripts/deploy.sh .gitignore backend/requirements.txt backend/requirements.lock`
- If you touch any additional backend/deploy file, run the smallest targeted verification needed and record it.
- If `npm audit` requires escalation or a user-terminal run, record the exact command and outcome in handoff.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- whether a migration was added for throttling persistence
- how per-IP and per-username throttling now work
- what header policy landed and any compatibility allowances in CSP
- which lock file name was chosen and how deploy now installs from it
- what the history check found
- whether `/setup/status` was restricted or left public with an explicit decision comment
- what happened with `npm audit`
- any residual risk intentionally left out of scope
- If you discover a genuine cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- The remaining backend/deploy hardening gaps are closed with a coherent, minimal, documented implementation.
- No accepted product-auth behavior is unintentionally changed.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-011`, `F-SEC-014`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-001`, `DEC-FE-006`)
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- backend handoff for this phase after backend finishes
- `frontend/src/store/authStore.ts`
- `frontend/src/api/setup.ts`
- `frontend/src/utils/setup.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `backend/app/__init__.py`
- `backend/app/api/setup/routes.py`

Goal
- Add frontend-side awareness of the deliberate refresh-token storage tradeoff and adjust setup-status consumption only if the backend restriction decision makes a real frontend change necessary.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to frontend auth/setup files plus `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`.
- Do not broaden into auth-storage migration, cookie work, or visual redesign.

Current Repo Reality You Must Respect
- `frontend/src/store/authStore.ts` deliberately persists only the refresh token in `localStorage` under `stoqio_refresh_token` (`DEC-FE-006`).
- This phase does not replace that storage model; it only documents the tradeoff and its compensating server-side headers.
- Current frontend setup-status callsites appear to be post-auth only, which likely means backend can auth-guard `/setup/status` without a frontend rewrite.
- However, verify the actual flow after backend finishes instead of assuming.

Non-Negotiable Contract Rules
- Do not migrate refresh handling to cookies.
- Do not change auth response shapes or auth-store data shape.
- Keep setup/auth UX unchanged unless a minimal compatibility fix is required by the backend `/setup/status` decision.

Tasks
1. `F-SEC-011` — frontend awareness:
- Add a short comment near the `localStorage` refresh-token write in `frontend/src/store/authStore.ts` explaining that:
- this persisted refresh-token choice is deliberate in the current baseline
- compensating browser hardening headers are now expected server-side
- this file should not be treated as permission to start storing the access token in `localStorage`
2. `F-SEC-014` — setup-status compatibility audit:
- Review the backend result for `/setup/status`.
- If the backend auth-guards the route and the current frontend flow still works, do not churn frontend code.
- If a real frontend adjustment is required, keep it minimal and restricted to the setup/auth callsites listed above.
- Document clearly whether frontend changes were actually needed or whether the existing authenticated flow was already compatible.

Verification
- If you only add the `authStore.ts` comment and no runtime logic changes are needed, source review is sufficient; record that explicitly.
- If you change setup/auth runtime code, run the smallest targeted frontend verification you can support from the existing repo (for example a targeted `vitest` slice or a build if appropriate) and record it.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- the exact comment added near refresh-token storage
- whether `/setup/status` required any frontend change
- any residual ambiguity or out-of-scope risk

Done Criteria
- The frontend now explicitly acknowledges the deliberate refresh-token storage tradeoff.
- No unnecessary frontend churn was introduced.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-010`, `F-SEC-011`, `F-SEC-012`, `F-SEC-013`, `F-SEC-014`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-001`, `DEC-FE-006`)
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- backend handoff for this phase after backend finishes
- frontend handoff for this phase after frontend finishes
- `backend/app/__init__.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/api/setup/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_setup.py`
- `backend/tests/test_phase9_ops.py`
- `frontend/src/store/authStore.ts`
- `scripts/deploy.sh`
- `.gitignore`
- `backend/requirements.txt`
- `backend/requirements.lock`

Goal
- Lock the final hardening contract for `F-SEC-010` through `F-SEC-015` with targeted verification and regression tests.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to test files plus `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`.
- Do not broaden into runtime code changes unless you hit a true blocker and document it clearly.

Current Repo Reality You Must Respect
- Existing tests already cover the current same-IP rate-limit behavior and setup/status basics.
- This phase should extend those tests to the new durable/account-scoped contracts rather than replacing the whole auth/setup suite.
- `npm audit` may hit the known sandbox/network limitation from `DEC-FE-001`; if so, you must record the exact failure rather than inventing a pass.

Minimum Required Coverage
1. `F-SEC-010` — login throttling:
- Add a test proving repeated failed attempts for the same username from different IPs are throttled once the account/username bucket limit is reached.
- Add a test proving throttle state survives a simulated process restart or fresh app instance using persisted/shared backing state.
- Keep the assertion grounded in the real login route and persisted store, not just an isolated helper.
2. `F-SEC-011` — security headers:
- Add a test proving an API response includes:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Content-Type-Options: nosniff`
- If helpful, add a narrow assertion that the CSP still allows the current SPA baseline without checking every directive literally.
3. `F-SEC-012` — Python lock file:
- Verify the pinned backend lock file exists.
- Verify `scripts/deploy.sh` installs from it rather than directly from `requirements.txt`.
4. `F-SEC-013` — ignore coverage:
- Verify `.gitignore` covers the requested secret-bearing patterns.
- The history-check result can remain a handoff/manual verification item unless backend added an automated assertion-worthy artifact.
5. `F-SEC-014` — setup-state disclosure:
- If backend restricted `/setup/status`, confirm unauthenticated callers are rejected with the expected auth failure.
- If backend deliberately left it public, confirm the explicit decision comment is present and the route behavior is unchanged.
6. `F-SEC-015` — npm audit gate:
- Confirm `scripts/deploy.sh` contains the `npm audit --audit-level=high` step.
- If an actual `npm audit --audit-level=high` run was possible, confirm it exited `0`.
- If it was blocked by sandbox/network limits, record that exact result and whether backend established the audit result through an approved alternate path.

Testing Guidance
- `backend/tests/test_auth.py` is the natural home for throttle persistence and username-bucket coverage.
- `backend/tests/test_setup.py` is the natural home for the setup-status auth/public decision.
- `backend/tests/test_phase9_ops.py` is a reasonable place for deploy-script, header, lock-file, and `.gitignore` verification if that keeps operational/security contracts discoverable.
- Avoid duplicating coverage that is already clear unless the new phase contract truly needs a sharper assertion.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py -q`
- `bash -n scripts/build.sh && bash -n scripts/deploy.sh`
- If you can safely run `cd frontend && npm audit --audit-level=high`, record the exact outcome.
- If you add any frontend-runtime-sensitive regression and there is an existing targeted frontend test to run, record that too.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which throttle, header, lock-file, ignore, setup-status, and deploy-audit guarantees are now explicitly locked
- whether `npm audit` truly ran or was environment-blocked
- any residual ambiguity or out-of-scope risk

Done Criteria
- The remaining hardening/deploy contracts are obvious from the tests and verification notes.
- No accepted auth/setup/product behavior is accidentally regressed.
- Verification is recorded in handoff.

## Follow-up Delegation Prompt - Backend/Deploy Agent

You are the backend/deploy follow-up agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before coding:
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

Goal
- Resolve the remaining backend/deploy blocker for `F-SEC-012` and fill the missing backend handoff trail so Phase 5 can be closed after final testing.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to `scripts/deploy.sh` and `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`.
- Do not edit frontend dependency files; a separate frontend follow-up agent owns the Vite/npm-audit blocker.
- Do not change throttle/auth/setup product behavior unless you discover a direct regression, and if so stop and document the blocker instead of broadening scope.

Current Blockers
- `scripts/deploy.sh` currently installs from `requirements.lock` when present but falls back to `requirements.txt` when the lock file is missing.
- Testing recorded that this weakens the `F-SEC-012` reproducible deploy contract.
- `backend.md` for this phase is missing, even though backend implementation work already landed.

Tasks
1. Update `scripts/deploy.sh` so deploy hard-fails if `backend/requirements.lock` is missing instead of falling back to `requirements.txt`.
2. Keep the existing comment that backend dependencies must be regenerated and committed when dependencies change; adjust wording if needed to make the hard-fail behavior clear.
3. Create or append `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md` using the `handoff/README.md` required section shape.
4. In `backend.md`, document both:
- the observable Phase 5 backend implementation already present in the worktree, including DB-backed login attempts, security headers, setup-status auth guard, `.gitignore`, requirements lock, deploy audit step, and history check status if available from testing/orchestrator
- your follow-up deploy hard-fail change
5. Do not claim `npm audit` is fixed; leave that to the frontend dependency follow-up and testing follow-up.

Verification
- Run `bash -n scripts/deploy.sh`.
- If safe, run `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q`.
- Record all commands and outcomes in `backend.md`.

Done Criteria
- `scripts/deploy.sh` cannot silently deploy from `requirements.txt` when the lock file is missing.
- `backend.md` exists with the required sections and enough detail for final testing/orchestration.

## Follow-up Delegation Prompt - Frontend Dependency Agent

You are the frontend dependency follow-up agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-001`, `DEC-FE-006`)
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/store/authStore.ts`

Goal
- Resolve the `F-SEC-015` high-severity `npm audit` blocker caused by the vulnerable Vite version while leaving Phase 5 auth/storage behavior unchanged.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to `frontend/package.json`, `frontend/package-lock.json`, and appending to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`.
- Do not edit backend/deploy files; a separate backend/deploy follow-up agent owns `scripts/deploy.sh`.
- Do not change refresh-token storage mechanics, auth response shapes, setup flow, or UI behavior.

Current Blocker
- Testing ran `npm audit --audit-level=high` with registry access and found one high-severity vulnerability affecting `vite 7.0.0 - 7.3.1`.
- The repo currently references `"vite": "^7.3.1"` and the lockfile resolves `node_modules/vite` to `7.3.1`.

Tasks
1. Update Vite to a non-vulnerable version that clears `npm audit --audit-level=high`.
2. Prefer the smallest safe dependency update that fixes the high finding. If `npm audit fix` proposes a broader change, inspect the diff and keep it minimal.
3. Update both `frontend/package.json` and `frontend/package-lock.json` if needed so future installs resolve the safe version intentionally.
4. Append a follow-up entry to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md` using the required handoff section shape.

Verification
- Run `cd frontend && npm audit --audit-level=high`.
- Run `cd frontend && npm run build` if dependency update succeeds.
- If network is blocked in the sandbox, request escalation for the npm command and record the exact result. Do not claim the audit is green unless it actually exits `0`.
- Record all commands and outcomes in `frontend.md`.

Done Criteria
- `npm audit --audit-level=high` exits `0`.
- Vite/package lock changes are minimal and documented.
- No auth/setup runtime behavior changed.

## Follow-up Delegation Prompt - Final Testing Agent

You are the final testing follow-up agent for Wave 4 Phase 5 of the STOQIO WMS project.

Read before testing:
- `handoff/README.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/orchestrator.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/backend.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/frontend.md`
- `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`
- `backend/tests/test_wave4_phase5_security.py`
- `scripts/deploy.sh`
- `backend/requirements.lock`
- `.gitignore`
- `frontend/package.json`
- `frontend/package-lock.json`

Goal
- Verify the Phase 5 follow-up fixes and determine whether the phase is ready for orchestrator acceptance.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to test files if a small assertion needs updating and appending to `handoff/wave-04/phase-05-wave-04-hardening-and-operational-follow-through/testing.md`.
- Do not fix product/deploy/dependency blockers yourself; report them clearly if they remain.

Tasks
1. Confirm `backend.md` now exists and has the required handoff sections.
2. Confirm `scripts/deploy.sh` hard-fails when `requirements.lock` is missing and no longer falls back to `requirements.txt`.
3. Confirm the Vite high-severity audit blocker is fixed by running `npm audit --audit-level=high` in `frontend/`.
4. Re-run the Phase 5 backend security regression suite.
5. Run syntax checks for deploy/build scripts.
6. If needed, update `backend/tests/test_wave4_phase5_security.py` so it explicitly fails on a `requirements.txt` fallback, but keep the change narrow.

Verification
- Run `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q`.
- Run `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q`.
- Run `bash -n scripts/build.sh`.
- Run `bash -n scripts/deploy.sh`.
- Run `cd frontend && npm audit --audit-level=high`.
- If dependency/network commands need escalation, request it and record the exact result.

Done Criteria
- All Phase 5 blockers from the prior testing handoff are resolved or explicitly still blocked with evidence.
- `testing.md` has an appended final follow-up entry with commands, results, and a clear accept/block recommendation.

## Final Orchestrator Acceptance - 2026-04-08 09:03 CEST

Status
- Accepted.

Summary
- Wave 4 Phase 5 is accepted after backend/deploy, frontend dependency, and final testing follow-ups resolved the prior blockers.
- Backend/deploy follow-up removed the `requirements.txt` fallback from `scripts/deploy.sh` and added the missing `backend.md` handoff.
- Frontend dependency follow-up updated Vite from `7.3.1` to `7.3.2`, preserving auth/setup runtime behavior.
- Final testing added a regression assertion preventing the deploy fallback from returning and verified the audit/deploy/security contracts.

Accepted Verification
- `cd backend && venv/bin/python -m pytest tests/test_wave4_phase5_security.py -q` -> `7 passed`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_setup.py tests/test_phase9_ops.py tests/test_wave4_phase5_security.py -q` -> `87 passed`
- `bash -n scripts/build.sh` -> passed
- `bash -n scripts/deploy.sh` -> passed
- `cd frontend && npm audit --audit-level=high` -> passed after escalated network access with `found 0 vulnerabilities`
- `git diff --check` -> passed

Final Notes
- `F-SEC-010` through `F-SEC-015` are now covered by implementation, handoff, and targeted regression/operational verification.
- The only sandbox-limited result was the expected npm registry DNS block; the escalated audit succeeded.
- No open Phase 5 acceptance blockers remain.
