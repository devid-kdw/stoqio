## Phase Summary

Phase
- Wave 7 - Phase 3 - Backend Process and Documentation Cleanup

Objective
- Remediate eight process/docs/low-severity findings from the 2026-04-08 dual-agent code review:
  M-8 (seed.py uses pbkdf2 instead of scrypt),
  L-1 (report pagination malformed int can return 500),
  N-4 (transaction log pagination passes unparsed strings),
  L-3 (stale pbkdf2 comment in auth.py),
  L-4 (Wave 6 frontend handoff stale about eslint-plugin-security),
  L-5 (Wave 6 verification notes conflict between orchestrator and agent handoffs),
  L-6 (README revoked-token cleanup docs outdated),
  L-7 (requirements.lock contains stale python-barcode).

Source Docs
- `handoff/README.md`
- `handoff/wave-07/README.md`
- `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (M-8, L-1, L-3 through L-7)
- `handoff/Findings/wave-06-second-opinion-review.md` (M-8, L-1, N-4, L-3 through L-7)
- `handoff/decisions/decision-log.md` (DEC-SEC-002 for scrypt policy)
- `backend/seed.py`
- `backend/app/api/reports/routes.py`
- `backend/app/utils/auth.py`
- `backend/tests/test_seed_hardening.py`
- `backend/tests/test_auth.py`
- `backend/requirements.txt`
- `backend/requirements.lock`
- `README.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/backend.md`

Current Repo Reality
- `seed.py:73` uses `generate_password_hash(password, method="pbkdf2:sha256")` which conflicts
  with DEC-SEC-002 (scrypt policy). Lazy migration on login exists but requires the seed admin
  to log in before rehash occurs; if the account is never used interactively, the pbkdf2 hash
  persists indefinitely.
- `app/api/reports/routes.py:22-23` and `71-72` call `int()` directly on query params with no
  try/except. Other modules use a `parse_positive_int()` helper. ValueError becomes a 500.
- `app/api/reports/routes.py:113-114` passes pagination params as raw strings to the service for
  the transaction log endpoint, inconsistent with the other two report pagination paths.
- `app/utils/auth.py:19` comment reads "Using pbkdf2:sha256 keeps this aligned with the app's
  supported hash policy." The code at line 22 uses `method="scrypt"`. Comment is stale.
- `backend/tests/test_auth.py` has test names/doc wording referencing pbkdf2 while asserting scrypt.
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md` says eslint-plugin-security
  is pending/commented. The actual state: plugin is installed and active in eslint.config.js.
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md:105` claims tests
  passed (567 backend, 41 frontend) while the backend and frontend handoff files explicitly state
  tests were not run due to Bash tool denial. These claims are mutually exclusive.
- `README.md:66` states revoked-token cleanup "is never run automatically on requests, startup, or
  logout." `app/__init__.py` has a `before_request` hook running cleanup at most once per hour.
- `requirements.lock:32` pins `python-barcode==0.16.1`. It is not in `requirements.txt`.
  `barcode_service.py` uses `reportlab.graphics.barcode`, not python-barcode. The venv binary
  `venv/bin/python-barcode` is present (installed transitively). Lock file should not include
  packages absent from requirements.txt.

Contract Locks / Clarifications
- **M-8 seed.py scrypt**: Change `method="pbkdf2:sha256"` to `method="scrypt"` at `seed.py:73`.
  Update `test_seed_hardening.py` to assert that the seeded admin hash starts with `"scrypt:"`.
  This is consistent with DEC-SEC-002.
- **L-1 + N-4 report pagination**: Find the `parse_positive_int()` helper used by other API modules
  (check `app/api/employees/routes.py:50` for the import pattern). Apply it to all three pagination
  paths in `reports/routes.py` (stock overview page, surplus page, transaction log page).
  For the transaction log path, if it currently passes raw strings to the service, convert them
  to int via `parse_positive_int()` at the route layer before passing to the service.
- **L-3 stale comment**: Update `auth.py:19` comment to accurately describe the scrypt policy.
  Update any test names or docstrings in `test_auth.py` that reference pbkdf2 while testing scrypt.
- **L-4 stale handoff**: Append a correction note to
  `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md` (do NOT overwrite the
  existing entry — append only per handoff protocol). Note that the eslint-plugin-security manual
  install was completed and the plugin is now active.
- **L-5 verification conflict**: Append a correction note to
  `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md` Validation Notes
  section (append only) clarifying that the orchestrator verification claim at line 105 was
  aspirational — the backend and frontend agents did not execute the test suite due to Bash tool
  restrictions. Future agents should not rely on that verification claim without re-running tests.
- **L-6 README**: Update `README.md` revoked-token cleanup section to accurately describe both
  the automatic hourly `before_request` cleanup AND the manual CLI command. Do not remove the
  manual CLI docs.
- **L-7 requirements.lock**: Remove the `python-barcode==0.16.1` line from `requirements.lock`.
  Verify no source file imports `python_barcode` or `barcode` (the python-barcode top-level
  module) before removing. If unsure, grep for `import barcode` and `from barcode` in the
  backend source. Note in backend.md that the lock file should be regenerated from a clean venv
  built from requirements.txt to fully resolve future drift.
- Do NOT run `pip install` or regenerate requirements.lock from scratch (agents cannot use the
  network). Manually remove the stale line.
- Do NOT change the Wave 6 orchestrator.md content other than appending the correction note.

File Ownership (this phase only — do not touch other files)
- `backend/seed.py`
- `backend/tests/test_seed_hardening.py`
- `backend/tests/test_auth.py` (comment/name updates only)
- `backend/app/api/reports/routes.py`
- `backend/app/utils/auth.py` (comment update only)
- `backend/requirements.lock`
- `README.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md` (append only)
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md` (append only)
- `handoff/wave-07/phase-03-wave-07-backend-process-and-docs/backend.md`

