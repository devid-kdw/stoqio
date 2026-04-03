## Phase Summary

Phase
- Wave 3 - Phase 9 - Ops & Diagnostic Hardening

Objective
- Harden operator-facing diagnostic and deployment tooling without changing product behavior, API/runtime contracts, or the accepted local-host deployment model.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-010`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-017`, `DEC-FE-006`)
- `handoff/wave-03/phase-08-wave-03-inventory-count-frontend-refactor/orchestrator.md`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-025`, `F-027`)
- `backend/diagnostic.py`
- `backend/seed.py`
- `backend/.env.example`
- `scripts/build.sh`
- `scripts/deploy.sh`

Current Repo Reality
- Wave 3 Phase 8 is accepted and is the current baseline. This phase should not broaden into product feature work.
- `backend/diagnostic.py` currently:
- loads `.env`
- creates the full Flask app
- prints the configured database URI
- prints whether the `admin` user exists
- prints all usernames/roles if `admin` is missing
- prints the stored password hash for `admin`
- prints whether `admin123` matches that hash
- This is not safe operator-facing diagnostic output.
- `backend/seed.py` still seeds the default bootstrap admin user `admin / admin123`. That broader bootstrap/security policy is not this phase's redesign scope, but the diagnostic helper must stop exposing credential-sensitive details about it.
- `scripts/build.sh` currently assumes frontend dependencies already exist and simply runs `npm run build`, then wipes and recopies `backend/static/`.
- `scripts/deploy.sh` currently:
- runs `git pull origin main`
- installs backend requirements into the active `python3` environment
- calls `./scripts/build.sh`
- runs Alembic with a bare `alembic upgrade head`
- restarts `wms` via `systemctl` when available
- The script does not currently make frontend dependency installation explicit, does not clearly enforce/communicate backend interpreter or virtualenv expectations, and relies mostly on shell-default failure behavior.
- Current docs already position STOQIO as a local-host/server deployment project and describe a non-Pi-specific Linux/systemd model, but the actual script behavior and the documented behavior have drifted. In particular, the docs describe a more self-sufficient frontend install/build step than the current scripts actually implement.
- `handoff/README.md` defines the standard `backend.md`, `frontend.md`, and `testing.md` agent files only. This phase also needs an ops/devops handoff and a documentation handoff, so the orchestrator must define explicit extra handoff files for those agents.

Contract Locks / Clarifications
- No product behavior changes are in scope.
- Do not change API contracts, JWT lifetimes, auth bootstrap semantics, role behavior, setup flow, or user-visible module behavior.
- No frontend product-code changes are expected in this phase unless a tiny supporting smoke fixture is truly required by testing.
- Do not redesign the bootstrap admin credential policy in `seed.py` during this phase. The hard requirement here is to stop operational tooling from exposing credential-sensitive information.
- `backend/diagnostic.py` may be removed, replaced, or retained, but if it remains it must be clearly safe for operator use and its scope must be explicit.
- Preserve the accepted local-host deployment model already used by this repo:
- local Linux server / mini PC / Windows-hosted local deployment remains valid
- do not add Raspberry Pi-only assumptions
- do not assume cloud CI/CD infrastructure
- Hardening the scripts may include:
- lockfile-aware frontend dependency installation before build
- explicit backend interpreter / virtualenv expectation handling
- clearer precondition checks and failure messages
- safer shell behavior
- Documentation must match the actual final script behavior precisely. Do not leave "wishful docs" that describe steps the scripts still do not perform.
- Special handoff rule for this phase:
- Backend agent writes `backend.md`
- Ops/devops agent writes `ops.md`
- Testing agent writes `testing.md`
- Documentation agent writes `documentation.md`
- `ops.md` and `documentation.md` must use the same section shape required by `handoff/README.md` for standard agent files.

Delegation Plan
- Backend:
- sanitize, retire, or redesign `backend/diagnostic.py` so it is safe and operator-appropriate
- Ops / DevOps:
- harden `scripts/build.sh` and `scripts/deploy.sh` to be more self-sufficient and less environment-fragile while preserving the accepted deployment model
- Testing:
- add practical smoke/regression coverage around the hardened tooling where feasible in-repo
- document manual host-level verification that cannot be safely executed in this environment
- Documentation:
- update README / deployment docs so operator instructions match the actual hardened scripts and diagnostic behavior

Acceptance Criteria
- `backend/diagnostic.py` no longer exposes password hashes, password-match checks, or comparable credential-sensitive output.
- If `backend/diagnostic.py` remains, its safe operator scope is clear in code and docs.
- `scripts/build.sh` and `scripts/deploy.sh` are more self-sufficient and less brittle around frontend dependency installation, backend environment expectations, and failure behavior.
- The accepted local-host deployment model remains intact and is not narrowed to Raspberry Pi-specific assumptions.
- README / deployment docs match the final script behavior and any required operator steps.
- Practical automated smoke verification is added where it fits the repo, and manual verification steps are recorded for the remaining host-level checks.
- No unintended product behavior change is introduced.
- The phase leaves complete backend, ops, testing, documentation, and orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend and Ops in parallel because their write scopes are disjoint.
- Testing should run after Backend/Ops delivery is available.
- Documentation should run after the final diagnostic/script behavior is known.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 9 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-010`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-017`, `DEC-FE-006`)
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `backend/diagnostic.py`
- `backend/seed.py`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-025`)

