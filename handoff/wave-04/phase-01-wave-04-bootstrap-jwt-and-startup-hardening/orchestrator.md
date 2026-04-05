## Phase Summary

Phase
- Wave 4 - Phase 1 - Bootstrap, JWT, and Startup Hardening

Objective
- Harden the bootstrap credential path, JWT/config defaults, and startup mode selection so STOQIO is fail-safe by default.
- This phase covers:
- `F-SEC-001` — hardcoded bootstrap admin credential
- `F-SEC-002` — predictable JWT/config fallback behavior
- `F-SEC-003` — hardcoded debug-oriented startup behavior

Source Docs
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-001`, `F-SEC-002`, `F-SEC-003`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-009`, `DEC-BE-017`)
- `handoff/wave-03/recap.md`
- `README.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/.env.example`
- `backend/seed.py`
- `backend/app/config.py`
- `backend/run.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_phase9_ops.py`

Current Repo Reality
- Wave 3 is closed and accepted; its Phase 10 baseline is the starting point for this phase.
- `backend/seed.py` still documents and creates `admin / admin123`.
- `README.md` still includes `venv/bin/python seed.py` in the normal backend bootstrap flow and does not warn that this script is local-development-only.
- `backend/app/config.py` still:
- injects a known fallback JWT secret from `_Base`
- defaults `FLASK_ENV` to `development` when unset
- allows the repo to boot into development-oriented behavior when env vars are absent
- `Production` already rejects weak/missing JWT secrets and blank/missing `DATABASE_URL`, but those guards are not fail-safe overall because the repo defaults to the `Development` path when `FLASK_ENV` is absent.
- `backend/run.py` still hardcodes `debug=True`.
- Existing auth tests already cover several production config guards, including missing/weak JWT secret behavior, but they do not yet lock:
- production-as-default environment selection
- seed bootstrap random-password behavior
- debug-off behavior when the environment is not explicitly development
- The accepted Wave 2 setup/seed decision is still that `backend/seed.py` remains the supported reference-data seed path after migrations (`DEC-BE-017`), but this phase now hardens it as a local-development bootstrap tool rather than leaving it safe-looking for shared or production-like instances.
- Live product docs outside `README.md` still contain older `admin123` references (`stoqio_docs/08_SETUP_AND_GLOBALS.md`, `stoqio_docs/19_IMPLEMENTATION_PLAN.md`), but the user explicitly scoped this phase to backend + testing plus a README update, not a broader docs-alignment sweep.
- Because `backend/seed.py` and `backend/run.py` load config through the real environment path, making production the default environment means local dev startup must rely on an explicit development signal (`backend/.env` or exported env vars). Do not undo the fail-safe goal just to preserve old implicit startup behavior.

Contract Locks / Clarifications
- Do not change warehouse business rules, auth route shapes, JWT lifetimes, refresh-token semantics, RBAC behavior, or first-run setup behavior.
- No frontend work is in scope for this phase.
- Do not broaden into other security findings from the review such as:
- password policy strengthening
- password-change refresh-token invalidation
- Excel export sanitization
- printer/network restriction hardening
- diagnostic cleanup
- `admin123` removal scope for this phase is:
- executable code paths
- runtime output / test expectations
- operator-facing `README.md` guidance
- Do not rewrite historical handoff artifacts just because they record the old credential. Those records are archival.
- If `.env.example` retains a checked-in development placeholder secret for local development, `Production` must explicitly reject that exact placeholder value as a known default.
- Keep changes narrow, fail-safe, and documentation-aligned with the actual final runtime behavior.

Delegation Plan
- Backend:
- harden `backend/seed.py`, `backend/app/config.py`, `backend/run.py`, and any tightly coupled config/example file needed to make the startup path fail-safe
- update `README.md` so the seed workflow is clearly local-development-only
- Testing:
- add regression coverage for the new fail-fast config behavior, seed output behavior, and debug-mode gating
- verify the README/operator guidance no longer normalizes a known bootstrap password

