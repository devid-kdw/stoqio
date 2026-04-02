## Phase Summary

Phase
- Wave 1 - Phase 13 - Article Statistics + Dark Mode

Objective
- Deliver two independent additions on top of the accepted Reports/Warehouse baseline:
- article-level statistics on the Warehouse article detail screen
- system-wide dark-mode toggle with localStorage persistence

Source Docs
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/05_DATA_MODEL.md` § 16
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`

Delegation Plan
- Backend:
- implement `GET /api/v1/articles/{id}/stats` for ADMIN/MANAGER and add backend coverage
- Frontend:
- add lazy-loaded article statistics UI on article detail and implement the dark-mode toggle/persistence flow
- Testing:
- lock backend regression coverage for the new stats contract and note frontend verification limits

Acceptance Criteria
- `GET /api/v1/articles/{id}/stats` exists and returns the delegated shape
- article with no history returns empty lists without server errors
- period filtering works for the selected window
- article detail lazily loads and renders the statistics section
- dark mode toggles, persists on refresh, and applies across the app baseline
- the phase leaves a complete orchestration, backend, frontend, and testing handoff trail

Validation Notes
- None yet.

Next Action
- Review delivered backend/frontend/testing work against the locked contract and verify the resulting baseline.

## [2026-03-26 18:35 CET] Orchestrator Validation - Wave 1 Phase 13 Article Statistics + Dark Mode

Status
- changes_requested

Scope
- Reviewed the delivered backend, frontend, and testing work for Phase 13 Wave 1.
- Re-ran the relevant backend suite plus frontend lint/build gates.
- Compared the implementation against the delegated API/UI contract and the phase acceptance criteria.

Docs Read
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/backend.md`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/frontend.md`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/testing.md`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/05_DATA_MODEL.md` § 16

Files Reviewed
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `frontend/package.json`
- `frontend/src/api/articles.ts`
- `frontend/src/main.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/reports/ReportsPage.tsx`

Commands Run
```bash
git status --short
git diff -- backend/app/api/articles/routes.py backend/app/services/article_service.py backend/tests/test_articles.py
git diff -- frontend/package.json frontend/package-lock.json frontend/src/api/articles.ts frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/main.tsx frontend/src/pages/warehouse/ArticleDetailPage.tsx
backend/venv/bin/pytest backend/tests/test_articles.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `40 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `343 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Accepted Work
- Backend route wiring for `GET /api/v1/articles/{id}/stats` is present and RBAC is correctly limited to `ADMIN` + `MANAGER`.
- Frontend Statistics section on article detail is lazy-loaded and does not fetch on page mount.
- Recharts was added properly after the earlier dependency blocker was resolved.
- Dark-mode persistence is correctly wired through Mantine's local-storage color-scheme manager with key `stoqio_color_scheme`.

Blocking Findings
- The delivered article-stats API contract drifted from the delegated shape and the testing handoff locked the drift instead of the requested contract. The backend returns `week` instead of `week_start`, returns `stock_history[].balance` instead of `stock_history[].quantity`, and adds undelegated top-level fields (`article_id`, `period_days`). The frontend and tests were then rewritten to match that drift rather than the delegated contract.
- The "no history" backend behavior does not match the delegated acceptance criteria. The task required an article with no transactions to return empty lists, but the backend always zero-fills weekly inbound/outbound buckets and the new tests explicitly enforce that non-empty zero-filled behavior.
- The new article-stats tests are date-brittle and will fail as the real calendar moves on. Both the service and tests depend on `date.today()`, while the fixture hardcodes rows relative to `2026-03-26` and then asserts exact 30-day/90-day inclusion behavior against those fixed timestamps.
- Dark mode is not yet truly system-wide. Shared shell surfaces were updated, but existing hardcoded light surfaces remain in the Reports screen, so the delivered implementation does not satisfy the requested app-wide color-scheme toggle baseline.

Closeout Decision
- Backend, frontend, and testing implementations are partially acceptable but not yet ready for closeout.
- Phase 13 Wave 1 is not formally closed.

Next Action
- Send the phase back for remediation of:
- the article-stats API contract drift (`week_start`, `stock_history[].quantity`, no undelegated top-level fields unless explicitly re-locked)
- the empty-history behavior mismatch
- the brittle date-dependent tests
- the remaining hardcoded light surfaces blocking a truly system-wide dark-mode baseline

## [2026-03-26 19:05 CET] Orchestrator Remediation + Final Validation - Wave 1 Phase 13 Article Statistics + Dark Mode

Status
- accepted

Scope
- Implemented the remaining remediations directly as orchestrator after the prior validation findings.
- Re-ran targeted backend tests, the full backend suite, and frontend lint/build gates.
- Added a short wave-level recap document so later agents can see what Wave 1 changed without reconstructing it from git alone.

Files Changed By Orchestrator
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/orchestrator.md`
- `docs/wave-01-recap.md`

What Changed
- Restored the delegated article-stats API contract:
- weekly buckets now use `week_start`
- `stock_history` now exposes `quantity`
- undelegated top-level fields were removed
- Restored the delegated empty-history behavior:
- article with no history now returns empty arrays for all four series instead of zero-filled weekly placeholders
- Stabilized the backend period logic and tests:
- stats now use UTC "today" semantics
- the seeded stats test data now derives from relative current dates instead of hardcoded March 2026 timestamps
- assertions now lock the delegated contract rather than the earlier drifted one
- Finished the dark-mode baseline for the finding that remained open:
- Reports interactive cards/widgets no longer force light-only white surfaces
- Added a short Wave 1 recap document at `docs/wave-01-recap.md`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_articles.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_articles.py -q` -> `40 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `343 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Closeout Decision
- The prior blocking findings are resolved.
- Phase 13 Wave 1 is formally closed.
- Wave 1 as a whole is formally closed.

Residual Notes
- Manual browser replay of the new Warehouse statistics charts and dark-mode toggle was not repeated in this orchestrator pass; acceptance is based on code-path review plus green backend/frontend verification.

Next Action
- Treat `docs/wave-01-recap.md` and the per-phase handoff trail as the baseline record for all post-Wave-1 work.
