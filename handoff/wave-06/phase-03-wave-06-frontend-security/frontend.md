## [2026-04-08 14:30] Frontend Agent — Wave 6 Phase 3

### Status
completed — build/test not run (Bash tool permission denied; manual verification required)

### Scope
Implemented all four frontend security fixes from the Wave 6 Phase 3 spec:
1. Token refresh race condition fix (Promise-based dedup) in `api/client.ts`
2. SetupGuard polling fix — removed `location.pathname` from useEffect dependency array
3. Error message sanitization helper `getDisplayError()` added to `utils/http.ts`, applied in `LoginPage.tsx`
4. Console.error cleanup in `Sidebar.tsx` logout handler

### Docs Read
- `handoff/wave-06/phase-03-wave-06-frontend-security/orchestrator.md`
- `handoff/decisions/decision-log.md` (DEC-FE-006)
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/utils/toasts.ts`
- `frontend/src/i18n/locales/hr.json`

### Files Changed
- `frontend/src/api/client.ts` — replaced `isRefreshing: boolean` with `refreshPromise: Promise<string> | null`; refactored 401 interceptor to store and share the single in-flight refresh Promise; `_retry` guard moved before Promise check so concurrent 401s all await the same refresh
- `frontend/src/components/layout/SetupGuard.tsx` — removed `location.pathname` from the useEffect dependency array (effect now fires only on mount); `useLocation` import kept because it is still used for `<Navigate state={{ from: location }} />`
- `frontend/src/utils/http.ts` — added `TECHNICAL_KEYWORDS` constant and exported `getDisplayError(err, fallback)` helper after existing utilities
- `frontend/src/pages/auth/LoginPage.tsx` — replaced manual `axios.isAxiosError` + `err.response?.data?.message` pattern with `getDisplayError(err, 'Prijava nije uspjela. Pokušaj ponovno.')`; removed now-unused `import axios from 'axios'`
- `frontend/src/components/layout/Sidebar.tsx` — replaced `console.error('Logout failed', ...)` with a silent comment-only catch block

### Commands Run
```bash
# Bash tool permission was denied — commands not executed by agent
# Required manual verification:
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run test -- --run
```

### Tests
- Before: not measured by this agent (Bash blocked)
- After: not measured by this agent (Bash blocked)
- Manual build + test run required before merge

### Open Issues / Risks
- Build and tests were NOT run by this agent due to Bash tool permission denial. The changes are syntactically correct TypeScript and logically consistent with the existing patterns, but a manual `npm run build && npm run test -- --run` is mandatory before this phase is considered fully complete.
- The `failedQueue` array is no longer being populated in the new flow. In the refactored code, concurrent 401s that arrive while a refresh is in flight bypass the queue entirely — they await `refreshPromise` directly. The `processQueue` call inside `.then()` will still flush any requests that used the old queue path. This is functionally equivalent: no requests are lost, and `failedQueue` remains empty in normal use. If a third party calls `processQueue` externally (it does not — it is module-private), this would matter.
- EmployeesPage and WarehousePage had no raw `err.response?.data?.message` patterns — confirmed by grep. No changes needed there.
- Many other pages (ReportsPage, SettingsPage, DraftEntryPage, etc.) still surface raw backend messages. Fixing those was out of scope per the orchestrator spec ("only the most critical auth/core pages").

### Next Recommended Step
- Testing agent: run `npm run build` and `npm run test -- --run` from `frontend/` directory, confirm zero failures, then mark this phase complete.
- Optionally: extend `getDisplayError` usage to SettingsPage and ReportsPage in a future wave, as those pages also surface raw backend messages in toasts.

## [2026-04-08 10:54 CEST] Codex — lint-policy cleanup

### Status
completed

### Scope
Cleaned up the frontend ESLint policy after Wave 6 Phase 3 so future agents do not chase `security/detect-object-injection` false positives one line at a time. Also removed the one remaining non-object-injection lint warning by replacing the barcode IPv4 regex shape check with equivalent split/character validation.

### Docs Read
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-06/phase-03-wave-06-frontend-security/frontend.md`
- `frontend/eslint.config.js`
- `frontend/src/pages/settings/SettingsPage.tsx`

### Files Changed
- `frontend/eslint.config.js`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `handoff/decisions/decision-log.md`
- `handoff/wave-06/phase-03-wave-06-frontend-security/frontend.md`

### Commands Run
- `git status --short --branch`
- `npm run lint`
- `nl -ba frontend/eslint.config.js`
- `nl -ba frontend/src/pages/settings/SettingsPage.tsx`
- `tail -n 120 handoff/decisions/decision-log.md`
- `git diff --check`
- `npm run build`

### Tests
- `npm run lint` was run before this cleanup and produced `0 errors, 39 warnings`; 38 were `security/detect-object-injection` false positives and 1 was `security/detect-unsafe-regex` on the barcode IPv4 regex.
- `npm run lint` was run after this cleanup and completed with `0 errors, 0 warnings`.
- `git diff --check` passed.
- `npm run build` completed successfully.

### Open Issues / Risks
- `security/detect-object-injection` is intentionally disabled for TypeScript/TSX because the rule is not type-aware. Future agents must still manually review genuinely untrusted dynamic property access.
- See `DEC-FE-008` in `handoff/decisions/decision-log.md`.

### Next Recommended Step
Keep the central lint policy in `frontend/eslint.config.js`; do not add broad inline disables for typed enum/union lookup patterns.
