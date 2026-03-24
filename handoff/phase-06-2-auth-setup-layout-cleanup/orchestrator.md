## Phase Summary

Phase
- Phase 6.2 - Auth / Setup Layout Cleanup

Objective
- Clean up the legacy Vite scaffold CSS residue around auth/setup screens and establish a small shared frontend baseline so future agents do not keep patching `LoginPage` and `SetupPage` independently.

Source Docs
- `handoff/README.md`
- `handoff/phase-06-1-setup-screen-layout/orchestrator.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2, § 4
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/index.css`
- `frontend/src/App.css`
- `frontend/src/main.tsx`

Current Repo Reality
- The `/setup` screen was recently fixed directly by the orchestrator so the card is centered and larger.
- That fix currently lives only in `SetupPage.tsx`.
- `LoginPage.tsx` and `SetupPage.tsx` still use separate layout approaches.
- `frontend/src/index.css` and `frontend/src/App.css` still contain legacy Vite scaffold styles (`#root`, `place-items`, `color-scheme`, demo button styling, etc.).
- Those scaffold styles are residue from project bootstrap rather than intentional STOQIO UI design.

Contract Locks / Clarifications
- This is a frontend-only cleanup lane. No backend or API changes.
- Do not redesign the whole product shell or authenticated layout.
- Scope is limited to:
- auth/setup page presentation
- dead or misleading global scaffold CSS cleanup
- optional small shared auth/setup wrapper/component if it reduces duplication cleanly
- Preserve the current centered, larger `/setup` presentation introduced in Phase 6.1.
- Do not accidentally change the visual structure of authenticated app pages such as sidebar/content screens.
- If `frontend/src/App.css` is unused, it may be removed. If `frontend/src/index.css` is kept, reduce it to intentional global baseline styles only.

Delegation Plan
- Backend:
- None.
- Frontend:
- Remove or neutralize legacy Vite scaffold CSS and consolidate auth/setup layout into a clearer shared baseline without changing app-shell pages.
- Testing:
- None.

Acceptance Criteria
- `/setup` remains centered and visually prominent.
- `/login` and `/setup` no longer depend on leftover Vite demo/scaffold CSS behavior.
- Global CSS no longer contains misleading demo styles that can affect future layout work.
- Any shared auth/setup layout extraction stays narrowly scoped and does not alter authenticated pages.
- Frontend lint and build pass.
- The phase leaves a clear handoff trail for future agents.

Validation Notes
- None yet.

Next Action
- Delegate to the Frontend Agent only.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Phase 6.2 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/phase-06-1-setup-screen-layout/orchestrator.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2, § 4
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/index.css`
- `frontend/src/App.css`
- `frontend/src/main.tsx`

Goal
- Clean up auth/setup layout drift and remove legacy Vite scaffold CSS residue so `/login` and `/setup` sit on a small intentional baseline instead of demo-template leftovers.

Non-Negotiable Contract Rules
- No backend changes.
- Preserve the current centered, larger `/setup` layout from Phase 6.1.
- Do not refactor the authenticated application shell.
- Keep the cleanup narrowly scoped to auth/setup screens and global scaffold CSS.
- If you extract a shared wrapper/component, keep it limited to auth/setup usage.
- Do not introduce a broad design rewrite.

Tasks
1. Audit `frontend/src/index.css` and `frontend/src/App.css` for legacy Vite scaffold/demo styles.
2. Remove unused or misleading scaffold styles that are not part of the STOQIO design baseline.
3. Ensure the app no longer depends on Vite demo defaults such as:
- `#root` width/padding demo constraints
- `body` centering/place-items behavior
- demo button/link styling
- demo color-scheme assumptions
4. Establish a clean, intentional auth/setup layout baseline:
- either by keeping page-local styles but aligning them clearly
- or by extracting a small shared auth/setup wrapper/layout component
5. Preserve or improve the current `/setup` presentation:
- centered in viewport
- large enough to read as a primary onboarding step
6. Make `/login` and `/setup` feel structurally consistent without changing their functional behavior.

Verification
- Run at minimum:
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/phase-06-2-auth-setup-layout-cleanup/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If you find that the cleanup would require broader app-shell refactoring, stop and log the exact blocker instead of silently expanding scope.

Done Criteria
- Legacy scaffold CSS residue is removed or neutralized.
- `/setup` keeps the corrected centered/larger presentation.
- `/login` and `/setup` share a clearer baseline.
- Lint/build verification is recorded.

## [2026-03-24 17:18] Orchestrator Validation - Phase 6.2 Auth / Setup Layout Cleanup

Status
- accepted

Scope
- Reviewed the frontend-only auth/setup cleanup delivery.
- Verified that the implementation stays within the delegated scope: auth/setup baseline cleanup only, with no app-shell or backend drift.

Docs Read
- `handoff/phase-06-2-auth-setup-layout-cleanup/orchestrator.md`
- `handoff/phase-06-2-auth-setup-layout-cleanup/frontend.md`
- `handoff/phase-06-1-setup-screen-layout/orchestrator.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 2, § 4

Files Reviewed
- `frontend/src/components/auth/AuthLayout.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/index.css`
- `frontend/src/App.css`

Commands Run
```bash
git status --short
git diff -- frontend/src/components/auth/AuthLayout.tsx frontend/src/pages/auth/LoginPage.tsx frontend/src/pages/auth/SetupPage.tsx frontend/src/index.css frontend/src/App.css handoff/phase-06-2-auth-setup-layout-cleanup/frontend.md handoff/phase-06-2-auth-setup-layout-cleanup/orchestrator.md
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- No functional review findings were identified.
- Accepted scope alignment:
- a narrow shared `AuthLayout` wrapper now covers `/login` and `/setup`
- the centered/larger `/setup` presentation from Phase 6.1 is preserved
- no authenticated app-shell layout code was touched
- no backend/API contract was changed
- Accepted cleanup result:
- legacy Vite scaffold/demo CSS content was removed from `frontend/src/index.css` and `frontend/src/App.css`
- both files remain harmless even though they are not currently imported, which removes future agent confusion without introducing runtime risk

Verification
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- This review did not include a live browser smoke pass for `/login` and `/setup`; visual confirmation in the backend-served build remains the only missing manual signal.
- Login copy remains largely English. That predates this cleanup and was not part of the delegated scope.

Next Action
- Treat Phase 6.2 as closed on the current frontend baseline.
- If a later frontend pass targets auth UX polish, build on `AuthLayout` instead of reintroducing page-local centering wrappers.
