## Phase Summary

Phase
- Wave 3 - Phase 7 - Revoked Token Retention Cleanup

Objective
- Add a safe, explicit cleanup path for expired `revoked_token` rows without weakening persisted logout revocation or refresh-token revocation semantics.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-008`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-012`, `DEC-FE-006`)
- `backend/app/__init__.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/app/models/revoked_token.py`
- `backend/tests/test_auth.py`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `README.md`
- `scripts/deploy.sh`

Current Repo Reality
- Refresh-token logout revocation is already DB-backed:
- `POST /api/v1/auth/logout` persists the refresh token `jti` in `revoked_token`
- `@jwt.token_in_blocklist_loader` checks the DB-backed registry through `app.utils.auth.is_token_revoked(...)`
- This is an accepted baseline via `DEC-BE-012`; it must not be weakened in this phase.
- `RevokedToken` currently stores:
- `jti`
- `token_type`
- `user_id`
- `revoked_at`
- `expires_at`
- The schema already carries the exact field needed for retention cleanup: `expires_at`.
- There is currently no explicit cleanup path in the repo for expired revoked rows:
- no Flask CLI/admin maintenance command
- no documented scheduled task
- no operator runbook step in the current deployment docs
- There are currently no Flask CLI commands registered anywhere in the repo, so this phase may need to introduce the first explicit maintenance command if that is the chosen design.
- Existing auth coverage already locks important runtime behavior in `backend/tests/test_auth.py`:
- logout succeeds only with a refresh token
- logout persists a revoked token row
- revoked refresh tokens can no longer mint new access tokens
- Current deployment/ops docs mention DB-backed logout revocation, but they do not tell operators how or when expired rows should be cleaned up:
- `stoqio_docs/07_ARCHITECTURE.md`
- `README.md`
- `scripts/deploy.sh` reflects the deploy flow but does not include any maintenance task for revocation cleanup
- `handoff/README.md` defines backend/frontend/testing agent files only. Because this phase explicitly includes a documentation agent, this phase needs a dedicated `documentation.md` handoff file using the same section shape as the standard agent files.

Contract Locks / Clarifications
- Runtime logout persistence and refresh-token revocation semantics must remain unchanged.
- Cleanup must delete only rows whose `expires_at` is strictly in the past at execution time.
- Rows with `expires_at IS NULL` must not be deleted by the cleanup path unless the user later changes that retention policy explicitly.
- Do not add automatic cleanup on every request, on auth checks, or on application startup. This phase requires an explicit operator-invoked or scheduled maintenance path.
- Do not change the current revocation lookup path in a way that would make an actually revoked unexpired refresh token usable again.
- If an index or query optimization is added, it must support the cleanup path without changing the logical revocation contract.
- Keep the change set narrow:
- no frontend work
- no redesign of JWT lifetimes
- no change from DB-backed revocation to another store
- no automatic deletion of still-valid revoked rows
- Documentation should explain the cleanup path in the local-host/server deployment context already used by this repo.

Delegation Plan
- Backend:
- implement one explicit cleanup path for expired revoked rows and keep runtime revocation behavior intact
- Testing:
- lock cleanup behavior and confirm auth/logout regression coverage remains green
- Documentation:
- update the repo's deployment/ops docs and leave a documentation-agent handoff trace in `documentation.md`

Acceptance Criteria
- There is now one clear explicit cleanup path for expired `revoked_token` rows.
- Cleanup removes only expired revoked rows and leaves non-expired rows intact.
- Logout persistence and refresh-token revocation behavior remain unchanged.
- Auth/logout regression coverage remains green.
- Ops/deployment docs explain how to run the cleanup in a local-host deployment.
- The phase leaves complete backend, testing, documentation, and orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first.
- Testing should run after backend delivery is available.
- Documentation can run after the cleanup mechanism name/path is finalized in backend delivery.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 7 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-008`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-012`, `DEC-FE-006`)
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- `backend/app/__init__.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/app/models/revoked_token.py`
- `backend/tests/test_auth.py`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `scripts/deploy.sh`

Goal
- Add a safe explicit cleanup path for expired `revoked_token` rows without weakening persisted logout revocation or refresh-token revocation semantics.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation files plus `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md`.
- Do not edit docs files in this phase. The documentation agent owns docs changes.
- Prefer leaving backend test changes to the testing agent unless a tiny backend-owned test is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- Logout revocation is already persisted through `add_to_blocklist(...)` and `is_token_revoked(...)`.
- `revoked_token.expires_at` already exists and is the only approved retention signal for this phase.
- There are currently no Flask CLI commands in the repo.
- Existing auth tests already lock DB-backed logout persistence and revoked-refresh rejection.

