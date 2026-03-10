## 2026-03-10 20:43:37 CET

### Status
Completed.

### Scope
Implemented the Phase 4 frontend first-run setup flow only:
- added `/setup` page for ADMIN with location name and timezone form
- added setup API client support for status check and initial location creation
- updated login redirect flow to branch on setup status
- added a global setup guard that blocks regular routes until setup is finished
- redirected completed installations away from `/setup`

### Docs Read
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2 and § 4
- `stoqio_docs/05_DATA_MODEL.md` § 23
- `stoqio_docs/07_ARCHITECTURE.md` § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-04-first-run-setup/backend.md`

### Files Changed
- `frontend/src/store/authStore.ts`
- `frontend/src/api/setup.ts`
- `frontend/src/utils/setup.ts`
- `frontend/src/utils/toasts.ts`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/main.tsx`
- `handoff/decisions/decision-log.md`
- `handoff/phase-04-first-run-setup/frontend.md`

### Commands Run
- `sed -n '1,220p' stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `sed -n '1,260p' stoqio_docs/05_DATA_MODEL.md`
- `sed -n '1,220p' stoqio_docs/07_ARCHITECTURE.md`
- `sed -n '1,240p' stoqio_docs/03_RBAC.md`
- `sed -n '1,240p' handoff/README.md`
- `sed -n '1,260p' handoff/decisions/decision-log.md`
- `sed -n '1,260p' frontend/src/store/authStore.ts`
- `sed -n '1,260p' frontend/src/api/auth.ts`
- `sed -n '1,260p' frontend/src/routes.tsx`
- `sed -n '1,260p' frontend/src/pages/auth/LoginPage.tsx`
- `sed -n '1,260p' frontend/src/components/layout/ProtectedRoute.tsx`
- `sed -n '1,260p' frontend/src/components/layout/AppShell.tsx`
- `sed -n '1,260p' frontend/src/api/client.ts`
- `sed -n '1,220p' frontend/src/utils/roles.ts`
- `sed -n '1,260p' backend/app/api/setup/routes.py`
- `sed -n '1,260p' backend/tests/test_setup.py`
- `npm run build`
- `npm run lint`
- `git status --short`
- `git diff -- frontend/src/store/authStore.ts frontend/src/api/setup.ts frontend/src/utils/setup.ts frontend/src/utils/toasts.ts frontend/src/components/shared/FullPageState.tsx frontend/src/components/layout/SetupGuard.tsx frontend/src/pages/auth/SetupPage.tsx frontend/src/pages/auth/LoginPage.tsx frontend/src/routes.tsx frontend/src/main.tsx`

### Tests
- Passed: `npm run build`
- Passed: `npm run lint`
- Manual verification by code path:
  - ADMIN login checks `GET /api/v1/setup/status` and routes to `/setup` when `setup_required` is true
  - `/setup` posts to `POST /api/v1/setup` through the authenticated API client and redirects to `/approvals` on success
  - all authenticated app routes now pass through `SetupGuard`, which redirects to `/setup` until setup is complete
  - completed installations opening `/setup` are redirected back to the ADMIN home route

### Open Issues / Risks
- Spec gap logged as `DEC-FE-003`: docs do not define the expected UX for non-ADMIN logins before setup is complete, so the implementation logs them out and returns them to `/login` to preserve ADMIN-only access to `/setup`.
- The timezone dropdown uses `Intl.supportedValuesOf('timeZone')` when available and falls back to a short static list otherwise. If the target browser lacks `supportedValuesOf`, the available choices are reduced but still include `Europe/Berlin`.
- Network/server failures during setup-status page loads now show a full-page retry state, but the wider app still does not have a centralized global retry/error-screen layer outside this setup flow.

### Next Recommended Step
Testing agent should verify the end-to-end setup flow against the new backend endpoints, including ADMIN first login, non-ADMIN behavior while setup is pending, and `/setup` access after initialization is complete.
