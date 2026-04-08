## Phase Summary

Phase
- Wave 7 - Phase 4 - Frontend Auth State and Domain Fixes

Objective
- Remediate seven frontend findings from the 2026-04-08 dual-agent code review:
  M-5 (refreshed tokens do not update frontend user/role state),
  M-6 (settings self role edit leaves auth state stale),
  N-6 (ProtectedRoute has no loading state — premature redirect risk on bootstrap),
  H-5 (editing a warehouse article overwrites density with 1),
  L-2 (warehouse article create does not refresh the list),
  M-4 (reports pagination/export type contract incomplete and behavior undocumented),
  M-9 (report default dates use UTC ISO string instead of local date parts).

Source Docs
- `handoff/README.md`
- `handoff/wave-07/README.md`
- `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (H-5, M-4, M-5, M-6, M-9, L-2)
- `handoff/Findings/wave-06-second-opinion-review.md` (M-4 correction, M-5, M-6, N-6, H-5, L-2, M-9)
- `handoff/decisions/decision-log.md` (DEC-FE-006 for refresh token storage)
- `frontend/src/store/authStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/main.tsx`
- `backend/app/api/auth/routes.py` (for /auth/me response shape)

Current Repo Reality
- `client.ts` token refresh: on successful refresh, calls `useAuthStore.getState().setAccessToken(newAccessToken)`
  only. Never updates `user` or calls `/auth/me`. The new JWT claims carry updated role info
  but nothing extracts them into the store.
- `main.tsx` calls `authApi.me()` at startup only. After that, `authStore.user` is never
  re-fetched from an authoritative source.
- `SettingsPage.tsx` `handleUserSave()`: after `updateUser()` succeeds, updates local `users`
  array only. No check for `editingUserId === currentUser?.id`. Auth store not updated.
- `ProtectedRoute.tsx`: uses `useAuthStore()` hooks (reactive to store changes). However, during
  bootstrap when `/auth/me` is in flight, `user` may be null while `accessToken` is non-null.
  No explicit "loading" state exists — the component may redirect to login prematurely before
  the `/me` response arrives. There is no `authStatus` field in the store.
- `warehouseUtils.ts:89`: `createArticleFormState()` initializes form density to `1` regardless
  of article.density. `warehouseUtils.ts:578`: `buildArticlePayload()` hard-codes `density: 1`
  in the payload for both create and update operations.
  IMPORTANT: The backend `article_service.py` preserves `existing_article.density` when the
  density field is absent from the PATCH body. Therefore the cleanest fix is to OMIT density
  from the update payload in `buildArticlePayload()` for edit operations, not to try to round-trip
  the value through the form. For create operations, density: 1 as the default is acceptable
  (new articles start at 1).
- `WarehousePage.tsx:283`: after article create, calls `navigate('/warehouse')`. Since the user
  is already on `/warehouse`, no re-mount occurs and the `useEffect` dependencies (query, page,
  filters) do not change, so no refetch fires. The new article does not appear.
- `api/reports.ts:45-50`: `StockOverviewResponse` interface omits `page` and `per_page` fields
  returned by the backend. `buildStockOverviewParams()` never sends pagination params.
  CRITICAL CORRECTION from second-opinion review: the original review said export "bypasses
  pagination and downloads all matching rows." This was WRONG. The backend `export_stock_overview()`
  calls `get_stock_overview()` with default page=1, per_page=100. The export therefore gives
  only the first 100 rows, not all matching rows. This makes M-4 MORE serious: the export
  is silently capped at 100 items without any indication in the UI. The fix must document this
  behavior clearly and update the type contract. A full-export path (no pagination on export)
  is the correct direction but requires backend coordination — for this phase, update the type
  contract and document the behavior in a comment. If a backend-only export endpoint already
  exists or can be called differently, prefer that; otherwise document the limitation.
- `reportsUtils.ts:7`: `new Date().toISOString().slice(0, 10)` yields the UTC date, not the
  browser-local date. Around midnight in non-UTC timezones, this produces the wrong default date.
  `reportsUtils.ts:11`: same issue for month-start calculation.
  IMPORTANT from second-opinion review: decide on UTC vs. local before fixing. The backend uses
  UTC for its date calculations. If the frontend sends local dates and the backend compares UTC,
  this creates a mismatch. Since the backend is consistently UTC, the frontend default dates
  should also use UTC (which they accidentally do now). However, the `new Date().toISOString().slice(0,10)`
  pattern is semantically wrong (it's UTC-by-accident not UTC-by-design). Fix by making the
  UTC intent explicit: use `new Date(Date.now()).toISOString().slice(0, 10)` with a comment,
  OR switch to local dates — but only if you also confirm the backend handles local dates correctly.
  Safest approach: make the UTC intent explicit in reportsUtils.ts with a comment, and do NOT
  change the UTC behavior. This avoids the backend mismatch risk.

Contract Locks / Clarifications
- **M-5 token refresh user state**: In `client.ts`, after a successful token refresh:
  1. Store the new access token (existing behavior)
  2. Call `authApi.me(newAccessToken)` to re-fetch the user object
  3. Update `authStore.user` with the response
  Add an `updateUser(user)` method to `authStore.ts` (or use an existing method that supports
  updating user without changing refreshToken). Do NOT call `setAuth()` since that requires all
  three params and would reset the refresh token unnecessarily.
  If the `/auth/me` call fails, do not block the original request retry — just skip the user update
  and proceed with the token. Log the failure for debugging.
- **M-6 self role edit**: In `SettingsPage.tsx` `handleUserSave()`, after `updateUser()` succeeds:
  check if `editingUserId === currentUser?.id`. If yes, call `authApi.me()` with the current
  access token and update `authStore.user` via the new `updateUser()` method. This ensures
  `ProtectedRoute` re-evaluates role access immediately.
- **N-6 ProtectedRoute loading state**: Add `authStatus: 'idle' | 'loading' | 'authenticated' | 'unauthenticated'`
  to `authStore.ts`. Set it to `'loading'` at the start of the bootstrap `/auth/me` call in
  `main.tsx`, then to `'authenticated'` or `'unauthenticated'` on completion.
  In `ProtectedRoute.tsx`, when `authStatus === 'loading'`, render a loading indicator
  (e.g., a centered `<Loader />` from Mantine, consistent with the existing design) instead of
  redirecting to login. Only redirect when `authStatus === 'unauthenticated'`.
- **H-5 warehouse density**: In `warehouseUtils.ts` `buildArticlePayload()`:
  - For UPDATE operations (when an existing article is being edited), omit the `density` field
    from the payload entirely. The backend preserves existing density when the field is absent.
  - For CREATE operations, keep `density: 1` as the default (new articles start at density 1).
  You will need to distinguish create vs. update in `buildArticlePayload()` — pass a parameter
  or check whether `article` (the existing article) is provided to the function.
  Do NOT change the form display or form state initialization — density is not a user-editable
  field and should stay hidden from the form.
- **L-2 warehouse list refresh**: In `WarehousePage.tsx`, after `articlesApi.create()` succeeds,
  call `loadArticles()` directly instead of (or in addition to) `navigate('/warehouse')`.
  Remove the redundant `navigate('/warehouse')` since the user is already on that route.
- **M-4 reports type contract**: In `frontend/src/api/reports.ts`, update `StockOverviewResponse`
  to include `page: number` and `per_page: number` fields. Add a prominent comment explaining
  the current behavior: the backend paginates stock overview at page=1, per_page=100 by default,
  and the export endpoint also returns only page 1 (100 rows). This is a known limitation — a
  full-export endpoint is the correct long-term fix and should be tracked as a follow-up.
  Do NOT add pagination UI controls — this is type contract + documentation only in this phase.
- **M-9 report dates**: In `reportsUtils.ts`, change the implicit UTC-by-accident behavior to
  explicit UTC-by-design. Keep the same `toISOString().slice(0, 10)` output but add a comment:
  ```typescript
  // Uses UTC date to match server-side UTC date calculations.
  // Do not change to local date without also updating backend report date handling.
  ```
  This preserves the current behavior while documenting the UTC convention explicitly.
- Do NOT change API response shapes, route paths, or backend files.
- Do NOT migrate refresh token storage to cookies (DEC-FE-006).
- Do NOT change the visual design of any page beyond adding a loading indicator in ProtectedRoute.

File Ownership (this phase only — do not touch other files)
- `frontend/src/store/authStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/main.tsx` (authStatus only)
- `handoff/wave-07/phase-04-wave-07-frontend-auth-and-domain/frontend.md`

Delegation Plan
- Frontend: implement all fixes, run build and lint, document

Acceptance Criteria
- After a token refresh, `authStore.user.role` reflects the current role from the backend
- After editing own role in Settings, `authStore.user.role` updates without page reload
- `ProtectedRoute` shows a loading indicator instead of redirecting to login during bootstrap
- Editing any field on an existing warehouse article no longer overwrites the stored density value
- Creating a new warehouse article immediately shows the article in the list without manual reload
- `StockOverviewResponse` TypeScript interface includes `page` and `per_page` fields
- A comment in `reports.ts` and `reportsUtils.ts` documents the UTC convention and the 100-row export limitation
- `npm run build` passes with no TypeScript errors
- `npm run lint` passes

Validation Notes
- 2026-04-08: Orchestrator created Wave 7 Phase 4. Runs in parallel with Phases 1, 2, 3, 5.
- 2026-04-08: Phase 4 agent completed all seven fixes. Frontend build: ✓ (3.37s, no TS errors). Lint: ✓ (0 warnings). Phase 4 closed.

Next Action
- Frontend agent implements all fixes. Can run simultaneously with Phases 1, 2, 3, 5.

---

## Delegation Prompt — Frontend Agent

You are the frontend auth and domain fix agent for Wave 7 Phase 4 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-07/phase-04-wave-07-frontend-auth-and-domain/orchestrator.md` (this file)
- `handoff/decisions/decision-log.md` (find DEC-FE-006 for refresh token storage constraint)
- `frontend/src/store/authStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/main.tsx`
- `backend/app/api/auth/routes.py` (to verify /auth/me response shape)