Non-Negotiable Contract Rules
- Do not change runtime revocation checks or logout semantics.
- Cleanup must delete only rows with `expires_at < now`.
- Do not delete rows with `expires_at IS NULL`.
- Do not add implicit cleanup inside request handling, JWT callbacks, app startup, or logout itself.
- The cleanup path must be explicit and operator-invoked or scheduler-invoked.
- If you add an index, keep it minimal and justified by the cleanup query path.
- Do not redesign auth/token storage, JWT lifetimes, or frontend bootstrap behavior.

Tasks
1. Design and implement one explicit cleanup mechanism for expired `revoked_token` rows.
2. Preferred implementation options:
- a Flask CLI command / maintenance command
- a documented scheduled task invoking that command
- or another explicit operator-invoked maintenance path if it fits the repo better
3. Ensure cleanup deletes only expired rows and leaves non-expired rows untouched.
4. Keep the existing runtime revocation checks exactly intact from the caller perspective.
5. If helpful, add a focused schema/query optimization for cleanup selection.
6. Make sure the chosen command/path is easy for the documentation agent to explain in local-host deployment docs.

Verification
- Run at minimum:
- `rg -n 'revoked_token|add_to_blocklist|is_token_revoked|logout' backend/app -g '*.py'`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q`
- If you add another backend slice tied to the cleanup mechanism, run the relevant targeted tests too and record them.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- the exact cleanup mechanism added
- how operators invoke it
- any schema/index change added and why
- files changed
- commands run
- tests run
- open issues or residual risk
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- There is a clear explicit cleanup path for expired revoked rows.
- Runtime revocation behavior remains unchanged.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 7 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-008`)
- `handoff/README.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- backend handoff for this phase after backend finishes
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/app/models/revoked_token.py`
- `backend/tests/test_auth.py`
- any backend file added for the cleanup mechanism

Goal
- Lock regression coverage around expired `revoked_token` cleanup while proving logout persistence and revoked-refresh behavior remain unchanged.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files and `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md`.

Non-Negotiable Contract Rules
- Focus on proving behavior stayed the same except for the new explicit cleanup path.
- Do not broaden into frontend/auth redesign.
- Prefer behavioral tests over implementation-detail assertions.
- Keep runtime revocation checks covered exactly as an auth contract, not as an internal DB detail only.

Minimum Required Coverage
1. Cleanup behavior:
- expired revoked rows are removed by the cleanup path
- non-expired revoked rows remain
- rows with `expires_at IS NULL` remain if such a case can exist in the current model/implementation
2. Auth regression behavior:
- runtime revoked-token checks still reject revoked refresh tokens exactly as before
- logout still persists a revoked row exactly as before
3. Run auth regression coverage after the cleanup mechanism lands.

Testing Guidance
- Extend `backend/tests/test_auth.py` first if practical.
- If the cleanup mechanism is a Flask CLI command, test it through Flask's CLI runner or another stable backend test path rather than only unit-testing a helper in isolation.
- Keep the assertions aligned with the real operator-invoked path added by backend.
- If an index/migration is introduced, cover the runtime behavior rather than schema minutiae unless a schema assertion is truly needed.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q`
- `cd backend && venv/bin/python -m pytest -q`
- Confirm the new cleanup path only removes expired rows and that revocation behavior remains unchanged.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which cleanup behaviors were explicitly locked
- which auth/logout regressions were explicitly revalidated
- residual risk, if any

Done Criteria
- Cleanup behavior is covered by regression tests.
- Auth/logout regression behavior remains green.
- Verification is recorded in handoff.

## Delegation Prompt - Documentation Agent

You are the documentation agent for Wave 3 Phase 7 of the STOQIO WMS project.

Read before editing:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-008`)
- `handoff/README.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- backend handoff for this phase after backend finishes
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `scripts/deploy.sh`

Goal
- Update the repo's ops/deployment docs so operators know how to run the expired revoked-token cleanup in a local-host deployment.

Special handoff rule for this phase
- `handoff/README.md` does not define a standard documentation-agent file.
- For this phase, append your work log to `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/documentation.md`.
- Use the same section shape required by `handoff/README.md`:
- `Status`
- `Scope`
- `Docs Read`
- `Files Changed`
- `Commands Run`
- `Tests`
- `Open Issues / Risks`
- `Next Recommended Step`

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to documentation files and `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/documentation.md`.

Non-Negotiable Contract Rules
- Document the cleanup mechanism that actually landed in backend; do not invent a different operator path.
- Keep the docs aligned with the repo's local-host/server deployment model.
- Do not redesign the deployment process beyond what is needed to explain the cleanup step.
- If the cleanup is intended as a scheduled task, explain one practical local-host scheduling approach without overstating platform guarantees.

Tasks
1. Update the relevant ops/deployment docs to mention the revoked-token cleanup mechanism.
2. Explain:
- what the cleanup does
- when operators should run it
- the exact command/path to run
- that it removes only expired revoked tokens and does not weaken active revocation
3. Prefer updating the docs already used for deployment/ops in this repo, such as:
- `stoqio_docs/07_ARCHITECTURE.md`
- `README.md`
- and any other closely related ops doc if the backend implementation makes it clearly relevant
4. Keep the wording practical for single-server local-host deployment.

Verification
- Review the backend delivery to ensure the documented command/path matches the actual implementation.
- Record any manual documentation verification you performed.

Done Criteria
- Operators can now discover and understand the cleanup mechanism from repo docs.
- Documentation changes and handoff are recorded.

## [2026-04-03 16:27 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend, testing, and documentation work for Wave 3 Phase 7.
- Compared the agent handoffs against the actual repo diff.
- Re-ran the requested auth and full-suite verification.
- Verified the new operator-facing CLI path and checked the migration chain readiness.

Docs Read
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/documentation.md`
- `handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/orchestrator.md`
- `backend/app/__init__.py`
- `backend/app/commands.py`
- `backend/app/api/auth/routes.py`
- `backend/app/utils/auth.py`
- `backend/migrations/versions/e1f2a3b4c5d6_add_revoked_token_expires_at_index.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_phase2_models.py`
- `README.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`