Goal
- Retire, sanitize, or redesign `backend/diagnostic.py` so it is safe for operator use and no longer exposes credential-sensitive information.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation files plus `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/backend.md`.
- Do not edit docs files in this phase. The documentation agent owns docs changes.
- Prefer leaving backend test changes to the testing agent unless a tiny backend-owned test is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- `backend/diagnostic.py` currently prints:
- database URI
- admin presence/state
- full username listing when admin is missing
- admin password hash
- whether `admin123` matches
- `backend/seed.py` still seeds the bootstrap admin user and reference data. This phase does not redesign that bootstrap policy.
- `diagnostic.py` currently loads `.env` and initializes the full Flask app, so any retained diagnostic path should remain aligned with the real configured backend environment rather than inventing a separate config path.

Non-Negotiable Contract Rules
- Do not print password hashes, password-match checks, raw secrets, JWT secrets, or comparable credential-sensitive output.
- Do not broaden this into a redesign of seed/bootstrap auth policy.
- If `diagnostic.py` remains in the repo, make its intended safe scope obvious in code comments/docstring/output.
- Keep the change set narrow and operational.
- Do not change auth runtime behavior, API routes, or product flows.

Tasks
1. Audit `backend/diagnostic.py` and decide whether the safest Phase 9 outcome is:
- sanitize and keep it
- replace it with a safer diagnostic pattern
- or retire it with a clearer/operator-safe alternative
2. Ensure the final operator-facing behavior no longer prints:
- password hash values
- whether `admin123` matches
- any other credential-sensitive output
3. If the file remains, make its intended scope explicit in its top-level docstring/comments and in its output shape.
4. Keep any remaining output focused on safe operational facts only.
5. Record clearly in handoff whether the file was retained, redesigned, or retired and why.

Verification
- Run at minimum:
- `cd backend && venv/bin/python diagnostic.py`
- `git diff -- backend/diagnostic.py`
- If you introduce any supporting backend file, run the smallest targeted verification needed and record it.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- whether the diagnostic helper was retained or retired
- what sensitive output was removed
- any residual operational risk
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- The diagnostic path no longer exposes credential-sensitive information.
- Its intended safe operational scope is clear.
- Verification is recorded in handoff.

## Delegation Prompt - Ops Agent