Your fixes (implement all of them):

1. **N-6: Auth store loading state** (`authStore.ts`, `main.tsx`, `ProtectedRoute.tsx`)
   Add `authStatus: 'idle' | 'loading' | 'authenticated' | 'unauthenticated'` to the auth store
   state and actions. Set it to `'loading'` in `main.tsx` before the `/auth/me` bootstrap call,
   then to `'authenticated'` if `/auth/me` succeeds, `'unauthenticated'` if it fails or if no
   refresh token exists. In `ProtectedRoute.tsx`, when `authStatus === 'loading'`, render a
   loading indicator (e.g., `<Loader />` from `@mantine/core`, centered in the viewport) instead
   of redirecting. This fix must be done FIRST so that the M-5 and M-6 fixes can use the same
   `updateUser()` action you add to the store.

2. **Add `updateUser()` to authStore** (`authStore.ts`)
   Add a `updateUser(user: User)` action that updates only the `user` field in the store, leaving
   `accessToken` and `refreshToken` unchanged. This will be called by M-5 and M-6 below.
   Also update `authStatus` to `'authenticated'` in this action.

3. **M-5: Update user state after token refresh** (`client.ts`)
   In the token refresh interceptor, after `useAuthStore.getState().setAccessToken(newAccessToken)`:
   - Import `authApi` (or use fetch directly if circular imports are a problem)
   - Call `authApi.me()` with the new access token
   - On success: call `useAuthStore.getState().updateUser(meResponse.user)` (or equivalent)
   - On failure: log a warning but do NOT block the original request retry
   Be careful about import order — if importing `authApi` creates a circular dependency with
   `client.ts`, use `useAuthStore.getState()` directly to call the `/auth/me` fetch inline,
   or restructure to avoid the cycle.

