## Phase Summary

Phase
- Wave 2 - Phase 7 - Installation-Wide Shell Branding

Objective
- Make shell branding/settings behave as installation-wide display state for all authenticated roles, not only `ADMIN`.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-037`)
- `stoqio_docs/18_UI_SETTINGS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-14-settings/orchestrator.md`

Delegation Plan
- Backend:
- add a minimal read-only authenticated shell-settings payload and keep mutable Settings endpoints `ADMIN`-only
- Frontend:
- load shell branding for all authenticated roles while preserving safe defaults on failure
- Testing:
- prove non-admin roles receive and render installation-wide shell branding and confirm mutable Settings permissions remain unchanged

Acceptance Criteria
- `ADMIN` sees configured location name and configured role display labels.
- Non-admin authenticated roles see the same installation-wide shell branding instead of default fallback labels only.
- Mutable Settings permissions remain `ADMIN`-only.
- Automated verification passes and matches the real backend/frontend contract.

Validation Notes
- Backend, frontend, and testing handoffs were reviewed.
- Automated verification re-run completed successfully on the current worktree:
  - `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` -> `44 passed`
  - `cd frontend && CI=true npm run test` -> `5 files passed, 19 tests passed`
  - `cd frontend && npm run lint -- --max-warnings=0` -> passed
  - `cd frontend && npm run build` -> passed

## [2026-04-02 18:18 CET] Orchestrator Review - Phase Not Accepted Yet

Status
- changes requested

Scope
- Reviewed the delivered backend, frontend, and testing work for installation-wide shell branding.
- Re-ran the requested automated verification.
- Cross-checked the live backend payload shape against the frontend store hydration logic and the new frontend tests.

Docs Read
- `handoff/phase-07-wave-02-installation-wide-shell-branding/backend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/testing.md`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`

Files Reviewed
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/backend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/testing.md`

Commands Run
```bash
git status --short
git diff --stat
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Findings
- Blocking:
- Backend and frontend do not agree on the `role_display_names` schema for `GET /api/v1/settings/shell`.
- Backend currently returns an array of `{role, display_name}` rows in `backend/app/services/settings_service.py`.
- Frontend currently types and hydrates `role_display_names` as `Record<SystemRole, string>` in `frontend/src/api/settings.ts` and `frontend/src/store/settingsStore.ts`.
- This is a real runtime contract bug, not a documentation-only mismatch:
- non-admin users will get the configured `location_name`
- but role display labels will silently fall back to defaults because the array payload does not populate role-keyed entries in the store map
- The new frontend test currently mocks the record-shaped payload expected by the frontend instead of the array payload actually produced by the backend, so the automated suite is green while the live contract is still broken.

Evidence
- Backend payload shape:
- `backend/app/services/settings_service.py:599-604`
- Frontend expected payload shape:
- `frontend/src/api/settings.ts:147-151`
- Frontend hydration path:
- `frontend/src/store/settingsStore.ts:21-26`
- `frontend/src/store/settingsStore.ts:76-79`
- Frontend test mocking the incompatible record shape:
- `frontend/src/components/layout/__tests__/AppShell.test.tsx:27-36`
- Backend tests explicitly lock the array shape:
- `backend/tests/test_settings.py:933`

Impact
- The phase goal is not yet satisfied for configured non-admin role labels.
- Verification requirement
- "Log in as another role -> the same configured shell branding is visible, not default fallback labels only."
- is not reliably met on the current code because the role label half of that branding contract is still broken in live runtime.

Closeout Decision
- Phase 7 is not accepted yet.

Next Action
- Backend and frontend must align the `role_display_names` contract on one shape.
- After that alignment, testing must update the frontend mock/assertions to match the real delivered payload and rerun verification.

## [2026-04-02 18:22 CET] Orchestrator Direct Fix + Final Validation

Status
- accepted

Scope
- Implemented the fix for the blocking review finding directly in the frontend layer and the affected frontend test.
- Re-ran the full requested verification matrix after the fix.
- Updated the Phase 7 handoff trail so future agents can see that the contract mismatch was found in orchestrator review and closed by an orchestrator direct-fix pass.

Docs Read
- `handoff/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/testing.md`
- `backend/app/services/settings_service.py`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`

Files Changed By Orchestrator
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/testing.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Validation Result
- Fixed contract alignment:
- backend continues to return `role_display_names` as the array shape already locked by `backend/tests/test_settings.py`
- frontend now types and hydrates that same array shape instead of expecting a record
- frontend AppShell test now mocks the real backend array payload instead of a fabricated record shape
- Verification passed after the fix:
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` -> `44 passed`
- `cd frontend && CI=true npm run test` -> `5 files passed, 19 tests passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Closeout Decision
- Wave 2 Phase 7 is formally accepted.

Next Action
- Treat the current repo state and this handoff trail as the accepted baseline for the next Wave 2 phase.