You are the ops/devops agent for Wave 3 Phase 9 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-010`)
- `handoff/README.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-027`)
- `scripts/build.sh`
- `scripts/deploy.sh`
- `backend/.env.example`
- `frontend/package.json`
- `frontend/package-lock.json`

Goal
- Harden `scripts/build.sh` and `scripts/deploy.sh` so deployment is more self-sufficient and less environment-fragile, without changing product behavior or narrowing the accepted local-host deployment model.

Special handoff rule for this phase
- `handoff/README.md` does not define a standard ops-agent file.
- Append your work log to `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md`.
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
- Your ownership is limited to `scripts/` plus `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md`.
- Do not edit README or architecture docs in this phase. The documentation agent owns docs updates.
- Do not edit backend implementation files unless you discover a true blocker that cannot be solved inside `scripts/`; if that happens, stop and document the blocker instead of expanding scope silently.

Current Repo Reality You Must Respect
- `scripts/build.sh` currently runs only `npm run build` and assumes frontend dependencies are already installed.
- `scripts/deploy.sh` currently uses the active `python3` / `pip` environment directly, calls `git pull`, then runs build + migrations + restart.
- `frontend/package-lock.json` exists, so a lockfile-aware install path is possible.
- The accepted local-host deployment model is broader than Raspberry Pi; Linux systemd examples are valid, but the scripts must not become Pi-only.

Non-Negotiable Contract Rules
- Do not change product/runtime behavior.
- Preserve the local-host deployment model already accepted in the repo.
- Do not introduce Raspberry Pi-only assumptions or hardware-specific paths.
- Harden the scripts at minimum around:
- frontend dependency installation before build
- explicit backend interpreter / virtualenv expectations
- clearer failure behavior and operator messages
- Keep the scripts practical for a single local server deployment maintained by an operator, not a cloud CI pipeline.
- Avoid broad/destructive script changes unrelated to this hardening goal.

Tasks
1. Harden `scripts/build.sh` so frontend dependency installation/build is more self-sufficient and lockfile-aware.
2. Harden `scripts/deploy.sh` so backend environment expectations are explicit and less fragile.
3. Improve failure clarity:
- make missing prerequisites obvious
- make the backend/python environment path clearer
- make script flow easier for an operator to reason about
4. Preserve the current local-host deployment flow shape where reasonable:
- update repo
- install dependencies
- build frontend
- apply migrations
- restart service when appropriate
5. Keep the final behavior documentation-friendly so the documentation agent can describe it clearly without caveats that contradict the scripts.

Verification
- Run at minimum:
- `bash -n scripts/build.sh`
- `bash -n scripts/deploy.sh`
- any safe local dry-run/smoke command you can perform without doing a destructive real deploy
- record clearly what you could not safely execute in this environment

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md`.
- Use the standard section shape listed above.
- Record:
- files changed
- commands run
- what script fragility was reduced
- what environment assumptions are now explicit
- any residual host-level risk or manual step

Done Criteria
- Build/deploy scripts are clearer and less brittle.
- Frontend dependency install/build behavior is more self-sufficient.
- Backend environment expectations are explicit.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 9 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-010`)
- `handoff/README.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- backend handoff for this phase after backend finishes
- ops handoff for this phase after ops finishes
- `backend/diagnostic.py`
- `scripts/build.sh`
- `scripts/deploy.sh`
- existing relevant test files under `backend/tests/`

Goal
- Add practical smoke verification for the hardened operational tooling and document the remaining manual checks for host-level behavior that cannot be safely exercised here.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to test files plus `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/testing.md`.

Non-Negotiable Contract Rules
- Focus on practical verification, not a broad product regression sweep beyond what the touched tooling warrants.
- Do not broaden into frontend product behavior changes.
- Prefer stable smoke/regression checks over brittle implementation-detail assertions.
- Do not execute a real destructive deploy in this environment.

Minimum Required Coverage / Verification
1. Add any practical in-repo smoke verification that fits the final implementation, for example:
- script syntax/structure checks
- safe subprocess-based checks
- diagnostic-output safety assertions
- other lightweight automation that does not require a real host restart
2. Revalidate that:
- `diagnostic.py` no longer exposes credential-sensitive output
- the hardened script flow is at least syntactically/safely smoke-checked
3. Document manual verification for:
- clean frontend build on a fresh dependency install
- deploy script behavior on a local host/server
- diagnostic script output safety

Testing Guidance
- Be pragmatic. A combination of small automated smoke checks plus explicit manual verification notes is acceptable if full host-level deploy execution is unsafe here.
- If you add subprocess/script tests, keep them robust and avoid assumptions that only hold on one machine.
- Record clearly what was automated versus what remains manual/operator-level.

Verification
- Run the relevant automated smoke/tests you add.
- Also run any existing targeted verification that meaningfully covers the touched operational tooling.
- Record exact commands and outcomes in handoff.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- automated checks added/run
- manual verification checklist
- residual risks

Done Criteria
- Practical smoke verification exists for the hardened tooling where feasible.
- Manual verification steps are documented for the remaining host-level checks.
- Verification is recorded in handoff.

## Delegation Prompt - Documentation Agent

You are the documentation agent for Wave 3 Phase 9 of the STOQIO WMS project.