4. **M-6: Update user state after self role edit** (`SettingsPage.tsx`)
   In `handleUserSave()`, after the `updateUser()` (settings API) call succeeds:
   - Get `currentUser` from `useAuthStore.getState()`
   - If `editingUserId === currentUser?.id`:
     - Call `authApi.me()` (or the equivalent) to re-fetch the current user
     - Call `useAuthStore.getState().updateUser(freshUser)` to sync auth store
   This ensures sidebar/route access reflects the new role immediately.

5. **H-5: Omit density from article update payload** (`warehouseUtils.ts`)
   Read `buildArticlePayload()` to understand its current signature and usage.
   Determine how to distinguish create vs. update (e.g., whether the function already takes an
   `isEdit` parameter or whether it can be inferred from the calling context).
   For UPDATE operations: remove the `density: 1` line from the payload. Do NOT add density to
   the payload at all — the backend preserves existing density when the field is absent.
   For CREATE operations: keep `density: 1` as the default.
   Verify in `ArticleDetailPage.tsx` that the update call path uses the updated function correctly.

6. **L-2: Refresh warehouse list after create** (`WarehousePage.tsx`)
   In the article create success handler: call `loadArticles()` (or whatever the list-fetch function
   is named) directly after the create succeeds. Remove the `navigate('/warehouse')` call since
   the user is already on that page and navigation is redundant.

7. **M-4: Reports type contract and documentation** (`api/reports.ts`, `reportsUtils.ts`)
   In `api/reports.ts`, update `StockOverviewResponse` to add `page: number` and `per_page: number`
   fields. Add a comment block above the interface:
   ```typescript
   // NOTE: Backend paginates stock overview at page=1, per_page=100 by default.
   // The export endpoint also returns only the first page (100 rows maximum).
   // Full-export support requires a dedicated backend endpoint — tracked as a follow-up.
   ```

8. **M-9: Document UTC date convention** (`reportsUtils.ts`)
   In `getTodayIsoDate()` and `getMonthStartIsoDate()`, add a comment:
   ```typescript
   // Uses UTC date intentionally to match server-side UTC date calculations.
   // Do not change to local date without updating backend report date handling.
   ```
   Do NOT change the behavior — keep `new Date().toISOString().slice(0, 10)`.

After all fixes:
- Run: `cd frontend && npm run build`
- Run: `cd frontend && npm run lint`
- Fix any TypeScript or lint errors before completing
- Write your entry in `handoff/wave-07/phase-04-wave-07-frontend-auth-and-domain/frontend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
