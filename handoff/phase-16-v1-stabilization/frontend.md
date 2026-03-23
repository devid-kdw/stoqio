# Frontend Handoff — Phase 16 V1 Stabilization

Reserved for frontend agent entries. Append only.

## [2026-03-17 18:23] Codex

Status
- completed

Scope
- Reviewed whether the confirmed Phase 16 stabilization fixes required frontend code changes.
- Updated shared documentation/handoff only; no frontend source change was required because the API contract used by the existing Draft Entry and auth UI remains compatible.

Docs Read
- `docs/v1-recap.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `handoff/decisions/decision-log.md`

Files Changed
- None in `frontend/`

Commands Run
```bash
# None
```

Tests
- Passed:
- None
- Failed:
- None
- Not run:
- frontend lint/build were not rerun in this phase because no frontend files changed

Open Issues / Risks
- Frontend still keeps auth tokens only in Zustand memory by design.
- Integer/decimal UOM display logic is still partially duplicated across frontend modules and remains a separate cleanup item.

Next Recommended Step
- If a later frontend stabilization pass happens, centralize UOM quantity formatting around authoritative `decimal_display` metadata instead of hardcoded integer-UOM sets.

## [2026-03-23 17:49] Codex

Status
- completed

Scope
- Fixed frontend auth bootstrap so page refresh keeps the user logged in when a valid refresh token exists.
- Kept the access token memory-only, persisted only the refresh token, and blocked route rendering until silent refresh plus `/auth/me` completed.
- Logged the cross-phase auth-storage policy change in `handoff/decisions/decision-log.md` as `DEC-FE-006` because `stoqio_docs/07_ARCHITECTURE.md` still documents the older memory-only policy.

Docs Read
- `stoqio_docs/07_ARCHITECTURE.md`
- `frontend/src/store/authStore.ts`
- `frontend/src/App.tsx`
- `frontend/src/api/auth.ts`
- `frontend/src/api/client.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `backend/app/api/auth/routes.py`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Files Changed
- `frontend/src/store/authStore.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/App.tsx`
- `handoff/decisions/decision-log.md`
- `handoff/phase-16-v1-stabilization/frontend.md`

Commands Run
```bash
sed -n '240,380p' stoqio_docs/07_ARCHITECTURE.md
sed -n '1,240p' frontend/src/store/authStore.ts
sed -n '1,240p' frontend/src/App.tsx
sed -n '1,240p' frontend/src/api/auth.ts
sed -n '1,260p' frontend/src/api/client.ts
sed -n '1,220p' frontend/src/components/layout/ProtectedRoute.tsx
sed -n '1,240p' frontend/src/pages/auth/LoginPage.tsx
sed -n '1,240p' frontend/src/components/layout/Sidebar.tsx
sed -n '220,360p' backend/app/api/auth/routes.py
npm run lint
npm run build
```

Tests
- Passed:
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- Failed:
- None
- Not run:
- Browser/manual auth smoke checks for refresh-on-reload, expired-access reload, manual localStorage removal, and logout cleanup were not executed in this agent session.

Open Issues / Risks
- `stoqio_docs/07_ARCHITECTURE.md` still says both tokens are memory-only. `DEC-FE-006` is the canonical policy update until the locked docs are explicitly revised.
- Silent bootstrap intentionally refreshes auth only. Setup status still resolves afterward through the existing `SetupGuard`, so protected routes avoid login flicker but may still show the setup-status loading state on first post-refresh render.

Next Recommended Step
- Run the browser checks from the task brief against a real backend session and then update the locked architecture/auth docs to replace the old memory-only token-storage note with the `DEC-FE-006` policy.

## [2026-03-23 17:58] Codex

Status
- completed

Scope
- Hardened the auth bootstrap after the initial implementation still reproduced a reload-to-login failure during user testing.
- Moved silent refresh bootstrap ahead of route rendering in `main.tsx`, hydrated the refresh token into Zustand before bootstrap requests, added a localStorage fallback in the axios 401 refresh path, and copied the fresh production bundle into `backend/static` for backend-served testing.

Docs Read
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `scripts/build.sh`
- `handoff/phase-16-v1-stabilization/frontend.md`

Files Changed
- `frontend/src/App.tsx`
- `frontend/src/main.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `handoff/phase-16-v1-stabilization/frontend.md`

Commands Run
```bash
npm run lint
npm run build
./scripts/build.sh
```

Tests
- Passed:
- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `./scripts/build.sh`
- Failed:
- None
- Not run:
- Browser/manual auth smoke checks were still not executed in the agent session after refreshing the backend-served bundle.

Open Issues / Risks
- If the Flask process caches static assets aggressively in the browser, user retesting should use a hard refresh so the newly copied `backend/static` assets are fetched.
- `stoqio_docs/07_ARCHITECTURE.md` remains stale versus `DEC-FE-006`.

Next Recommended Step
- Retest the refresh flow against the backend-served app on `:5000` with a hard reload. If it still fails, capture the failing `/api/v1/auth/refresh` or `/api/v1/auth/me` response from the browser network tab so the next debugging step targets the real failing contract instead of frontend timing.