Read before editing:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-010`)
- `handoff/README.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- backend handoff for this phase after backend finishes
- ops handoff for this phase after ops finishes
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/diagnostic.py`
- `scripts/build.sh`
- `scripts/deploy.sh`

Goal
- Update README / deployment docs so operator instructions match the final hardened script and diagnostic behavior.

Special handoff rule for this phase
- `handoff/README.md` does not define a standard documentation-agent file.
- Append your work log to `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/documentation.md`.
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
- Your ownership is limited to documentation files plus `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/documentation.md`.

Non-Negotiable Contract Rules
- Document the behavior that actually landed. Do not describe script steps that do not really happen.
- Keep the docs aligned with the accepted local-host deployment model already used by the repo.
- Mention any required operator steps clearly.
- Do not broaden into unrelated product-doc cleanup.

Tasks
1. Update the relevant docs to reflect the final hardened behavior of:
- `backend/diagnostic.py`
- `scripts/build.sh`
- `scripts/deploy.sh`
2. Make required operator steps explicit.
3. Call out any important environment expectation the scripts now rely on.
4. Keep the wording practical for a local-host/server operator.

Verification
- Review the backend and ops deliveries to ensure the docs match the actual implementation.
- Record any manual doc verification you performed.

Done Criteria
- README / deployment docs match the hardened script behavior.
- Required operator steps are clear.
- Documentation changes and handoff are recorded.

## [2026-04-03 17:13 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend, ops, testing, and documentation work for Wave 3 Phase 9.
- Compared the agent handoffs against the actual repo diff.
- Re-ran targeted verification for the hardened diagnostic helper, the new Phase 9 smoke coverage, the touched auth regression slice, the shell-script syntax checks, and the rebuilt frontend asset flow.
- Accepted the phase with the explicit note that a real host-level `./scripts/deploy.sh` restart smoke remains a manual operator check because it performs `git pull` and service restart side effects.

Docs Read
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/backend.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/testing.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/documentation.md`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `backend/diagnostic.py`
- `backend/tests/test_phase9_ops.py`
- `scripts/build.sh`
- `scripts/deploy.sh`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`

Commands Run
```bash
git status --short
git diff -- backend/diagnostic.py scripts/build.sh scripts/deploy.sh backend/tests/test_phase9_ops.py README.md stoqio_docs/07_ARCHITECTURE.md handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/backend.md handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/testing.md handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/documentation.md
bash -n scripts/build.sh && bash -n scripts/deploy.sh
cd backend && venv/bin/python diagnostic.py
cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_auth.py -q
./scripts/build.sh
```

Findings
- None.

Validation Result
- Passed:
- `backend/diagnostic.py` is now explicitly a safe operator helper:
- no password hash output
- no `admin123` password-match output
- no full user-list dump
- configured database URI is redacted
- unavailable database now yields a safe status message instead of leaking or crashing
- `scripts/build.sh` is now more self-sufficient and explicit:
- requires `npm`
- requires `frontend/package-lock.json`
- runs `npm ci --include=dev --no-audit --no-fund` before build
- fails fast with a clearer trap/error message
- `scripts/deploy.sh` is now clearer and less environment-fragile:
- defaults backend interpreter to `backend/venv/bin/python`
- allows `BACKEND_VENV_DIR` / `BACKEND_PYTHON` override
- uses `git pull --ff-only`
- installs backend requirements and runs Alembic through the explicit backend interpreter
- prints clearer step/failure messages
- new automated smoke coverage in `backend/tests/test_phase9_ops.py` locks:
- safe diagnostic output with a populated test DB
- safe diagnostic output when the configured database is unavailable
- shell syntax validity for `scripts/build.sh`
- shell syntax validity for `scripts/deploy.sh`
- targeted backend regression verification passed:
- `cd backend && venv/bin/python -m pytest tests/test_phase9_ops.py tests/test_auth.py -q` -> `53 passed`
- direct diagnostic verification passed:
- `cd backend && venv/bin/python diagnostic.py` emitted only safe status output
- script syntax verification passed:
- `bash -n scripts/build.sh && bash -n scripts/deploy.sh`
- rebuilt frontend asset flow passed:
- `./scripts/build.sh` completed successfully and recopied fresh assets into `backend/static`
- docs are now aligned with the actual hardened behavior in:
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`

Closeout Decision
- Wave 3 Phase 9 is accepted and closed.

Residual Notes
- A real host-level `./scripts/deploy.sh` end-to-end smoke remains a manual operator step because it performs `git pull` and can restart the `wms` service. This is documented in the testing handoff and is not a blocker for phase acceptance.

Next Action
- Treat the current worktree and this orchestrator closeout as the accepted Wave 3 Phase 9 baseline.
- Proceed to Wave 3 Phase 10 - Contract Codification & Docs Alignment.