Acceptance Criteria
- `backend/seed.py` no longer hardcodes `admin123`.
- A one-time random password is generated with `secrets.token_urlsafe(16)` only when the bootstrap admin user is first created.
- That generated password is printed once during seed completion and is not echoed on skip/re-run paths or elsewhere in runtime/test output.
- `README.md` explicitly states that `backend/seed.py` is for local development only and must never be run on a production or shared instance.
- `backend/app/config.py` no longer relies on a predictable runtime fallback JWT secret.
- Missing `FLASK_ENV` now resolves to the production config path.
- Production startup fails immediately with a clear `RuntimeError` if `JWT_SECRET_KEY` is missing or equals the known checked-in default/example value.
- No non-production-safe defaults are active when env vars are absent.
- `backend/run.py` no longer hardcodes `debug=True`; debug mode is enabled only when the environment is explicitly development.
- All non-development config classes leave `DEBUG = False`.
- New/updated backend tests pass and the phase leaves a complete backend + testing + orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first because testing should lock the final runtime behavior, not the pre-change baseline.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 4 Phase 1 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-001`, `F-SEC-002`, `F-SEC-003`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-009`, `DEC-BE-017`)
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `README.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/.env.example`
- `backend/seed.py`
- `backend/app/config.py`
- `backend/run.py`
- `backend/tests/test_auth.py`

Goal
- Make the bootstrap, JWT-secret, and startup configuration fail-safe by default without changing product behavior or broadening into unrelated security findings.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation/config/startup files, `README.md`, and `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/backend.md`.
- Do not edit `stoqio_docs/` files or historical handoff files in this phase unless you hit a true blocker that makes the runtime/README result misleading; if so, document it clearly before expanding scope.
- Prefer leaving backend test changes to the testing agent unless a tiny backend-owned regression test is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- `backend/seed.py` still hardcodes `admin123` and documents it.
- `README.md` still presents `seed.py` as part of the normal backend bootstrap flow without a local-dev-only warning.
- `backend/app/config.py` still contains a known JWT fallback string and defaults missing `FLASK_ENV` to `development`.
- `Production` already rejects weak/missing `JWT_SECRET_KEY` and blank/missing `DATABASE_URL`, but the repo is not fail-safe overall because the default environment path is still development-oriented.
- `backend/run.py` still hardcodes `debug=True`.
- `backend/.env.example` currently carries a checked-in development placeholder secret. If you keep that development convenience, production must still reject it explicitly.

Non-Negotiable Contract Rules
- Do not change auth endpoint contracts, token lifetimes, refresh behavior, RBAC behavior, setup-flow semantics, or warehouse business logic.
- Do not broaden into password-policy changes, password-change token invalidation, export sanitization, printer SSRF hardening, or diagnostic cleanup.
- Keep `backend/seed.py` idempotent.
- Historical handoff records may continue to mention `admin123`; do not rewrite archival history just to scrub old prose.
- Once this phase is done, the app should be safer by default even if an operator forgets to set `FLASK_ENV`.

