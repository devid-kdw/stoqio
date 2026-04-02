## 2026-03-14 19:16:18 CET

Status
- Blocked

Scope
- Reviewed the Phase 14 Settings spec, global UI rules, RBAC rules, Phase 14 backend handoff, and the current frontend shell/page patterns.
- Mapped the real frontend implementation touchpoints for this phase: `frontend/src/api/settings.ts`, `frontend/src/routes.tsx`, `frontend/src/pages/settings/SettingsPage.tsx`, and shared Settings-backed branding / role-label usage in the shell.
- Did not modify frontend source files because the task-level write constraint explicitly limited writes to `handoff/implementation/phase-14-settings/frontend.md` only.

Docs Read
- `stoqio_docs/18_UI_SETTINGS.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/implementation/phase-14-settings/backend.md`
- `frontend/src/utils/setup.ts`
- `frontend/src/utils/toasts.ts`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/api/employees.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/reports.ts`
- `frontend/src/api/setup.ts`
- `frontend/src/utils/roles.ts`
- `frontend/src/store/authStore.ts`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/employees/EmployeesPage.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `backend/tests/test_settings.py`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/articles/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/services/employee_service.py`
- `backend/app/services/order_service.py`

Files Changed
- `handoff/implementation/phase-14-settings/frontend.md`

