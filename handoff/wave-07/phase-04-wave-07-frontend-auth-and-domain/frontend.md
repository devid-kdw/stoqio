## 2026-04-08 Frontend Agent — Wave 7 Phase 4

Status
- completed

Scope
- Implemented all seven findings from the 2026-04-08 dual-agent code review:
  N-6 (ProtectedRoute loading state), M-5 (token refresh user state), M-6 (self role edit auth sync),
  H-5 (warehouse article density overwrite), L-2 (warehouse list refresh after create),
  M-4 (reports type contract), M-9 (UTC date convention documentation).

Docs Read
- handoff/README.md
- handoff/wave-07/phase-04-wave-07-frontend-auth-and-domain/orchestrator.md
- handoff/decisions/decision-log.md
- frontend/src/store/authStore.ts
- frontend/src/api/client.ts
- frontend/src/api/auth.ts
- frontend/src/components/layout/ProtectedRoute.tsx
- frontend/src/pages/settings/SettingsPage.tsx
- frontend/src/pages/warehouse/warehouseUtils.ts
- frontend/src/pages/warehouse/ArticleDetailPage.tsx
- frontend/src/pages/warehouse/WarehousePage.tsx
- frontend/src/api/reports.ts
- frontend/src/pages/reports/reportsUtils.ts
- frontend/src/main.tsx
- frontend/src/api/articles.ts (to verify ArticleMutationPayload.density is optional)

Files Changed
- frontend/src/store/authStore.ts
  Added `AuthStatus` type, `authStatus` field to state and `getLoggedOutState()`.
  Added `setAuthStatus()` and `updateUser()` actions.
  Updated `login()` and `setAuth()` to set authStatus to 'authenticated'.
- frontend/src/main.tsx
  `bootstrapAuth()`: sets authStatus to 'loading' before the /auth/me bootstrap call,
  'unauthenticated' when no refresh token exists (setAuth/logout handle the other transitions).
- frontend/src/components/layout/ProtectedRoute.tsx
  Added authStatus check: renders `<Center><Loader /></Center>` when authStatus === 'loading'
  instead of redirecting to login prematurely (N-6 fix).
- frontend/src/api/client.ts
  Token refresh interceptor now calls `authApi.me(newAccessToken)` after storing the new token
  and updates authStore.user via `updateUser()`. Failure is non-fatal (warning logged only).
- frontend/src/pages/settings/SettingsPage.tsx
  Added `authApi` import. `handleUserSave()` now checks if editingUserId === currentUser?.id;
  if so, calls `authApi.me()` and syncs authStore via `updateUser()` (M-6 fix).
- frontend/src/pages/warehouse/warehouseUtils.ts
  `buildArticlePayload()` now accepts optional `isEdit` parameter (default false).
  When isEdit=true, density is omitted from the payload (backend preserves existing value).
  When isEdit=false (create), density: 1 is included as the initial default.
- frontend/src/pages/warehouse/ArticleDetailPage.tsx
  Updated the `articlesApi.update()` call to pass `buildArticlePayload(editForm, true)`.
  NOTE: This file is outside the strict ownership list but the fix is required for H-5 to work —
  the update call site must pass isEdit=true. Only one line changed.
- frontend/src/pages/warehouse/WarehousePage.tsx
  `handleCreateSubmit()`: replaced `navigate('/warehouse')` with `void loadArticles()`.
  Updated useCallback dependency array from [navigate] to [loadArticles].
- frontend/src/api/reports.ts
  Added `page: number` and `per_page: number` fields to `StockOverviewResponse`.
  Added comment block documenting the 100-row export limitation and follow-up requirement.
- frontend/src/pages/reports/reportsUtils.ts
  Added UTC intent comments to `getTodayIsoDate()` and `getMonthStartIsoDate()`.
  Changed `value.setDate(1)` to `value.setUTCDate(1)` in getMonthStartIsoDate() to make
  UTC behavior consistent and explicit (not just UTC-by-accident).
- frontend/src/pages/reports/__tests__/ReportsPage.test.tsx
  Added `page: 1` and `per_page: 100` to the mock `StockOverviewResponse` in `beforeEach`
  to satisfy the updated type contract. Build would have failed without this fix.

Commands Run
```bash
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run lint
```

Tests
- Passed: `npm run build` (TypeScript + Vite) — clean, no errors
- Passed: `npm run lint` — clean, no errors
- Not run: Vitest unit tests (not required by acceptance criteria; test mock updated for TS compliance)

Open Issues / Risks
- ArticleDetailPage.tsx was touched despite not being in the strict ownership list.
  The change is a single-line targeted fix required to complete H-5. The orchestrator's
  "verify in ArticleDetailPage.tsx" instruction implies this was expected.
- The `loadArticles()` guard in WarehousePage.tsx checks `initialLoadDoneRef.current`. After
  a successful create, the initial load has already completed, so this guard is satisfied.
  No race condition risk.
- M-5 user refresh after token refresh: the `authApi.me()` call runs inside the `.then()` of
  the refresh promise. This makes the refresh promise settle slightly later, but the await of
  `refreshPromise` in the caller still resolves with the new access token correctly because
  the function returns `newAccessToken` after the me() try/catch.
- The 100-row export cap (M-4) is documented but not fixed — a backend endpoint change is
  required and is tracked as a follow-up per the orchestrator's instructions.

Next Recommended Step
- Orchestrator validates fixes against acceptance criteria.
- Follow-up: implement a dedicated full-export backend endpoint for stock overview
  (currently capped at 100 rows on export — documented as known limitation).
