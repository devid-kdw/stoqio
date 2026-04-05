## Phase Summary

Phase
- Wave 4 - Phase 4 - Diagnostic and Settings Shell Hardening

Objective
- Remove any remaining credential-sensitive output from the local diagnostic helper and ensure `GET /api/v1/settings/shell` is protected through the same active-user authorization path used elsewhere in the API.
- This phase covers:
- `F-SEC-008` — diagnostic script sensitive output
- `F-SEC-009` — `/settings/shell` active-user authorization consistency

Source Docs
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-008`, `F-SEC-009`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/orchestrator.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `handoff/wave-04/phase-03-wave-04-export-sanitization-and-printer-config-hardening/orchestrator.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/utils/auth.py`
- `backend/app/api/settings/routes.py`
- `backend/diagnostic.py`
- `backend/tests/test_settings.py`
- `backend/tests/test_phase9_ops.py`

Current Repo Reality
- Wave 4 Phase 3 is accepted and is the current baseline.
- Both findings in this phase were already addressed earlier in accepted Wave 3 work:
- Wave 3 Phase 3 hardened `GET /api/v1/settings/shell` onto the shared active-user authorization path.
- Wave 3 Phase 9 sanitized `backend/diagnostic.py` so it no longer prints password hashes or the old `admin123` check output.
- In the current repo:
- `backend/app/api/settings/routes.py` already protects `GET /api/v1/settings/shell` with `@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")`.
- `backend/diagnostic.py` already uses a redacted database-URI formatter and no longer prints password hashes or verifies `admin123`.
- The one requirement from the user prompt that is not yet explicit in code wording is the top-of-file support-only warning for `backend/diagnostic.py`:
- make clear it is a local support-only tool
- make clear it must not be committed with real credentials
- make clear it must not be run on production instances
- Existing tests already cover part of this surface:
- `backend/tests/test_phase9_ops.py` checks diagnostic output safety
- `backend/tests/test_settings.py` checks shell access for active roles plus inactive/nonexistent-user rejection
- Because the repo is already mostly aligned, this phase is a narrow regression audit and explicit contract-lock pass.
- Do not reopen accepted Wave 3 scope unless you find a real current regression in the repo.

Contract Locks / Clarifications
- Do not change the `GET /api/v1/settings/shell` response payload.
- Do not narrow `/settings/shell` access to `ADMIN` only; it must remain available to any authenticated active user role.
- Do not change auth route URLs, JWT handling, settings payload shapes, or other settings-route permissions outside this specific shell authorization check.
- For `backend/diagnostic.py`, do not redesign the helper or broaden output changes beyond removing sensitive material and adding the explicit support-only warning.
- No frontend work is in scope for this phase.
- No documentation-agent work is in scope for this phase.

Delegation Plan
- Backend:
- audit the existing `diagnostic.py` and `/settings/shell` implementation against the new Phase 4 prompt
- make only the minimal backend code change(s) still needed in the current repo
- Testing:
- tighten or extend regression coverage so this phase's exact security contract is obvious and locked

Acceptance Criteria
- `backend/diagnostic.py` does not print any password hash.
- `backend/diagnostic.py` does not print or check `admin123`.
- `backend/diagnostic.py` does not emit a plaintext database password in `DATABASE_URI` output.
- `backend/diagnostic.py` has a visible top-of-file warning that it is a local support-only tool and must not be committed with real credentials or run on production instances.
- `GET /api/v1/settings/shell` is protected through the standard active-user authorization path (`require_role(...)` or equivalent shared helper with current-user active validation).
- Active authenticated users can still load `/api/v1/settings/shell` successfully.
- A deactivated user's still-valid JWT is rejected on `/api/v1/settings/shell`.
- New or updated tests pass and clearly lock the accepted contract.
- The phase leaves complete backend + testing + orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first because the repo is already mostly aligned and testing should lock the final backend state, not an outdated assumption.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 4 Phase 4 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-008`, `F-SEC-009`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/orchestrator.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/orchestrator.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/utils/auth.py`
- `backend/app/api/settings/routes.py`
- `backend/diagnostic.py`
- `backend/tests/test_phase9_ops.py`
- `backend/tests/test_settings.py`

Goal
- Finish any remaining minimal backend hardening needed for `F-SEC-008` and `F-SEC-009` without reopening already accepted Wave 3 work.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation files plus `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/backend.md`.
- Do not edit frontend files, README/docs files, or historical handoff files in this phase.
- Prefer leaving test-file changes to the testing agent unless a tiny backend-owned adjustment is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- `backend/diagnostic.py` is already mostly sanitized:
- it uses a redacted database-URI formatter
- it no longer prints password hashes
- it no longer checks or prints `admin123`
- `backend/app/api/settings/routes.py` already uses `@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")` on `GET /api/v1/settings/shell`.
- That means this phase is not greenfield implementation. Audit first, then make only the minimum remaining change(s) needed.
- The likely remaining backend delta is the explicit top-of-file support-only warning in `backend/diagnostic.py`, unless you find a real regression.

