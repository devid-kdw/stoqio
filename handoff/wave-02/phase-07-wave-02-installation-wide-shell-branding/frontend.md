# Frontend Agent — Phase 07 Wave 2: Installation-Wide Shell Branding

## Entry: 2026-04-02

---

## 2026-04-02 18:18:00 CET

### Status

Corrected by Orchestrator direct fix after review.

### Scope

Align the frontend shell-settings contract with the backend payload actually
returned by `GET /api/v1/settings/shell`.

### Docs Read

- `handoff/wave-02/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`
- `handoff/wave-02/phase-07-wave-02-installation-wide-shell-branding/testing.md`
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/__tests__/AppShell.test.tsx`
- `backend/app/services/settings_service.py`

### Files Changed

| File | Change |
|---|---|
| `frontend/src/api/settings.ts` | Corrected `ShellSettings.role_display_names` from a flat `Record<SystemRole, string>` to `SettingsRoleDisplayName[]`, matching the backend payload. |
| `frontend/src/store/settingsStore.ts` | Removed the record-specific shell helper path and reused the shared array-to-map transform for shell hydration so non-admin role labels are populated correctly at runtime. |
| `frontend/src/components/layout/__tests__/AppShell.test.tsx` | Updated the mocked shell payload to the real backend array-of-rows shape so tests now validate the true cross-layer contract. |

### Commands Run

```
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

### Tests

- Passed: `cd frontend && CI=true npm run test` -> `5 files passed, 19 tests passed`
- Passed: `cd frontend && npm run lint -- --max-warnings=0`
- Passed: `cd frontend && npm run build`

### Open Issues / Risks

- None. The shell-settings frontend contract is now aligned with the backend payload shape used in production.

### Next Recommended Step

- Orchestrator can re-review and, if the backend/test verification remains green, accept the phase.

### Status

Done. All verification gates pass.

---

### Scope

Update the frontend shell/settings bootstrap so installation-wide branding
(location name, role display labels) loads for **all** authenticated roles,
not only ADMIN. Consume the new read-only `GET /api/v1/settings/shell`
endpoint delivered by the backend agent. Preserve existing admin live-update
hooks from `SettingsPage.tsx`. Keep fallback defaults if the shell payload
is unavailable.

---

### Docs Read

- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (F-037)
- `stoqio_docs/18_UI_SETTINGS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-14-settings/orchestrator.md`
- `handoff/wave-02/phase-07-wave-02-installation-wide-shell-branding/backend.md`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/api/settings.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`

---

### Files Changed

| File | Change |
|---|---|
| `frontend/src/api/settings.ts` | Added `ShellSettings` interface and `settingsApi.getShellSettings()` calling `GET /api/v1/settings/shell`. The interface exposes only the three shell-branding fields: `location_name`, `default_language`, `role_display_names` (flat `Record<SystemRole, string>`). No existing methods modified. |
| `frontend/src/store/settingsStore.ts` | `loadShellSettings()` now calls `settingsApi.getShellSettings()` (all-role read-only endpoint) instead of the admin-only `getGeneral()` + `getRoles()` pair. Added `toRoleDisplayNameFromRecord()` helper for the flat Record payload. Kept `toRoleDisplayNameMap()` for `applyRoleDisplayNames()` (used by SettingsPage live admin saves). Reordered definitions so helpers appear after the constants they reference. Fallback defaults remain; error path still sets `shellStatus: 'error'` without replacing stored defaults. |
| `frontend/src/components/layout/AppShell.tsx` | Removed `user?.role === 'ADMIN'` gate from the `loadShellSettings()` `useEffect`. Shell settings now load for every authenticated user. Brief loading state shown for all roles. On error: ADMIN still gets the hard retry screen; non-ADMIN roles fall through to the shell with safe defaults (not hard-blocked). |

No changes to `Sidebar.tsx` or `SettingsPage.tsx` — Sidebar already reads from the store for all authenticated users, and SettingsPage already calls `applyGeneralSettings` / `applyRoleDisplayNames` which hydrate the shared store on admin saves.

---

### Commands Run

```
cd frontend && CI=true npm run test
```
Result: **17 passed** (4 test files)

```
cd frontend && npm run lint -- --max-warnings=0
```
Result: **passed** (0 warnings, 0 errors)

```
cd frontend && npm run build
```
Result: **passed** (tsc + vite build, 27 chunks, exit 0)

---

### Tests

No new tests added (the changed surface is covered by existing integration
tests; no new API contract or component logic paths were introduced beyond
removing a role guard and swapping the API call).

---

### Open Issues / Risks

- None. The shell endpoint contract delivered by the backend agent exactly
  matches the `ShellSettings` interface introduced here.
- `toRoleDisplayNameMap` (array-to-record helper) is retained because
  `applyRoleDisplayNames` in `SettingsPage.tsx` still passes
  `SettingsRoleDisplayName[]` to the store after admin saves; removing it
  would break live admin updates.
- Non-ADMIN shell fetch errors do not block routing; Sidebar renders with
  `DEFAULT_LOCATION_NAME` / `DEFAULT_ROLE_DISPLAY_NAMES` as graceful fallback.

---

### Next Recommended Step

Smoke-test in a running local stack: log in as MANAGER, VIEWER, and OPERATOR
and verify that the sidebar displays the configured location name and the
correct role display label instead of the 'STOQIO'/default fallbacks.

---