Tasks
1. `F-SEC-001` — Bootstrap credential hardening:
- Remove the hardcoded `admin123` password from `backend/seed.py`.
- Replace it with a one-time password generated via `secrets.token_urlsafe(16)`.
- Print the generated password once to terminal output on seed completion only when the admin user is created for the first time.
- Do not print a password on skip/re-run paths.
- Remove any other executable-code/runtime references to `admin123` as a credential, but do not broaden into historical handoff cleanup.
2. Update `README.md` so it explicitly states that `backend/seed.py` is for local development only and must never be run on a production or shared instance.
3. `F-SEC-002` — JWT secret and config defaults:
- Remove the known runtime fallback JWT secret from `backend/app/config.py`.
- Make `production` the explicit default environment when `FLASK_ENV` is not set.
- Keep production fail-fast behavior clear and early: if `JWT_SECRET_KEY` is missing or equals the known checked-in default/example value, raise a clear `RuntimeError` before app initialization completes.
- Ensure no non-production-safe defaults are active when env vars are absent.
- Preserve or improve the existing fail-fast `DATABASE_URL` behavior in production.
4. If needed, adjust `backend/.env.example` so local development still has an explicit development path, but do not reintroduce an implicit runtime fallback in code.
5. `F-SEC-003` — Debug/startup hardening:
- Remove the hardcoded `debug=True` behavior from `backend/run.py`.
- Derive debug mode strictly from an explicit development environment check.
- Verify all non-development config classes keep `DEBUG = False`.
- Ensure the production path can never accidentally enable the interactive debugger.
6. Keep the implementation diff narrow and fail-safe.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q`
- `rg -n "admin123|debug=True|dev-local-jwt-secret-change-me-2026" backend README.md`
- `git diff -- backend/seed.py backend/app/config.py backend/run.py backend/.env.example README.md`
- If you add or touch any additional backend file, run the smallest targeted verification needed and record it.
- If you perform a seed/runtime smoke, do it only against a clearly disposable local test environment and record the exact env/command used.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- where the bootstrap credential path was hardened
- what now happens when `FLASK_ENV` is unset
- how the checked-in/example JWT placeholder is treated in production
- how debug mode is now derived
- any residual docs drift or operational risk left intentionally out of scope
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- The seed/bootstrap path no longer creates a known default admin password.
- Startup/config behavior is fail-safe by default.
- Production/debug behavior is explicit and safe.
- README guidance matches the actual intended use of `seed.py`.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 4 Phase 1 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-001`, `F-SEC-002`, `F-SEC-003`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-009`, `DEC-BE-017`)
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- backend handoff for this phase after backend finishes
- `README.md`
- `backend/.env.example`
- `backend/seed.py`
- `backend/app/config.py`
- `backend/run.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_phase9_ops.py`

Goal
- Lock the new fail-safe behavior with regression tests and verification focused on:
- missing-JWT production startup failure
- seed bootstrap output no longer normalizing a known password
- debug staying off unless the environment is explicitly development

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files plus `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/testing.md`.
- Do not broaden into product-doc rewrites or backend runtime changes unless you hit a true blocker and document it clearly.

Non-Negotiable Contract Rules
- Keep behavior unchanged except for the intended hardening from this phase.
- Prefer tests whose names and assertions make the security contract obvious to future reviewers.
- Historical handoff files may still contain `admin123`; do not try to scrub archival history from tests.
- The key thing to lock is fail-safe default behavior, not just the happy-path development flow.

Minimum Required Coverage
1. Production config / startup:
- Add or strengthen a test proving that initializing the production config without `JWT_SECRET_KEY` raises `RuntimeError`.
- Add or strengthen a test proving that when `FLASK_ENV` is absent, the config path does not silently resolve to development.
2. Seed/bootstrap output:
- Add a test confirming the seed path no longer emits `admin123`.
- Make the assertions clear that the bootstrap password is generated rather than hardcoded.
- Prefer a deterministic test by monkeypatching the generator or a narrow seed helper rather than relying on a real persistent DB.
3. Debug gating:
- Add a test confirming debug mode is `False` when the environment is not explicitly development.
- If helpful, also lock the positive case that explicit development enables debug.
4. Verification / repo checks:
- Verify `README.md` no longer instructs operators to use a known default password on a production/shared instance.

Testing Guidance
- Extend `backend/tests/test_auth.py` if that keeps the config/startup contract easiest to discover.
- Use a separate targeted test file only if it makes the seed/run/config hardening easier to isolate.
- It is acceptable to inspect captured output or source-adjacent behavior, but prefer behavior-level assertions over brittle string snapshots when possible.
- If backend refactors `seed.py` for testability, lean into that narrower unit-level verification instead of building a broad subprocess harness.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_phase9_ops.py -q`
- `rg -n "admin123" README.md backend`
- Record exact results in handoff, including any intentionally remaining historical references outside this phase's scope.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which fail-safe behaviors were explicitly locked
- whether `README.md` verification passed
- any residual ambiguity or docs drift left out of scope

Done Criteria
- The new seed/config/run security behavior is obvious from the tests.
- The fail-safe default behavior is locked against regression.
- Verification is recorded in handoff.

## [2026-04-05 15:31 CEST] Orchestrator Review - Changes Requested

Status
- changes_requested

Scope
- Reviewed the delivered backend and testing handoffs for Wave 4 Phase 1.
- Compared the handoffs against the actual repo worktree and targeted diffs.
- Re-ran the claimed automated verification.
- Ran targeted startup and seed smokes against a disposable SQLite database and direct config instantiation checks.