Commands Run
```bash
git status --short
git diff -- backend/app/__init__.py backend/app/commands.py backend/tests/test_auth.py backend/migrations/versions/e1f2a3b4c5d6_add_revoked_token_expires_at_index.py README.md stoqio_docs/05_DATA_MODEL.md stoqio_docs/07_ARCHITECTURE.md handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/backend.md handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/testing.md handoff/wave-03/phase-07-wave-03-revoked-token-retention-cleanup/documentation.md
ls backend/migrations/versions | sort
rg -n 'revision =|down_revision =' backend/migrations/versions/*.py
cd backend && venv/bin/flask --help
cd backend && venv/bin/flask purge-revoked-tokens --help
cd backend && venv/bin/flask purge-revoked-tokens --dry-run
cd backend && venv/bin/python -m pytest tests/test_auth.py -q
cd backend && venv/bin/python -m pytest tests/test_phase2_models.py -q
cd backend && venv/bin/python -m pytest -q
```

Findings
- None.

Validation Result
- Passed:
- backend now exposes one explicit operator-facing cleanup path via `flask purge-revoked-tokens` in `backend/app/commands.py`, registered from `backend/app/__init__.py`
- the cleanup command is explicit only:
- not invoked on request handling
- not invoked on startup
- not invoked during logout
- the cleanup logic is correctly scoped to expired rows only:
- `expires_at IS NOT NULL`
- `expires_at < now`
- `expires_at IS NULL` rows are preserved
- runtime auth/revocation semantics remain intact:
- `backend/app/api/auth/routes.py` and `backend/app/utils/auth.py` were not altered in ways that change logout persistence or revoked-refresh rejection
- testing now locks the expected cleanup behaviors and auth regressions inside `backend/tests/test_auth.py`
- the new migration `e1f2a3b4c5d6_add_revoked_token_expires_at_index.py` is chained correctly after `d4e5f6a7b8c9`, and the migration regression slice still passes:
- `cd backend && venv/bin/python -m pytest tests/test_phase2_models.py -q` -> `2 passed`
- live CLI discovery and operator path were verified:
- `cd backend && venv/bin/flask --help` shows `purge-revoked-tokens`
- `cd backend && venv/bin/flask purge-revoked-tokens --help` shows the documented `--dry-run` option
- `cd backend && venv/bin/flask purge-revoked-tokens --dry-run` completed successfully and reported `[dry-run] 3 expired revoked_token row(s) would be deleted.`
- documentation now explains the cleanup path in the actual repo ops docs:
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q` -> `49 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `464 passed in 57.17s`

Closeout Decision
- Wave 3 Phase 7 is accepted and closed.

Residual Notes
- No residual implementation or documentation issues were found in this phase.

Next Action
- Treat the current worktree and this orchestrator closeout as the accepted Wave 3 Phase 7 baseline.
- Proceed to Wave 3 Phase 8 - Inventory Count Frontend Refactor.