Non-Negotiable Contract Rules
- Do not change the `/settings/shell` payload.
- Do not narrow `/settings/shell` access below "any authenticated active user".
- Do not change other settings-route authorization rules.
- Do not redesign `diagnostic.py` or add unrelated new output.
- Do not reopen Wave 3 build/deploy tooling scope.

Tasks
1. `F-SEC-008` — diagnostic script hardening:
- Audit `backend/diagnostic.py` against the current repo state.
- Ensure any `DATABASE_URI` output remains redacted and never exposes the plaintext password component.
- Ensure there is no password-hash output.
- Ensure there is no `admin123` verification block or output.
- Add a visible comment/docstring warning near the top of the file making clear that:
- this is a local support-only tool
- it must not be committed with real credentials
- it must not be run on production instances
- Do not change other safe operator output unnecessarily.
2. `F-SEC-009` — `/settings/shell` authorization:
- Audit `backend/app/api/settings/routes.py` and `backend/app/utils/auth.py`.
- If `/settings/shell` is already protected through the shared active-user authorization path, do not churn it.
- If you discover any drift from the standard active-user path, fix it narrowly.
- Keep the route available to active authenticated roles:
- `ADMIN`
- `MANAGER`
- `WAREHOUSE_STAFF`
- `VIEWER`
- `OPERATOR`
- Keep the shell payload unchanged.
3. Keep the implementation diff minimal and explain clearly in handoff whether this phase required:
- a real backend code change
- or only confirmation that prior accepted hardening still holds

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_settings.py -q`
- `cd backend && venv/bin/python diagnostic.py`
- `rg -n "password_hash|admin123|DATABASE_URI|require_role\\(" backend/diagnostic.py backend/app/api/settings/routes.py backend/app/utils/auth.py`
- `git diff -- backend/diagnostic.py backend/app/api/settings/routes.py`
- If `diagnostic.py` requires an explicit disposable env to run safely in your verification, use one and record the exact env/command in handoff.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- whether `diagnostic.py` still needed code changes or was already aligned
- how the database URI is redacted
- confirmation that no password-hash/admin123 output remains
- whether `/settings/shell` needed an authorization change or was already aligned
- any residual risk intentionally left out of scope
- If you discover a genuine cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- Any remaining backend gap for `F-SEC-008` / `F-SEC-009` is closed with a minimal diff.
- No accepted earlier hardening is regressed.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 4 Phase 4 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-008`, `F-SEC-009`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/orchestrator.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/orchestrator.md`
- backend handoff for this phase after backend finishes
- `backend/diagnostic.py`
- `backend/app/api/settings/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_phase9_ops.py`
- `backend/tests/test_settings.py`

Goal
- Lock the exact `F-SEC-008` and `F-SEC-009` security contract with targeted regression coverage, while respecting that the repo is already mostly hardened from accepted Wave 3 work.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files plus `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/testing.md`.
- Do not broaden into runtime code changes or doc rewrites unless you hit a true blocker and document it clearly.

Current Repo Reality You Must Respect
- Existing tests already cover part of this space:
- `backend/tests/test_phase9_ops.py` checks that diagnostic output avoids password-hash / `admin123` leakage
- `backend/tests/test_settings.py` already covers `/settings/shell` access for active roles and rejection for inactive/nonexistent users
- This phase should make the current prompt's exact guarantees explicit, not duplicate tests without improving clarity.

Non-Negotiable Contract Rules
- Keep the `/settings/shell` payload contract unchanged.
- Keep `/settings/shell` available to active authenticated users across the allowed roles.
- The key testing goal is to make the security contract obvious to future reviewers.
- Prefer tightening existing test modules over scattering new files unless a small new file is clearly cleaner.

Minimum Required Coverage
1. `F-SEC-008` — diagnostic script hardening:
- Assert that diagnostic output does not contain any password hash.
- Assert that diagnostic output does not contain any reference to `admin123`.
- Assert that any `DATABASE_URI` output does not expose a plaintext password component.
- If helpful, assert the redacted output still remains operationally useful (for example, it still indicates that a DB URI is configured without leaking the secret).
- If the new top-of-file warning in `diagnostic.py` lands, add a narrow source-level assertion only if that is the clearest way to lock the requirement without brittle output coupling.
2. `F-SEC-009` — `/settings/shell` authorization:
- Assert that an active authenticated user can still access `GET /api/v1/settings/shell` successfully.
- Assert that a deactivated user's still-valid JWT is rejected.
- Keep the assertion grounded in the active-user auth path used by the real route, not a mocked shortcut.
3. Regression clarity:
- Reuse and tighten `backend/tests/test_phase9_ops.py` and `backend/tests/test_settings.py` where that keeps the contract easiest to discover.
- If current tests already cover a scenario, improve names/assertions only where needed to match the exact phase contract.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_settings.py -q`
- If you add or significantly tighten `/settings/shell` auth tests, also run the smallest targeted auth/settings slice that proves they are stable.
- Record exact results in handoff.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which diagnostic-output guarantees are now explicitly locked
- which `/settings/shell` active/inactive auth guarantees are explicitly locked
- whether you reused existing test modules or introduced a new one
- any residual ambiguity or out-of-scope risk

