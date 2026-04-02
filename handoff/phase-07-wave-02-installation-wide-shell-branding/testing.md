## Testing Log - Wave 2 Phase 7 (Installation-Wide Shell Branding)

**Status**: Done
**Scope**: Add tests asserting non-admins can retrieve correct branding without exposing mutable settings and asserting frontend properly switches from store defaults to payload elements.
**Docs Read**: 
- `handoff/README.md`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `backend/tests/test_settings.py`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
**Files Changed**:
- `backend/tests/test_settings.py`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx` (New)
**Commands Run**:
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` (pass)
- `cd frontend && CI=true npm run test` (pass)
- `cd frontend && npm run lint -- --max-warnings=0` (pass)
- `cd frontend && npm run build` (pass)
**Tests**:
- Verified backend permissions check matrix using parameterized tests for all mutable settings endpoints (e.g., `PUT`, `POST`, `DELETE`, `PATCH` operations routing) specifically asserting a `403 FORBIDDEN` for `MANAGER`/`VIEWER` roles.
- Created `AppShell.test.tsx` verifying non-admin access uses properly mapped mock role labels against payload content.
- Asserted fallback defaults persist safely without blocking when backend responses throw errors.
**Open Issues / Risks**:
- **Production-code mismatch discovered**: In `app/services/settings_service.py`, the `get_shell_settings` route returns `role_display_names` as a list of objects (e.g. `[{"role": "ADMIN", "display_name": "Admin"}]`). However, `frontend/src/api/settings.ts` defines it strictly as `Record<SystemRole, string>` and `settingsStore.ts` explicitly expects this hashmap for its hydration loop (`toRoleDisplayNameFromRecord`). This will break the hydration iteration step on the active branch in production since the frontend will try to destructure an array instead of an object map. This has been mocked according to frontend expectations in the newly added tests and left unpatched per instructions restricting scope only to testing verification routines.
**Next Recommended Step**: Have the backend/frontend align `role_display_names` schema interface (either dict mapping or processing array transformation natively via `api`) before completing next phase handoff. Or wrap up this phase if acceptable to keep it in the back-log.

## 2026-04-02 18:18:00 CET - Orchestrator Direct Fix Follow-up

### Status

Resolved.

### Scope

Document the direct orchestrator fix that aligned the frontend shell payload handling with the backend's real `role_display_names` array shape and updated the frontend test mock accordingly.

### Docs Read

- `handoff/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `backend/app/services/settings_service.py`

### Files Changed

- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/frontend.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/testing.md`
- `handoff/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`

### Commands Run

- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q`
- `cd frontend && CI=true npm run test`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

### Tests

- Passed: backend settings suite -> `44 passed`
- Passed: frontend Vitest suite -> `5 files passed, 19 tests passed`
- Passed: frontend lint
- Passed: frontend build

### Open Issues / Risks

- None for the previously reported shell payload mismatch. The frontend test mock now matches the real backend array payload, and the store hydration path handles that payload correctly.

### Next Recommended Step

- Orchestrator can treat the earlier mismatch finding in this file as closed by the direct fix above.
