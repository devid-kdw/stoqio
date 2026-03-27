## Phase Summary

Phase
- Wave 2 - Phase 4 - Startup/Auth Hardening

Objective
- Harden startup/auth behavior by making Production fail fast on missing `DATABASE_URL` and removing the hardcoded dummy-hash maintenance trap from the login path without changing user-visible auth behavior.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-035`, `F-036`)
- `stoqio_docs/07_ARCHITECTURE.md` § 3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `backend/app/config.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_auth.py`

Current Repo Reality
- `backend/app/config.py` currently enforces strong `JWT_SECRET_KEY` validation in `Production`, but it sets `self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")` without raising when the variable is missing or blank.
- `backend/app/api/auth/routes.py` currently keeps the timing-safe nonexistent-user login path by always calling `check_password_hash(...)`, but the fallback path depends on a hardcoded route-local PBKDF2 hash literal (`_dummy_hash`).
- The current auth test suite already covers the user-visible login contract for wrong password, nonexistent user, inactive user, refresh, logout, and rate limiting.
- The current auth/config tests do not yet lock the new Wave 2 requirements:
- Production config must fail immediately when `DATABASE_URL` is missing or empty
- the nonexistent-user login path must still exercise password-hash verification without depending on a hardcoded route-local hash string
- Repo baseline before this phase is green:
- backend test suite previously reverified by orchestrator at `361 passed`
- this phase should remain backend/testing only with no frontend work

Contract Locks / Clarifications
- This phase is backend + testing only. No frontend delegation is required.
- Production startup hardening scope is narrow:
- in `Production`, missing or blank `DATABASE_URL` must raise a clear `RuntimeError` during config initialization
- keep development behavior unchanged unless a direct implementation need proves otherwise
- keep existing weak/missing `JWT_SECRET_KEY` protection behavior unchanged
- Auth hardening scope is narrow:
- preserve the current timing-safe intent that nonexistent-user login still exercises the password-hash check path
- remove the hardcoded PBKDF2 literal from the route file
- generate or centralize the dummy hash through the same supported password-hash policy used by the app instead of embedding a static hash string in the route
- do not change login response shape, token lifetimes, rate limiting, error codes, or user-visible auth outcomes for valid/invalid credentials
- Do not broaden this into a general auth redesign, secret rotation project, seed/bootstrap change, or password-policy change.
- Testing must prove contract behavior, not just implementation detail:
- Production config failure on missing/empty `DATABASE_URL`
- weak/missing `JWT_SECRET_KEY` protection still behaves as before
- nonexistent-user login still invokes the hash-check path and still returns the same `401 INVALID_CREDENTIALS` behavior

Delegation Plan
- Backend:
- harden `Production` config for missing/blank `DATABASE_URL`, refactor the dummy-hash path into shared supported auth infrastructure, and keep runtime auth behavior unchanged
- Testing:
- add focused regression coverage for Production config initialization and the timing-safe nonexistent-user login path after the backend refactor

Acceptance Criteria
- Initializing `Production` without `DATABASE_URL` fails immediately with a clear `RuntimeError`.
- Initializing `Production` with weak or missing `JWT_SECRET_KEY` still fails as before.
- The login route no longer embeds a hardcoded PBKDF2 dummy hash literal.
- The nonexistent-user login path still exercises password-hash verification instead of skipping the hash-check path.
- User-visible auth behavior remains unchanged:
- nonexistent user still returns `401 INVALID_CREDENTIALS`
- wrong password still returns `401 INVALID_CREDENTIALS`
- inactive user handling remains unchanged
- New backend tests cover the new config/auth hardening requirements and pass.
- The phase leaves complete backend, testing, and orchestration handoff notes.

