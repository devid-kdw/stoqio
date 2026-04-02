## Phase Summary

Phase
- Phase 1 - Project Setup

Objective
- Create the full project skeleton for the WMS monorepo.
- No business models, no feature routes, and no real UI screens yet.
- Only project structure, configuration, scaffolding, and startup tooling.

Source Docs
- `stoqio_docs/07_ARCHITECTURE.md` § 1
- `stoqio_docs/07_ARCHITECTURE.md` § 5
- `stoqio_docs/07_ARCHITECTURE.md` § 6
- `handoff/README.md`

Delegation Plan
- Backend: create backend skeleton, Flask app factory, config, extensions, requirements, env example, run entrypoint, test scaffold, and a simple health endpoint for verification.
- Frontend: scaffold Vite React TypeScript app, add core dependencies, configure proxy, and create minimal auth/i18n/api scaffolding.
- Testing: verify backend and frontend startup and confirm proxy to `/api/v1/health` works.

Acceptance Criteria
- `backend/` and `frontend/` match the Phase 1 scope from the implementation plan.
- `cd backend && flask run` starts without errors.
- `cd frontend && npm run dev` starts without errors.
- Frontend dev server proxies `/api` to Flask correctly.
- Each agent leaves a trace in its handoff file.

Validation Notes
- Backend and frontend agent deliveries reviewed.
- Fixed frontend Vite proxy target from `http://localhost:5000` to `http://127.0.0.1:5000` to avoid macOS AirPlay conflicts observed by testing.
- Updated `backend/run.py` to load `.env` via `python-dotenv` so the development entry point behaves consistently with the documented setup.
- Added missing top-level Phase 1 skeleton artifacts: root `.gitignore`, root `README.md`, `scripts/build.sh`, and `scripts/deploy.sh`.
- Added Mantine core stylesheet import and updated frontend document title to `WMS`.
- Re-verified:
  - `backend/venv/bin/pytest backend/tests -v` → pass
  - `npm run build` → pass
  - `npm run lint -- --max-warnings=0` → pass
  - `./scripts/build.sh` → pass, copies frontend build to `backend/static/`
  - direct backend health check → `{"status":"ok"}`
  - Vite proxy health check via `http://127.0.0.1:3000/api/v1/health` → `{"status":"ok"}`

Next Action
- Phase 1 is complete and verified.
- Proceed to Phase 2.

## Delegation Prompt - Backend Agent

You are the backend agent for Phase 1 of the WMS project.

Read before coding:
- `stoqio_docs/07_ARCHITECTURE.md` § 1 (folder structure)
- `stoqio_docs/07_ARCHITECTURE.md` § 5 (Pi deployment)
- `stoqio_docs/07_ARCHITECTURE.md` § 6 (development workflow)
- `handoff/README.md`

Goal
- Implement the backend project skeleton only.
- Do not implement database models beyond empty package scaffolding.
- Do not implement feature routes beyond a minimal health endpoint required for verification.
- Do not expand scope into authentication, business logic, or production deployment.

Tasks
1. Create the backend folder structure from `07_ARCHITECTURE.md` § 1.
2. Implement `backend/app/__init__.py` with `create_app()`.
3. Implement `backend/app/extensions.py` with SQLAlchemy, JWT, and Migrate instances.
4. Implement `backend/app/config.py` with Development and Production configs.
   - Read `DATABASE_URL` and `JWT_SECRET_KEY` from environment variables.
   - Production must refuse to start if `JWT_SECRET_KEY` is default, missing, or weak.
5. Create `backend/requirements.txt` with the specified packages.
6. Create `backend/.env.example` with `FLASK_ENV`, `DATABASE_URL`, and `JWT_SECRET_KEY` placeholders.
7. Create `backend/run.py` as the development entry point.
8. Create `backend/tests/conftest.py` scaffold.
9. Add a minimal GET `/api/v1/health` endpoint so Phase 1 proxy verification is possible.

