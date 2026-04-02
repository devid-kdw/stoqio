## Phase Summary

Phase
- Wave 2 - Phase 6 - Obsolete Location Seed Retirement

Objective
- Remove or explicitly retire the obsolete location-seeding path so new installs cannot be misled into bypassing the current first-run setup flow.
- Make repo markdown artifacts consistent with the accepted single-location `/setup` model.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-024`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-003`)
- `handoff/implementation/phase-04-first-run-setup/orchestrator.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `backend/seed_location.py`
- `backend/seed.py`

Current Repo Reality
- `backend/seed_location.py` has been removed.
- The current baseline in `stoqio_docs/08_SETUP_AND_GLOBALS.md` is explicit:
- no location is seeded
- the first `Location` must be created through the authenticated first-run `/setup` flow
- `DEC-BE-003` reserves `Location.id = 1` for that single supported v1 location
- Older Phase 3 handoff/testing artifacts now carry supersession notes so they no longer read like live instructions to run `seed_location.py`, including:
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` now records `F-024` in the past tense, so the repo-state update is preserved without leaving the doc factually stale.

Contract Locks / Clarifications
- The supported install path is now singular:
- run migrations
- run `backend/seed.py` for admin/reference data
- create the first and only supported `Location` through `/setup`
- New installs must not be directed toward `seed_location.py` anywhere in the repo.
- Preferred implementation is to remove `backend/seed_location.py` entirely.
- If an implementation constraint truly requires keeping a file at that path temporarily, it must be converted into an explicit obsolete stub that fails loudly and tells the operator to use the Phase 4 first-run setup flow instead.
- Historical handoff artifacts may keep factual records of what happened in March 2026, but they must no longer read as current instructions for bootstrapping a fresh installation.
- For old handoff/testing markdown, prefer a clear supersession/correction note over silently rewriting history when the file is primarily a historical transcript.
- `backend/seed.py` remains valid for admin/reference data only. This phase must not accidentally expand it to create a `Location`.
- Do not broaden this phase into new setup features, seed-credential hardening, or a wider docs sweep unrelated to the obsolete location helper.
- Documentation updates are mandatory in this phase. Code cleanup alone is not sufficient.

Delegation Plan
- Backend:
- retire `backend/seed_location.py` safely
- scrub or supersede repo markdown references that still instruct people to run it
- keep the first-run `/setup` flow as the only supported location-creation path
- Frontend:
- none
- Testing:
- none as a separate agent; backend verification is sufficient for this cleanup phase

Acceptance Criteria
- `backend/seed_location.py` is removed, or retained only as a loud obsolete stub that cannot silently seed a current install.
- No current repo instruction path for fresh installs tells operators or agents to run `seed_location.py`.
- Repo docs and handoff artifacts align on the same setup model:
- `seed.py` seeds admin/reference data only
- `/setup` is the only supported path for creating the initial location
- Historical artifacts that still mention `seed_location.py` are clearly marked as superseded/obsolete rather than left ambiguous.
- The phase leaves a complete orchestrator and backend handoff trail.

Validation Notes
- Backend agent completed the cleanup.
- `backend/seed_location.py` was deleted.
- The Phase 3 handoff/testing artifacts were updated with supersession notes and current setup-path wording.
- The review doc was updated to describe the helper in the past tense.
- Verification completed:
  - `rg -n "seed_location\\.py|python seed_location|seed location" handoff stoqio_docs docs memory README.md backend -g '!backend/venv/**'`
  - `cd backend && venv/bin/python -m pytest tests/test_setup.py tests/test_auth.py -q` → `55 passed`

Next Action
- Phase 6 cleanup is complete.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 2 Phase 6 of the STOQIO WMS project.

You are not alone in the codebase. Do not revert unrelated work. Your ownership is limited to retiring the obsolete location-seeding helper, updating the affected repo markdown artifacts, optionally adding a narrow decision-log entry if needed for cross-phase clarity, and appending your work log to `handoff/wave-02/phase-06-wave-02-location-seed-retirement/backend.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-024`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-003`)
- `handoff/implementation/phase-04-first-run-setup/orchestrator.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `backend/seed_location.py`
- `backend/seed.py`

Goal
- Remove or explicitly retire the obsolete location-seeding path so the first-run `/setup` flow is the only supported location-creation path for new installs, and make the repo markdown trail consistent with that baseline.

Current Repo Reality
- At the start of this phase, `backend/seed_location.py` still seeded `Location(name='Main Warehouse', is_active=True)` and only checked by name.
- Phase 4 later established a different contract:
- no location is pre-seeded
- first location is created through authenticated `POST /api/v1/setup`
- `Location.id = 1` is reserved for the single supported v1 location
- Several old Phase 3 markdown artifacts initially told the reader to run `seed_location.py`, which conflicted with the accepted setup model.