Delegation Plan
- Backend: implement all fixes above, run tests, document

Acceptance Criteria
- `seed.py` admin hash uses scrypt (hash starts with `"scrypt:"`)
- `test_seed_hardening.py` asserts scrypt
- Malformed `page` or `per_page` on stock overview, surplus, and transaction log endpoints returns HTTP 400, not 500
- `auth.py:19` comment accurately describes scrypt
- `test_auth.py` test names do not reference pbkdf2 when testing scrypt behavior
- Wave 6 Phase 4 frontend.md has a correction note appended
- Wave 6 Phase 4 orchestrator.md has a correction note appended to Validation Notes
- `README.md` accurately describes both automatic and manual revoked-token cleanup
- `requirements.lock` does not contain `python-barcode`
- All pre-existing backend tests pass

Validation Notes
- 2026-04-08: Orchestrator created Wave 7 Phase 3. Runs in parallel with Phases 1, 2, 4, 5.
- 2026-04-08: Phase 3 agent completed all eight fixes. One regression introduced: parse_positive_int applied to transaction log per_page used default=100 instead of the service default of 50, and did not handle empty strings as defaults. Orchestrator fixed reports/routes.py: added `or None` to all three pagination endpoints to treat empty strings as defaults, and corrected transaction log per_page default to 50. Full backend suite: 579 passed, 0 failed. Phase 3 closed.

Next Action
- Backend agent implements. Can run simultaneously with Phases 1, 2, 4, 5.

---

## Delegation Prompt — Backend Agent

