## Phase Summary

Phase
- Wave 6 - Phase 3 - Frontend Security

Objective
- Remediate four High/Medium/Low frontend security findings from the 2026-04-08 review:
  V-8 (token refresh race condition — multiple concurrent 401s start multiple refreshes),
  S-7 (SetupGuard polls fetchSetupStatus on every route navigation change),
  S-9 (API error messages from backend surfaced raw to users — info disclosure),
  N-6 (console.error in production code leaks error details to browser console).

Source Docs
- `handoff/README.md`
- `handoff/wave-06/README.md`
- `handoff/decisions/decision-log.md` (DEC-FE-006 for auth storage baseline)
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/utils/http.ts` (getApiErrorBody or similar)
- `frontend/src/utils/toasts.ts`

Current Repo Reality
- `api/client.ts`: `isRefreshing` flag and `failedQueue` are module-level mutable state.
  The check `if (!isRefreshing)` and `isRefreshing = true` are not atomic in JS's event
  loop sense — multiple 401 responses arriving before the first refresh resolves can all
  pass the check, triggering multiple parallel refresh calls.
- `components/layout/SetupGuard.tsx`: `location.pathname` is in the useEffect dependency
  array, causing `fetchSetupStatus()` to be called on every route navigation. Setup status
  should only be fetched once on mount, not on every navigation.
- Multiple page components surface `err.response?.data?.message` or
  `getApiErrorBody(err)?.message` directly in toast notifications. Backend error messages
  can contain internal implementation details, schema names, or constraint names.
- `Sidebar.tsx:25` has `console.error('Logout failed', ...)` — logs to browser console
  in production. Multiple other pages may have similar patterns.

Contract Locks / Clarifications
- Do NOT change the refresh token localStorage storage model (DEC-FE-006).
- Do NOT change the access token memory-only model.
- Do NOT change the bootstrap hydration flow in `main.tsx`.
- The refresh dedup fix: the standard pattern is to store the refresh Promise itself
  (not just a boolean flag) so that all queued 401 requests await the same Promise.
  Use `let refreshPromise: Promise<string> | null = null` instead of `isRefreshing`.
  Keep the `failedQueue` pattern for retrying queued requests.
- SetupGuard fix: remove `location.pathname` from the dependency array. The effect should
  run only on mount (empty dependency array `[]`). Verify the guard still correctly
  redirects on initial load.
- Error message sanitization: create a helper `getDisplayError(err, fallback: string)`
  in `utils/http.ts` that returns `fallback` by default and only returns the backend
  message if it does NOT contain technical keywords (e.g., "constraint", "column",
  "database", "traceback", "Exception", "Error:"). Otherwise always return fallback.
  Replace direct `getApiErrorBody(err)?.message` usages in LoginPage and the most
  critical pages with this helper.
- console.error removal: in production-deployed code, `console.error` is acceptable for
  genuine unexpected errors. Remove or downgrade (to console.warn/no-op) only instances
  that log sensitive data like token values, user credentials, or full error objects.
  Do not remove all console.error — only the ones flagged in Sidebar.tsx logout handler.
- Do NOT change any visual design, routing logic, or page layouts.
- Do NOT add any new npm packages.

Delegation Plan
- Frontend:
  - Fix token refresh race in `api/client.ts` (Promise-based dedup)
  - Fix SetupGuard dependency array
  - Add `getDisplayError()` helper to `utils/http.ts`
  - Replace raw backend message surfacing in `LoginPage.tsx` and other critical paths
  - Clean up the Sidebar.tsx console.error logout handler
  - Run `npm run build` and `npm run test` to verify no regressions
  - Document in `frontend.md`

Acceptance Criteria
- Multiple concurrent 401 responses result in exactly ONE refresh call — subsequent
  requests are queued and retried after the single refresh resolves
- SetupGuard makes exactly one `fetchSetupStatus()` call on initial mount, not on
  each route navigation
- Login error messages shown to the user are generic (e.g., "Prijava nije uspjela.")
  and do not expose internal backend error details
- `npm run build` passes without errors
- `npm run test` (or `npm run test -- --run`) passes all existing tests
- Handoff files follow the required section shape

Validation Notes
- 2026-04-08: Orchestrator created Wave 6 Phase 3 handoff. Runs in parallel with Phases 1 and 2.
- 2026-04-08 10:35 CEST: Frontend agent completed all 4 fixes. Build and test run by orchestrator: npm run build ✓, 11 test files / 41 tests passed. Phase 3 closed.

Next Action
- Frontend agent implements all fixes. Can run in parallel with backend phases.


---

## Delegation Prompt — Frontend Agent

You are the frontend security remediation agent for Wave 6 Phase 3 of the STOQIO WMS project.
This phase runs in parallel with the backend phases.

Read before coding:
- `handoff/README.md`
- `handoff/wave-06/phase-03-wave-06-frontend-security/orchestrator.md`
- `handoff/decisions/decision-log.md` (especially DEC-FE-006)
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/utils/toasts.ts`

Your fixes (implement all of them):

1. **Token refresh race condition** (`frontend/src/api/client.ts`)
   Replace the boolean `isRefreshing` flag with a Promise-based dedup. The fix:
   - Replace `let isRefreshing = false` with `let refreshPromise: Promise<string> | null = null`
   - In the 401 response interceptor, if `refreshPromise` is null, create it:
     ```typescript
     refreshPromise = authApi.refresh()
       .then(data => {
         // store new tokens
         return data.access_token
       })
       .finally(() => { refreshPromise = null })
     ```
   - If `refreshPromise` already exists, await the same promise — do not create a new one
   - All queued requests await `refreshPromise` then retry with the new token
   - Keep the `failedQueue` / `processQueue` pattern for managing waiting requests
   - Keep `originalRequest._retry` guard to prevent infinite loops
   Read the existing implementation very carefully before changing it to preserve the
   queue-flush behavior.

2. **SetupGuard polling** (`frontend/src/components/layout/SetupGuard.tsx`)
   Find the `useEffect` that calls `fetchSetupStatus()`. Remove `location.pathname`
   (or any equivalent) from the dependency array. The effect should run with `[]` so it
   fires only once on mount. Verify the guard still redirects to /setup when required
   and to the home route when setup is complete.

3. **Error message sanitization** (`frontend/src/utils/http.ts`)
   Add a new exported function `getDisplayError(err: unknown, fallback: string): string`
   that:
   - Extracts the backend message from the error (use the existing pattern)
   - Returns the fallback string if the message contains any of these substrings
     (case-insensitive): "constraint", "column", "database", "traceback", "Exception:",
     "Error:", "sqlalchemy", "psycopg", "integrity"
   - Returns the backend message otherwise
   - If no backend message, returns fallback
   Then in `LoginPage.tsx`, replace the raw `err.response?.data?.message` or equivalent
   with `getDisplayError(err, t('auth.loginError') ?? 'Prijava nije uspjela.')`.
   Also replace in any other page that directly surfaces raw backend messages in toasts.

4. **Console.error cleanup** (`frontend/src/components/layout/Sidebar.tsx`)
   In the logout error handler, change:
   ```typescript
   console.error('Logout failed', e instanceof Error ? e.message : 'unknown error')
   ```
   to either remove it entirely or replace with a silent no-op. The user already sees the
   logout failure via the UI. Sensitive error details should not appear in browser console
   in production builds.

After all fixes:
- Run: `cd frontend && npm run build`
- Run: `cd frontend && npm run test -- --run` (or equivalent Vitest command)
- Fix any failures before completing
- Write your entry in `handoff/wave-06/phase-03-wave-06-frontend-security/frontend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