Docs Read
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/backend.md`
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/testing.md`
- `README.md`
- `backend/seed.py`
- `backend/app/config.py`
- `backend/run.py`
- `backend/app/api/setup/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_seed_hardening.py`
- `backend/tests/test_phase9_ops.py`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-017`)

Commands Run
```bash
git status --short
git diff -- README.md backend/seed.py backend/app/config.py backend/run.py backend/tests/test_auth.py backend/tests/test_seed_hardening.py
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_seed_hardening.py tests/test_phase9_ops.py -q
cd backend && venv/bin/python -c "import os; os.environ.pop('FLASK_ENV', None); os.environ.pop('JWT_SECRET_KEY', None); os.environ['DATABASE_URL']='postgresql://user:pass@localhost/wms_prod'; from app import create_app; ..."
cd backend && venv/bin/python -c "import os; os.environ.pop('FLASK_ENV', None); os.environ['DATABASE_URL']='postgresql://user:pass@localhost/wms_prod'; os.environ['JWT_SECRET_KEY']='review-jwt-secret-2026-000000000000'; from app.config import get_config; ..."
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/alembic upgrade head
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/python seed.py
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/python seed.py
```

Findings
- High: `README.md` now states that production installs must create the initial admin account through the authenticated first-run setup flow, but the actual `/api/v1/setup` implementation only creates the initial `Location` and itself requires an already authenticated `ADMIN` JWT. There is no matching production bootstrap path in the repo for creating that first admin through setup. Because the same README block also says `seed.py` must never run on a production or shared instance, the resulting operator guidance is internally contradictory and not operationally true. See `README.md:28-33`, `backend/app/api/setup/routes.py:39-42`, and `handoff/decisions/decision-log.md` (`DEC-BE-017`).
- Medium: The generated bootstrap password is printed inside `_seed_admin()` before the single `db.session.commit()` in `run_seed()`. If a later seeder or the final commit fails, the operator can see a password for an admin row that never committed. That does not satisfy the delegated requirement to print the one-time password on seed completion. See `backend/seed.py:50-63` and `backend/seed.py:186-196`. Current tests do not lock this commit-order behavior.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_seed_hardening.py tests/test_phase9_ops.py -q` → `59 passed`
- Direct config smoke confirms that missing `FLASK_ENV` resolves to `Production` and `DEBUG` is `False` in that path.
- Direct startup smoke confirms app initialization now fails immediately when `JWT_SECRET_KEY` is absent in the production-default path.
- Disposable DB seed smoke confirms first run prints a random password and second run does not print a password.
- Blocked:
- Phase 1 is not accepted yet because the README bootstrap guidance is not accurate for the actual setup/auth flow, and the seed password is emitted before successful completion of the transaction.

Next Action
- Return to Backend for a narrow follow-up:
- move one-time password emission until after successful `db.session.commit()`
- fix `README.md` so it describes the actual supported bootstrap/admin path without claiming that `/setup` creates the initial admin account
- After that follow-up, rerun the targeted tests and seed smoke, then re-review for acceptance.

## [2026-04-05 15:42 CEST] Orchestrator Follow-Up - Fixes Implemented and Phase Accepted

Status
- accepted

Scope
- Implemented the narrow follow-up fixes directly as orchestrator so the previous review blockers are now closed.
- This follow-up work was done by the orchestrator, not by the earlier backend/testing deliveries, so future agents should treat the prior `backend.md` and `testing.md` entries as the pre-fix state for this phase.
- Updated `backend/seed.py` so the one-time bootstrap password is returned from `_seed_admin()` and printed only after the full seed transaction commits successfully.
- Updated `README.md` so it no longer misstates `/setup` as the admin-creation path and now accurately describes that first-run setup creates only the initial `Location`.
- Strengthened `backend/tests/test_seed_hardening.py` so the new commit-order behavior and corrected README wording are locked against regression.

Files Changed
- `backend/seed.py`
- `README.md`
- `backend/tests/test_seed_hardening.py`
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_seed_hardening.py tests/test_phase9_ops.py -q
cd backend && venv/bin/python -c "import os; os.environ.pop('FLASK_ENV', None); os.environ.pop('JWT_SECRET_KEY', None); os.environ['DATABASE_URL']='postgresql://user:pass@localhost/wms_prod'; from app import create_app; ..."
cd backend && venv/bin/python -c "import os; os.environ.pop('FLASK_ENV', None); os.environ['DATABASE_URL']='postgresql://user:pass@localhost/wms_prod'; os.environ['JWT_SECRET_KEY']='review-jwt-secret-2026-000000000000'; from app.config import get_config; ..."
cd backend && rm -f /tmp/stoqio_wave4_seed_review_fresh.sqlite
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review_fresh.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/alembic upgrade head
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review_fresh.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/python seed.py
cd backend && FLASK_ENV=development DATABASE_URL=sqlite:////tmp/stoqio_wave4_seed_review.sqlite JWT_SECRET_KEY=review-seed-jwt-secret-2026-000000000000 venv/bin/python seed.py
```

Findings
- None. The previous README/bootstrap contradiction and seed commit-order issue are resolved.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_seed_hardening.py tests/test_phase9_ops.py -q` → `62 passed`
- Production-default config smoke still fails fast when `JWT_SECRET_KEY` is absent.
- Production-default config smoke still resolves to `Production` with `DEBUG = False` when `FLASK_ENV` is unset and a valid secret is present.
- Fresh disposable-db seed smoke succeeds after migrations and prints a one-time random password after successful completion.
- Re-run disposable-db seed smoke does not print a password again once the admin already exists.
- `README.md` now accurately states that authenticated first-run setup creates the initial `Location` only and does not create the first admin account.

Next Action
- Wave 4 Phase 1 is complete.
- Future Wave 4 work should build on this accepted baseline rather than reopening the bootstrap/JWT/debug defaults unless a concrete new regression is found.