Constraints
- Keep implementation minimal and clean.
- Use the architecture doc as the source of truth for file placement.
- Avoid placeholder logic that implies unfinished business features are implemented.
- If a folder is required by the architecture but has no code yet, add the package scaffold only.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-01-project-setup/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record all files changed, commands run, tests executed, blockers, and assumptions.
- If you discover a spec gap, add it to `handoff/decisions/decision-log.md` and reference it.

Done Criteria
- Backend starts with `flask run` from `backend/`.
- `/api/v1/health` returns a success response.
- Handoff entry is complete.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Phase 1 of the WMS project.

Read before coding:
- `stoqio_docs/07_ARCHITECTURE.md` § 1 (folder structure)
- `stoqio_docs/07_ARCHITECTURE.md` § 6 (development workflow)
- `handoff/README.md`

Goal
- Implement the frontend project skeleton only.
- Do not build real pages or feature flows yet.
- Create the Vite React TypeScript scaffold and the minimum app structure needed for future phases.

Tasks
1. Scaffold a React + TypeScript project using Vite inside `frontend/`.
2. Install dependencies:
   - `react-router-dom@6`
   - `@tanstack/react-query`
   - `zustand`
   - `axios`
   - `i18next`
   - `react-i18next`
   - `@mantine/core`
   - `@mantine/hooks`
3. Configure Vite proxy so all `/api` requests go to `http://127.0.0.1:5000`.
4. Create `frontend/src/main.tsx` and `frontend/src/App.tsx` with a minimal app that renders `WMS`.
5. Create `frontend/src/store/authStore.ts` with fields:
   - `user`
   - `accessToken`
   - `refreshToken`
   - `isAuthenticated`
   All should initialize to null or false as appropriate.
6. Create `frontend/src/i18n/index.ts` plus locale files:
   - `frontend/src/i18n/locales/hr.json`
   - `frontend/src/i18n/locales/en.json`
   - `frontend/src/i18n/locales/de.json`
   - `frontend/src/i18n/locales/hu.json`
   Use empty objects for now.
7. Create `frontend/src/api/client.ts` as an axios client pointed at `/api/v1/`.
   - Add a request interceptor that attaches the bearer token from the Zustand auth store.
   - Add a response interceptor scaffold for future 401 refresh handling, but do not implement refresh flow yet.

Constraints
- Keep the UI minimal.
- Match the architecture file layout where practical for Phase 1.
- Do not invent feature pages beyond basic scaffolding.
- Do not implement auth flow in this phase.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-01-project-setup/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, verification steps, blockers, and assumptions.
- If you discover a spec gap, add it to `handoff/decisions/decision-log.md` and reference it.

Done Criteria
- Frontend starts with `npm run dev` from `frontend/`.
- Frontend code includes proxy config and the requested scaffolds.
- Handoff entry is complete.

## Delegation Prompt - Testing Agent

You are the testing agent for Phase 1 of the WMS project.

Read before testing:
- `stoqio_docs/07_ARCHITECTURE.md` § 5
- `stoqio_docs/07_ARCHITECTURE.md` § 6
- `handoff/README.md`
- `handoff/implementation/phase-01-project-setup/orchestrator.md`
- backend and frontend handoff entries after those agents finish

Goal
- Verify the Phase 1 skeleton works as specified.
- Focus on startup checks and proxy validation.
- Do not expand scope into feature testing.

Tasks
1. Review backend and frontend handoff notes to understand what was changed.
2. Run the minimum verification required by the phase:
   - `cd backend && flask run`
   - `cd frontend && npm run dev`
   - verify that the frontend dev server proxies a request to backend `/api/v1/health`
3. Record exact results.
4. If verification fails, capture the failure precisely and identify whether it is backend, frontend, environment, or integration.
5. Do not silently fix product code unless explicitly asked by the orchestrator; your primary job is verification and clear reporting.

Handoff Requirements
- Append your work log to `handoff/implementation/phase-01-project-setup/testing.md`.
- Use the section shape required by `handoff/README.md`.
- List commands run, observed results, blockers, and residual risks.

Done Criteria
- Verification results are recorded clearly.
- Any failure is actionable and attributed.
