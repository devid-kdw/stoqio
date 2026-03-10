## Phase Summary

Phase
- Phase 3 - Authentication

Objective
- Implement backend and frontend authentication for an existing installation.
- Verify login, refresh, logout, protected routing, and RBAC-aware navigation.
- Keep first-run `/setup` flow out of scope for this phase.

Source Docs
- `stoqio_docs/07_ARCHITECTURE.md` §2, §3, §4, §6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` §1, §3.4, §4
- `stoqio_docs/05_DATA_MODEL.md` §22, §23, §25, §26
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` §13, §15
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Delegation Plan
- Backend: implement auth routes, role guards, rate limiting, logout invalidation, and bootstrap seed data.
- Frontend: implement login page, Zustand auth state, refresh interceptor, protected routing, and RBAC sidebar.
- Testing: verify backend auth contract and frontend behavior on an initialized installation.

Acceptance Criteria
- Backend exposes working `/api/v1/auth/login`, `/refresh`, `/logout`.
- Bootstrap seed creates `admin / admin123` plus required reference data.
- Frontend login flow, route protection, and sidebar RBAC match Phase 3 scope.
- Backend tests pass and frontend builds successfully.
- Phase 3 handoff trail is complete.

Validation Notes
- Backend auth implementation reviewed and accepted after follow-up fixes to logout/refresh semantics.
- Seed/bootstrap reliability was fixed by loading `.env` in `backend/seed.py`, `backend/diagnostic.py`, and `backend/seed_location.py`.
- Frontend follow-up fixes added notification mounting, auth API/store alignment, and explicit redirect-to-login handling after refresh failure.
- Verified:
  - `backend/venv/bin/pytest backend/tests -q` → `32 passed`
  - `cd frontend && npm run lint -- --max-warnings=0` → success
  - `cd frontend && npm run build` → success
  - temporary SQLite verification DB can be migrated, seeded, location-seeded, and authenticated with `admin / admin123`
- Browser-level verification was not run inside the sandbox, so a manual smoke check remains recommended but no open functional blockers remain in code review or automated verification.

Next Action
- Phase 3 can be closed.
- Proceed to Phase 4 - First-Run Setup.

## Live Environment Note

- A post-closure browser login failure on `localhost:5173/login` was traced to the user's real `wms_dev` database being empty, not to a remaining auth implementation defect.
- Running `backend/seed.py` and `backend/seed_location.py` against the actual Postgres database restored the expected Phase 3 initialized-installation state.
- After that fix, login with `admin / admin123` succeeded both against the live backend endpoint and through the Vite proxy path used by the browser.