Validation Notes
- 2026-03-27 18:23:56 CET — Orchestrator review completed.
- Accepted:
- `backend/app/api/auth/routes.py` no longer embeds a hardcoded PBKDF2 dummy hash literal; the nonexistent-user login path now calls `get_dummy_hash()` from `backend/app/utils/auth.py`.
- The timing-safe auth intent is still present: the nonexistent-user login path still exercises `check_password_hash(...)`, and targeted auth regression coverage for that path passes.
- Weak/missing `JWT_SECRET_KEY` protection remains intact, and the targeted/full backend test runs are green:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q` -> `39 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `370 passed`
- Finding:
- `backend/app/config.py` does not yet treat whitespace-only `DATABASE_URL` values as blank. The current check is `if not db_url`, so `DATABASE_URL='   '` still initializes `Production()` successfully instead of failing fast on a blank value.
- Orchestrator reproduction:
- `cd backend && venv/bin/python - <<'PY' ... Production() ... PY` with `DATABASE_URL='   '` -> `OK '   '`
- Impact:
- The delegated startup hardening contract is only partially satisfied. Missing and empty-string `DATABASE_URL` now fail, but blank whitespace-only values still slip through and defer failure deeper into startup/runtime.
- Missing:
- Normalize `DATABASE_URL` before validation in `Production.__init__` so whitespace-only values fail fast too.
- Add a regression test that covers whitespace-only `DATABASE_URL`, not just the empty string.
- 2026-03-27 18:27:41 CET — Follow-up fix implemented directly by Orchestrator on user request.
- Orchestrator updated `backend/app/config.py` so `Production.__init__` trims `DATABASE_URL` before validation; whitespace-only values now fail fast with the same clear `RuntimeError`.
- Orchestrator added a focused regression test in `backend/tests/test_auth.py` for whitespace-only `DATABASE_URL`.
- Verification re-run by Orchestrator after the follow-up fix:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q` -> `40 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `371 passed`
- direct reproduction check with `DATABASE_URL='   '` now raises `RuntimeError Production requires DATABASE_URL to be set. Set it in your .env file.`
- Phase is accepted.

Next Action
- Phase is accepted.
- No further action is required for this phase unless the user wants to broaden startup/auth hardening beyond the current `F-035` / `F-036` scope.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 2 Phase 4 of the STOQIO WMS project.

You are not alone in the codebase. Do not revert unrelated work. Your ownership is limited to backend startup/auth code, any targeted backend tests truly required to support your backend change, and `handoff/phase-04-wave-02-startup-auth-hardening/backend.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-035`, `F-036`)
- `stoqio_docs/07_ARCHITECTURE.md` § 3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-04-wave-02-startup-auth-hardening/orchestrator.md`
- `backend/app/config.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_auth.py`

Goal
- Harden startup/auth behavior by making `Production` fail fast on missing `DATABASE_URL` and removing the hardcoded dummy-hash maintenance trap from the login path while preserving the current auth contract.

Current Repo Reality
- `Production.__init__` currently validates `JWT_SECRET_KEY` but does not fail fast on missing/blank `DATABASE_URL`.
- `login()` currently keeps the nonexistent-user path timing-safe by always calling `check_password_hash(...)`, but the fallback path depends on a hardcoded route-local PBKDF2 hash literal.
- The current test suite already locks the user-visible login outcomes, so this phase should preserve those behaviors rather than redefine them.

Non-Negotiable Contract Rules
- In `Production`, missing or blank `DATABASE_URL` must raise a clear `RuntimeError` during config initialization.
- Keep the existing weak/missing `JWT_SECRET_KEY` protection behavior unchanged.
- Preserve the timing-safe intent of the nonexistent-user login path:
- nonexistent-user login must still exercise the password-hash check path
- do not replace it with an early return that skips hash verification
- Remove the hardcoded PBKDF2 literal from the route file.
- Generate or centralize the dummy hash through the same supported password-hash policy used by the app.
- Prefer shared auth infrastructure for the dummy-hash path over a new route-local constant.
- Keep user-visible auth behavior unchanged:
- same login endpoint
- same response shape
- same token behavior
- same error semantics for invalid credentials / inactive users
- Do not broaden this into password-policy changes, seed/bootstrap changes, or unrelated auth refactors.

Tasks
1. In `Production` config, raise a clear `RuntimeError` when `DATABASE_URL` is missing or blank.
2. Keep current `JWT_SECRET_KEY` validation semantics unchanged.
3. Refactor the nonexistent-user login fallback so it no longer depends on a hardcoded PBKDF2 literal embedded in `backend/app/api/auth/routes.py`.
4. Centralize or generate the dummy hash through the same supported password-hash policy used by the app.
5. Keep the timing-safe hash-check behavior intact for nonexistent-user login.
6. Keep backend changes minimal and localized to this phase scope.
7. Append your work log to `handoff/phase-04-wave-02-startup-auth-hardening/backend.md` using the section shape required by `handoff/README.md`.

Suggested Implementation Direction
- Prefer a small shared helper in the auth utility layer rather than leaving the dummy-hash generation in the route file.
- If the dummy hash is generated dynamically, avoid unnecessary per-request churn if a simpler centralized cached approach keeps the same contract.
- Keep the route contract thin; this is a hardening pass, not a redesign.

Verification
- Run the smallest relevant backend verification you need, but at minimum cover the touched auth/config surface.
- If you add or update backend tests as part of the implementation, record the exact commands and results.
- If the blast radius grows beyond the targeted files, expand verification accordingly and record why.

Done Criteria
- `Production` fails fast on missing/blank `DATABASE_URL`.
- Weak/missing `JWT_SECRET_KEY` protection is unchanged.
- The route no longer embeds a hardcoded PBKDF2 dummy hash literal.
- Nonexistent-user login still exercises password-hash verification.
- No user-visible auth contract drift was introduced.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 2 Phase 4 of the STOQIO WMS project.

You are not alone in the codebase. Do not revert unrelated work. Your ownership is limited to backend regression coverage and `handoff/phase-04-wave-02-startup-auth-hardening/testing.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-035`, `F-036`)
- `stoqio_docs/07_ARCHITECTURE.md` § 3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-04-wave-02-startup-auth-hardening/orchestrator.md`
- backend handoff for this phase after the Backend Agent finishes
- `backend/app/config.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_auth.py`

