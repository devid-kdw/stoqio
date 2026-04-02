## Phase Summary

Phase
- Phase 4 - First-Run Setup

Objective
- Implement the first-run setup flow end to end:
  - detect missing `Location`
  - redirect ADMIN to `/setup`
  - block normal app usage until setup is complete
  - create the initial `Location`

Source Docs
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2
- `stoqio_docs/05_DATA_MODEL.md` § 23
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/07_ARCHITECTURE.md` § 4
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Delegation Plan
- Backend: add `/api/v1/setup/status`, add ADMIN-only `POST /api/v1/setup`, validate payload, and cover the flow with backend tests.
- Frontend: add `/setup` page, setup API client support, post-login setup branching, and a global setup guard for authenticated routes.
- Orchestrator follow-up: review Phase 4 delivery, close residual risks, update docs, and decide whether the phase can be marked complete.

Acceptance Criteria
- Fresh database: ADMIN login redirects to `/setup`.
- Completing setup creates the initial `Location` and redirects to `/approvals`.
- Existing initialized installation skips `/setup` and goes to the normal home route.
- `POST /api/v1/setup` without auth returns `401`.
- `POST /api/v1/setup` with non-ADMIN role returns `403`.
- `POST /api/v1/setup` after setup is already complete returns `409`.

Validation Notes
- Backend and frontend agent deliveries were reviewed against the Phase 4 prompt and source docs.
- Orchestrator follow-up implemented the remaining closure items after review:
  - `backend/app/api/setup/routes.py`
  - `backend/tests/test_setup.py`
  - `frontend/src/utils/setup.ts`
  - `frontend/src/pages/auth/SetupPage.tsx`
  - `stoqio_docs/08_SETUP_AND_GLOBALS.md`
  - `stoqio_docs/06_SESSION_NOTES.md`
  - `handoff/decisions/decision-log.md`
- Follow-up fixes applied:
  - backend setup creation now uses DB-backed singleton conflict handling for the single supported v1 `Location`
  - setup submission now retries once on network/server failure and falls back to a full-page retry state on repeated failure
  - docs now explicitly define non-ADMIN behavior while setup is pending
- Re-verified after follow-up:
  - `backend/venv/bin/pytest backend/tests -q` → pass (`47 passed`)
  - `cd frontend && npm run lint -- --max-warnings=0` → pass
  - `cd frontend && npm run build` → pass
- No open Phase 4 blockers remain after follow-up review.

Next Action
- Phase 4 is complete.
- Proceed to Phase 5 - Draft Entry.