Commands Run
- `rg --files handoff | sort`
- `rg --files handoff stoqio_docs frontend/src | rg '(^handoff/README\\.md$|^handoff/decisions/decision-log\\.md$|^handoff/implementation/phase-13-reports/orchestrator\\.md$|^stoqio_docs/18_UI_SETTINGS\\.md$|^stoqio_docs/08_SETUP_AND_GLOBALS\\.md$|^stoqio_docs/03_RBAC\\.md$|^frontend/src/utils/setup\\.ts$|^frontend/src/utils/toasts\\.ts$|^frontend/src/components/shared/FullPageState\\.tsx$|^frontend/src/routes\\.tsx$|/settings/|api/.+|pages/.+|layout|shell|sidebar|auth|role)'`
- `sed -n '1,220p' stoqio_docs/18_UI_SETTINGS.md`
- `sed -n '1,260p' stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `sed -n '1,220p' stoqio_docs/03_RBAC.md`
- `sed -n '1,220p' handoff/README.md`
- `sed -n '1,260p' handoff/decisions/decision-log.md`
- `sed -n '1,220p' handoff/implementation/phase-13-reports/orchestrator.md`
- `sed -n '1,260p' handoff/implementation/phase-14-settings/backend.md`
- `sed -n '1,260p' frontend/src/routes.tsx`
- `sed -n '1,260p' frontend/src/utils/setup.ts`
- `sed -n '1,260p' frontend/src/utils/toasts.ts`
- `sed -n '1,260p' frontend/src/components/shared/FullPageState.tsx`
- `sed -n '1,260p' frontend/src/api/client.ts`
- `sed -n '1,260p' frontend/src/utils/http.ts`
- `sed -n '1,260p' frontend/src/api/articles.ts`
- `sed -n '1,260p' frontend/src/api/employees.ts`
- `sed -n '1,240p' frontend/src/api/reports.ts`
- `sed -n '1,260p' frontend/src/api/setup.ts`
- `sed -n '1,260p' frontend/src/utils/roles.ts`
- `sed -n '1,260p' frontend/src/store/authStore.ts`
- `sed -n '1,260p' frontend/src/components/layout/Sidebar.tsx`
- `sed -n '1,260p' frontend/src/components/layout/AppShell.tsx`
- `sed -n '1,220p' frontend/src/components/layout/ProtectedRoute.tsx`
- `sed -n '1,240p' frontend/src/components/layout/SetupGuard.tsx`
- `sed -n '1,320p' frontend/src/pages/reports/ReportsPage.tsx`
- `sed -n '1,260p' frontend/src/pages/employees/EmployeesPage.tsx`
- `sed -n '1,220p' frontend/src/pages/auth/LoginPage.tsx`
- `sed -n '450,930p' backend/tests/test_settings.py`
- `sed -n '590,980p' backend/app/services/settings_service.py`
- `sed -n '1,360p' backend/app/api/settings/routes.py`
- `sed -n '440,560p' backend/app/services/employee_service.py`
- `sed -n '140,220p' backend/app/api/articles/routes.py`
- `sed -n '1,160p' backend/app/api/employees/routes.py`
- `sed -n '1,120p' backend/app/api/orders/routes.py`
- `sed -n '1088,1168p' backend/app/services/order_service.py`
- `rg -n 'i18n|language|default_language|setLanguage|role label|display name|location name|STOQIO|Korisnik:' frontend/src`
- `rg -n 'ROLE_LABELS|role_display_name|user.role|display_name|STOQIO|Location name|Login' frontend/src/components frontend/src/pages frontend/src/utils`
- `rg -n 'lookups/articles|/articles\\?|def .*lookup.*article|@.*articles' backend/app -g'*.py'`
- `date '+%Y-%m-%d %H:%M:%S %Z'`

Tests
- Not run.
- Reason: no frontend source changes were permitted, and the requested verification commands (`cd frontend && npm run lint -- --max-warnings=0`, `cd frontend && npm run build`) were intentionally not run because the task-level write constraint limited output changes to this handoff file only.

Open Issues / Risks
- Blocker: the requested Phase 14 frontend implementation could not be applied because the allowed write scope excluded the actual frontend files that must change.
- Backend contract note from `DEC-SET-001`: quota `scope` wire values are `GLOBAL_ARTICLE_OVERRIDE` and `JOB_TITLE_CATEGORY_DEFAULT`, and user edit uses optional field `password` for admin-driven password reset.
- Frontend assumption logged explicitly: for the Quotas article selector, the only existing search-style lookup that returns broad active article matches is `GET /api/v1/orders/lookups/articles?q=...`. `GET /api/v1/articles?q=...` is exact-match lookup mode, and `GET /api/v1/employees/lookups/articles?q=...` is limited to personal-issue categories. If Phase 14 must allow quota creation against any active article without exact article number input, the frontend should reuse the Orders lookup unless backend adds a dedicated Settings lookup.
- Settings-backed branding / role labels are not centralized today. Hardcoded UI strings currently live in `frontend/src/components/layout/Sidebar.tsx` (`STOQIO`, current-user role label) and `frontend/src/pages/auth/LoginPage.tsx` (`STOQIO Login`). Implementing the Phase 14 requirement cleanly will likely need a shared client-side settings state so General and Roles saves update the shell immediately.
- Full implementation still needs Croatian client-rendered copy on the new Settings page, per-section loading/saving state, one-retry-then-full-page-error behavior via existing `runWithRetry` + `FullPageState`, and append-free source edits outside this handoff file.

Next Recommended Step
- Lift the write restriction for frontend source files and implement the phase in one pass: add `frontend/src/api/settings.ts`, replace the `/settings` placeholder in `frontend/src/routes.tsx`, create `frontend/src/pages/settings/SettingsPage.tsx`, and update the shell role / branding consumers (`frontend/src/components/layout/Sidebar.tsx`, plus shared settings state and any login/header branding touchpoints needed for immediate General / Roles updates). After code changes, run `cd frontend && npm run lint -- --max-warnings=0` and `cd frontend && npm run build`.

## 2026-03-14 19:46:16 CET

Status
- Completed

Scope
- Implemented the real Phase 14 frontend Settings module with typed API wiring, a lazy-loaded `/settings` route, and a full ADMIN-only Settings page with all 9 required sections.
- Added a narrow shell settings store so General and Roles changes update the current ADMIN sidebar branding and role label immediately in the same session.
- Kept the work frontend-only and did not change backend runtime code.

Docs Read
- `stoqio_docs/18_UI_SETTINGS.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-14-settings/backend.md`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/utils/toasts.ts`
- `frontend/src/utils/setup.ts`
- `frontend/src/utils/http.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/store/authStore.ts`

Files Changed
- `frontend/src/api/settings.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/routes.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `handoff/implementation/phase-14-settings/frontend.md`

Commands Run
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Tests
- Passed:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Failed:
- None
- Not run:
- Browser smoke validation

Open Issues / Risks
- Assumption used: because there is no non-ADMIN settings read endpoint and RBAC must not be widened, backend-backed shell branding / role labels are hydrated for the current ADMIN session via the new settings store. Non-ADMIN sessions fall back to defaults unless the store was already hydrated earlier in the same browser session.
- Login page branding remains static by design. There is no anonymous settings endpoint, and this follow-up did not invent one.
- Quota article search intentionally reuses `GET /api/v1/orders/lookups/articles?q=...` exactly as instructed. It therefore follows the Orders lookup behavior for active articles.

Next Recommended Step
- Run an in-browser ADMIN smoke test across all 9 sections, especially quota create/edit/delete, supplier search pagination with inactive toggle, and self-deactivate handling in Users.