Goal
- Lock regression coverage for Production config startup hardening and the timing-safe nonexistent-user login path after the backend refactor.

Current Repo Reality
- Existing auth tests already cover visible login outcomes, but they do not yet prove the new config failure contract or the preserved hash-check path for nonexistent users.
- This phase is targeted hardening. Keep the new test surface focused and avoid unrelated auth-suite rewrites.

Non-Negotiable Test Rules
- Add/configure backend tests for Production config initialization:
- missing `DATABASE_URL` in `Production` must fail immediately
- weak/missing `JWT_SECRET_KEY` protection must still behave as before
- Add/update auth tests proving nonexistent-user login still follows the timing-safe hash-check path without relying on the old hardcoded route-local hash string.
- Keep user-visible auth assertions intact:
- nonexistent user still yields `401 INVALID_CREDENTIALS`
- existing wrong-password/inactive-user semantics remain stable
- Prefer focused mocking/monkeypatching where needed rather than brittle implementation-coupled assertions about exact private variable names.
- Do not broaden this into a full auth-suite rewrite or unrelated config refactor test pass.

Tasks
1. Add focused backend coverage for `Production` config initialization:
- missing `DATABASE_URL` -> clear immediate failure
- blank `DATABASE_URL` -> clear immediate failure if the backend implementation treats blank as invalid separately
- weak/missing `JWT_SECRET_KEY` protection still fails
2. Add or update auth tests proving the nonexistent-user login path still exercises password-hash verification after the refactor.
3. Keep the test strategy resilient to the new shared-helper design:
- do not assert the old hardcoded literal
- prove the hash-check path is still executed
4. Preserve the existing user-visible login outcome assertions.
5. Append your work log to `handoff/phase-04-wave-02-startup-auth-hardening/testing.md` using the section shape required by `handoff/README.md`.

Suggested Test Direction
- For config hardening, use focused environment monkeypatching against `Production`.
- For the nonexistent-user auth path, prefer monkeypatching/spying on the hash-check path and/or the centralized dummy-hash helper so the test proves behavior without depending on the removed literal.
- If the backend agent keeps all test changes in `backend/tests/test_auth.py`, work with that. If a new focused config test file is added, keep it narrow.

Verification
- Run the new/updated backend test command(s) that cover this phase.
- Also rerun the smallest relevant auth subset needed to prove no contract drift.
- If you need broader backend-suite verification because the backend refactor touches shared auth infrastructure, record that explicitly.

Done Criteria
- Production config hardening is covered by automated tests.
- The timing-safe nonexistent-user login path is covered by automated tests.
- User-visible auth behavior remains locked by the test suite.
- All new tests pass and are recorded in handoff.