Non-Negotiable Contract Rules
- Preferred outcome: delete `backend/seed_location.py`.
- If you keep a file at that path temporarily, it must fail loudly and immediately with a clear obsolete/superseded message. It must not create or preserve a current-install `Location` row.
- Do not repurpose `backend/seed_location.py` into a second supported setup path.
- Do not expand `backend/seed.py` to create a location.
- Scrub the repo markdown trail so fresh-install instructions no longer point to `seed_location.py`.
- Keep historical trace honest:
- if an old handoff/testing file is primarily a historical record, preserve the fact that the helper was once used
- but add a clear supersession/correction note so it no longer reads like a current instruction
- Update markdown files that would otherwise remain factually stale after the helper is retired, including the review doc if its wording still asserts the helper currently exists.
- Keep the scope narrow:
- no new setup endpoints
- no auth/credential redesign
- no unrelated docs cleanup

Tasks
1. Retire the obsolete helper by deleting `backend/seed_location.py`, or by converting it into an explicit obsolete stub that aborts with a clear message.
2. Audit and update all remaining repo markdown references that currently instruct readers to run that helper, at minimum:
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md`
3. Make the supported setup path explicit wherever needed:
- migrations
- `backend/seed.py` for admin/reference data
- authenticated first-run `/setup` for the initial location
4. Preserve historical accuracy in handoff artifacts while removing any ambiguity that `seed_location.py` is still supported.
5. If you discover a cross-phase clarification that should become part of the durable baseline, add it to `handoff/decisions/decision-log.md`.
6. Append your work log to `handoff/wave-02/phase-06-wave-02-location-seed-retirement/backend.md` using the section shape required by `handoff/README.md`.

Suggested Implementation Direction
- Prefer deletion if nothing in the runtime or tooling still depends on the file.
- For old handoff/testing files, a short appended supersession note is usually better than rewriting historical command transcripts.
- For live reference docs such as verification command guides, replace the obsolete bootstrap instructions directly so they are safe for current readers.

Verification
- Run the smallest relevant verification needed for this cleanup, but cover both repo-state and setup-baseline confidence.
- At minimum run:
- `rg -n "seed_location\\.py|python seed_location|seed location" handoff stoqio_docs docs memory README.md backend -g '!backend/venv/**'`
- `cd backend && venv/bin/python -m pytest tests/test_setup.py tests/test_auth.py -q`
- If your implementation remains docs-only apart from deleting or stubbing `seed_location.py`, record clearly why broader backend verification was unnecessary.

Done Criteria
- New installs are no longer pointed at `seed_location.py`.
- The first-run `/setup` flow is the only supported location-creation path in repo code/docs.
- Historical markdown no longer leaves the obsolete helper looking current.
- Verification is recorded in handoff.

## [2026-04-02 17:46 CET] Orchestrator Validation - Wave 2 Phase 6 Obsolete Location Seed Retirement

Status
- accepted

Scope
- Reviewed the backend delivery for the obsolete location-seeding retirement phase.
- Re-ran the key repo-state and setup/auth verification locally.
- Corrected one documentation-only closeout issue in the decision log so the new baseline entry uses a unique ID (`DEC-BE-017`) instead of colliding with an older Phase 15 backend decision.

Docs Read
- `handoff/wave-02/phase-06-wave-02-location-seed-retirement/backend.md`
- `handoff/wave-02/phase-06-wave-02-location-seed-retirement/orchestrator.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`

Files Reviewed
- `backend/seed_location.py`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-03-authentication/backend.md`
- `handoff/implementation/phase-03-authentication/orchestrator.md`
- `handoff/implementation/phase-03-authentication/testing.md`
- `handoff/implementation/phase-03-authentication/verification_commands.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md`
- `handoff/wave-02/phase-06-wave-02-location-seed-retirement/backend.md`

Commands Run
```bash
git status --short
git diff --stat
rg -n "seed_location\\.py|python seed_location|seed location" handoff stoqio_docs docs memory README.md backend -g '!backend/venv/**'
test -e backend/seed_location.py && echo EXISTS || echo MISSING
cd backend && venv/bin/python -m pytest tests/test_setup.py tests/test_auth.py -q
```

Validation Result
- `backend/seed_location.py` is deleted (`MISSING`).
- The repo-wide grep now returns only historical/supersession mentions, review-history references, and current phase handoff material. No active fresh-install instruction path still points to `seed_location.py`.
- `cd backend && venv/bin/python -m pytest tests/test_setup.py tests/test_auth.py -q` -> `55 passed`
- The old Phase 3 artifacts now preserve history without presenting the retired helper as a supported current-install step.
- The review document no longer claims the helper currently exists as active repo reality; it now records the finding in past tense with the retirement noted.

Findings
- One documentation-only issue was found during review:
- the new decision-log entry initially reused `DEC-BE-010`, which already belonged to an older Phase 15 backend decision
- orchestrator corrected the new cleanup entry to `DEC-BE-017`
- No remaining blocking implementation or documentation findings were identified after that fix.

Closeout Decision
- Wave 2 Phase 6 is formally accepted.

Next Action
- Treat the current repo state and this handoff trail as the accepted baseline for the next Wave 2 phase.