You are the backend process and documentation cleanup agent for Wave 7 Phase 3 of the STOQIO
WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-07/phase-03-wave-07-backend-process-and-docs/orchestrator.md` (this file)
- `handoff/decisions/decision-log.md` (find DEC-SEC-002 for scrypt policy)
- `backend/seed.py`
- `backend/tests/test_seed_hardening.py`
- `backend/tests/test_auth.py`
- `backend/app/api/reports/routes.py`
- `backend/app/api/employees/routes.py` (for parse_positive_int import pattern)
- `backend/app/utils/auth.py`
- `backend/requirements.lock`
- `README.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`

Your fixes (implement all of them):

1. **M-8: seed.py scrypt** (`backend/seed.py`)
   Change `method="pbkdf2:sha256"` to `method="scrypt"` in the admin password hash generation.
   Then update `backend/tests/test_seed_hardening.py` to assert the seeded admin hash starts
   with `"scrypt:"` instead of `"pbkdf2:"`.

2. **L-1 + N-4: Report pagination error handling** (`backend/app/api/reports/routes.py`)
   Find how `parse_positive_int()` is imported and used in another route module (e.g., employees).
   Apply `parse_positive_int()` to the `page` and `per_page` parameters in all three report
   pagination paths:
   - Stock overview pagination (currently bare `int()` calls)
   - Surplus pagination (currently bare `int()` calls)
   - Transaction log pagination (currently passing raw strings — convert to int here)
   This ensures malformed input returns HTTP 400 instead of a 500 crash.

3. **L-3: Stale comment in auth.py** (`backend/app/utils/auth.py`)
   Update the comment at line 19 (or wherever it appears) that references pbkdf2:sha256 as the
   policy. Replace it with a comment accurately describing that the app uses scrypt (per DEC-SEC-002)
   and that the dummy hash uses the same algorithm for timing-safe comparison.
   In `backend/tests/test_auth.py`, update any test names or docstrings that reference pbkdf2
   while asserting scrypt behavior. Code logic must NOT change — only comments and test names.

4. **L-4: Wave 6 frontend handoff correction** (append to existing file)
   Open `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`.
   Append (do NOT overwrite) a dated correction note:
   ```
   ## [2026-04-08] Wave 7 Phase 3 — Correction Note
   Status: correction
   The eslint-plugin-security manual install referenced above was completed after the Wave 6 Phase 4
   agent run. As of the Wave 7 review (2026-04-08), eslint-plugin-security is installed (package.json)
   and active (eslint.config.js imports and applies security.configs.recommended). The "pending manual
   install" and "commented-out" references in the original entry no longer reflect repo state.
   ```

5. **L-5: Wave 6 verification conflict correction** (append to existing file)
   Open `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`.
   Append to the Validation Notes section:
   ```
   - 2026-04-08 (Wave 7 Phase 3 correction): The 2026-04-08 10:45 CEST validation note claiming
     "567 passed, build ✓, 41/41 tests ✓" was aspirational. Both the backend.md and frontend.md
     for this phase explicitly state tests were NOT run due to Bash tool restrictions. Future agents
     must not rely on the orchestrator's verification claim without re-running the test suite.
   ```

6. **L-6: README revoked-token cleanup** (`README.md`)
   Find the section that says cleanup "is never run automatically on requests, startup, or logout."
   Update it to accurately describe both mechanisms:
   - Automatic cleanup: runs at most once per hour via a `before_request` hook in `app/__init__.py`
     (deletes revoked_token rows whose `expires_at` is in the past)
   - Manual cleanup: the CLI command (keep existing docs for the manual command)
   Do not remove any existing documentation — only add/correct the automatic cleanup description.

7. **L-7: Remove stale python-barcode from requirements.lock** (`backend/requirements.lock`)
   First, grep for `import barcode` and `from barcode` in all backend source files to confirm
   no source imports the python-barcode top-level module.
   Then remove the `python-barcode==0.16.1` line from `requirements.lock`.
   Note: do not regenerate the lock file from scratch (no network access). Manual line removal is correct.

After all fixes:
- Run: `cd backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Fix any failures before completing
- Write your entry in `handoff/wave-07/phase-03-wave-07-backend-process-and-docs/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