Done Criteria
- The Phase 4 security contract is obvious from the tests.
- Diagnostic safety and shell active-user authorization are locked against regression.
- Verification is recorded in handoff.

## [2026-04-05 17:36 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend and testing handoffs for Wave 4 Phase 4.
- Compared the handoff claims against the actual repo worktree and targeted diffs.
- Re-ran the delegated verification suite and a direct runtime smoke of `backend/diagnostic.py`.
- Validated that this phase stayed intentionally narrow and did not reopen already accepted Wave 3 behavior.

Docs Read
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/orchestrator.md`
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/backend.md`
- `handoff/wave-04/phase-04-wave-04-diagnostic-and-settings-shell-hardening/testing.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/orchestrator.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `backend/diagnostic.py`
- `backend/app/api/settings/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_phase9_ops.py`
- `backend/tests/test_settings.py`

Commands Run
```bash
git status --short
git diff -- backend/diagnostic.py backend/tests/test_phase9_ops.py backend/tests/test_settings.py
sed -n '1,120p' backend/diagnostic.py
sed -n '1,70p' backend/app/api/settings/routes.py
sed -n '1080,1195p' backend/tests/test_settings.py
cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_settings.py -q
cd backend && venv/bin/python diagnostic.py
cd backend && venv/bin/python - <<'PY'
import diagnostic as diagnostic_module
for raw in [
    'postgresql://dbuser:SuperSecret123@db.internal:5432/stoqio',
    'postgresql://dbuser@db.internal:5432/stoqio',
    None,
]:
    print(repr(raw), '=>', diagnostic_module._redacted_database_uri(raw))
PY
```

Findings
- None.

Validation Result
- Passed:
- `backend/diagnostic.py` now carries an explicit `WARNING — LOCAL SUPPORT TOOL ONLY` block near the top of the file.
- `backend/diagnostic.py` still avoids password-hash output and any `admin123` verification/output.
- Direct helper smoke confirms `DATABASE_URI` output is redacted and does not expose the plaintext password:
- runtime output on this workspace: `postgresql://grzzi@localhost/wms_dev`
- helper proof with password-bearing URI: `postgresql://dbuser:***@db.internal:5432/stoqio`
- `GET /api/v1/settings/shell` remains protected through `@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")`, which uses the shared active-user validation path in `backend/app/utils/auth.py`.
- Existing shell tests still cover:
- all five active authenticated roles -> `200`
- anonymous request -> `401`
- deactivated user with still-valid JWT -> `401`
- nonexistent/deleted user with JWT -> `401`
- New Phase 4 regression locks in `backend/tests/test_phase9_ops.py` make the diagnostic redaction and support-only warning explicit without duplicating route behavior unnecessarily.
- `cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_settings.py -q` -> `81 passed in 63.89s`
- `cd backend && venv/bin/python diagnostic.py` emitted only safe status output and no plaintext password.

Closeout Decision
- Wave 4 Phase 4 is accepted and closed.

Accepted Baseline After Phase 4
- `backend/diagnostic.py` is now explicitly documented in-code as a local support-only helper and remains free of credential-sensitive output.
- Database URI display in diagnostics remains redacted: useful for support, but without plaintext password leakage.
- `/api/v1/settings/shell` continues to use the shared active-user authorization path and should be treated as already hardened baseline behavior, not a future TODO.
- The test suite now makes both the diagnostic redaction contract and the shell active-user contract easier to rediscover during later security work.

Next Action
- Wave 4 Phase 4 is complete.
- Future work should treat `F-SEC-008` and `F-SEC-009` as closed unless a concrete new regression is found.
