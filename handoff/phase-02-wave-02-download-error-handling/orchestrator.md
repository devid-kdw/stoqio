## Phase Summary

Phase
- Wave 2 - Phase 2 - Download/Error Handling Standardization

Objective
- Standardize frontend blob-download error handling so backend JSON error payloads survive `responseType: 'blob'` flows and surface the real backend `message`.
- Remove duplicated local network/server error helpers where `frontend/src/utils/http.ts` already provides the accepted retry/error baseline.
- Leave a durable orchestration trail for the frontend/testing-only cleanup phase.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-028`, `F-032`)
- `stoqio_docs/17_UI_REPORTS.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/package.json`

Current Repo Reality
- The repo already has the correct async blob-error parser in `frontend/src/utils/http.ts` as `getApiErrorBodyAsync(...)`.
- The Warehouse barcode flow in `frontend/src/pages/warehouse/ArticleDetailPage.tsx` already uses the correct blob-error handling pattern and is the reference implementation for this phase.
- Reports exports in `frontend/src/pages/reports/ReportsPage.tsx` and Order PDF download in `frontend/src/pages/orders/OrderDetailPage.tsx` still use synchronous error-body parsing after blob requests, so backend business-error messages can be lost behind generic toasts.
- Older/high-churn pages still duplicate page-local `isNetworkOrServerError(...)`, `getApiErrorBody(...)`, and/or local retry wrappers instead of importing the shared HTTP utility layer.
- The repo currently has no frontend test runner, no frontend test script, and no existing frontend test files. Any automated frontend coverage added in this phase must account for that reality explicitly.

Contract Locks / Clarifications
- This phase is frontend-only plus testing. No backend agent is delegated.
- Blob-download failure handling must use `await getApiErrorBodyAsync(error)` anywhere the request path uses `responseType: 'blob'`.
- At minimum, fix:
- Reports export actions
- Order PDF download
- any additional blob-download flow discovered during the audit that still uses the wrong synchronous parser
- Use the Warehouse barcode download implementation as the canonical local reference pattern. Do not invent a second blob-error handling style.
- Shared HTTP baseline means reusing `runWithRetry(...)`, `isNetworkOrServerError(...)`, `getApiErrorBody(...)`, and `getApiErrorBodyAsync(...)` from `frontend/src/utils/http.ts` where equivalent helpers already exist.
- This phase is not a general i18n/copy rewrite. Preserve established page-level user-facing wording unless a message change is strictly required by the helper convergence or the touched path already delegates to the shared baseline.
- Do not change backend endpoints, response shapes, export/PDF success behavior, filenames, or RBAC visibility rules.
- Do not broaden this into a general app-wide HTTP abstraction refactor. Limit cleanup to the delegated pages/flows and clearly log any intentionally untouched duplicate with rationale.
- Because the repo has no frontend test harness today, the testing agent may add the smallest viable test stack needed to fulfill the delegated automated coverage. Keep that addition minimal and scoped to this phase.

Delegation Plan
- Backend:
- None for this phase.
- Frontend:
- patch blob-download error handling, converge duplicated helper logic on the shared HTTP utility layer, and keep user-facing behavior stable outside the locked cleanup scope
- Testing:
- add minimal automated frontend coverage for blob-download failures and shared retry/error regressions, introducing the smallest viable test harness only if required

Acceptance Criteria
- A failing Reports export that returns a blob-encoded backend JSON error surfaces the real backend `message` in the UI toast.
- A failing Order PDF download that returns a blob-encoded backend JSON error surfaces the real backend `message` in the UI toast.
- Reports exports, Order PDF download, and any additional discovered blob-download flow no longer rely on synchronous blob-error parsing.
- `DraftEntryPage`, `ApprovalsPage`, `DraftGroupCard`, `ReceivingPage`, and affected setup/auth wrappers no longer carry redundant local network/server helper implementations when the shared HTTP utility already covers that behavior.
- Existing retry/fatal-state behavior for the touched pages remains intact after helper convergence.
- New automated coverage exists for the delegated blob-download failure scenarios and passes.
- The phase leaves a complete orchestration, frontend, and testing handoff trail.

Validation Notes
- 2026-03-27 17:32:09 CET — Orchestrator review completed.
- Accepted:
- Frontend implementation matches the delegated scope. All blob-download flows found in the repo now align with the accepted async parser pattern:
- `frontend/src/pages/reports/ReportsPage.tsx` uses `await getApiErrorBodyAsync(error)` for stock, surplus, and transactions exports.
- `frontend/src/pages/orders/OrderDetailPage.tsx` uses `await getApiErrorBodyAsync(error)` for PDF download failures.
- Existing warehouse barcode flows remained on the correct reference pattern.
- Shared HTTP helper convergence landed on the delegated pages without broadening into unrelated product changes.
- Runtime verification re-run by orchestrator passed:
- `cd frontend && CI=true npm run test` -> 4 files passed, 17 tests passed
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- Missing / needs follow-up:
- `handoff/phase-02-wave-02-download-error-handling/testing.md` does not fully follow the required section shape from `handoff/README.md`. It is missing the explicit `Docs Read`, `Files Changed`, `Tests`, and `Open Issues / Risks` section names required by protocol, even though most of that information is present under alternate headings.
- Residual risk:
- Setup/auth wrapper cleanup was verified by code review plus lint/build, but the new automated tests cover the explicitly requested blob-download regressions and Draft Entry / Approvals / Receiving fatal-state behavior, not the setup/auth wrappers.
- 2026-03-27 17:35:32 CET — Follow-up closed by Orchestrator on user request.
- Orchestrator appended a documentation-only correction entry to `handoff/phase-02-wave-02-download-error-handling/testing.md` so the file now explicitly contains the required `Status`, `Scope`, `Docs Read`, `Files Changed`, `Commands Run`, `Tests`, `Open Issues / Risks`, and `Next Recommended Step` sections.
- No product code, test code, or verification results were changed in this follow-up.

Next Action
- Phase is functionally accepted.
- Ask the Testing Agent to append a protocol-compliant handoff entry to `testing.md` so the documentation trail fully matches `handoff/README.md`.
- Documentation follow-up is now complete; no additional action is required for this phase unless the user wants a new wave opened.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 2 Phase 2 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-028`, `F-032`)
- `stoqio_docs/17_UI_REPORTS.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-02-wave-02-download-error-handling/orchestrator.md`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/api/reports.ts`
- `frontend/src/api/orders.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`

Goal
- Standardize blob-download error handling so frontend download/export flows preserve backend JSON error messages, and converge duplicated local retry/network/server helper logic onto the shared HTTP utility layer where the repo already has that baseline.

Current Repo Reality
- The correct blob-download error handling pattern already exists in `frontend/src/pages/warehouse/ArticleDetailPage.tsx`.
- `frontend/src/utils/http.ts` already exposes the shared primitives this phase should converge on:
- `runWithRetry(...)`
- `isNetworkOrServerError(...)`
- `getApiErrorBody(...)`
- `getApiErrorBodyAsync(...)`
- Reports exports and Order PDF download still lose backend blob-error messages because they use synchronous parsing on failure paths.
- Older pages still define local helper functions that duplicate the shared utility behavior.

Non-Negotiable Contract Rules
- Use `await getApiErrorBodyAsync(error)` for blob-download failure toasts wherever the request path uses `responseType: 'blob'`.
- Use the Warehouse barcode flow as the implementation reference pattern.
- Audit all blob-download flows; patch at minimum Reports exports and Order PDF download, plus any additional blob-download path you discover during the audit.
- Reuse the shared HTTP helper layer where it already matches the needed behavior. Do not introduce new duplicate local helpers for retry/network/server parsing.
- Keep success-path download behavior unchanged.
- Keep backend business-error visibility and RBAC behavior unchanged.
- Do not broaden this into a general frontend redesign, i18n rewrite, or large-scale refactor of unrelated pages.
- Preserve existing page-level user-facing wording where feasible; this phase is about helper convergence and error preservation, not copy churn.

Tasks
1. Audit every frontend flow that calls an endpoint with `responseType: 'blob'`.
2. Replace synchronous blob-error parsing with `await getApiErrorBodyAsync(error)` everywhere appropriate.
3. Use `frontend/src/pages/warehouse/ArticleDetailPage.tsx` as the reference implementation for correct blob-error handling.
4. Apply the fix at minimum to:
- Reports export actions
- Order PDF download
- any additional blob-download flow discovered during patching
5. Audit pages that still define local connection/network/server error helpers instead of importing from `frontend/src/utils/http.ts`.
6. Normalize the following to the shared utility layer where the existing helpers are equivalent:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- any setup/auth wrapper still carrying duplicated connection/fatal-state logic
7. Keep user-facing behavior unchanged outside improved backend-error preservation and helper consistency.
8. Record any intentionally untouched duplicate helper or wrapper with a short rationale in your handoff instead of silently skipping it.

Verification
- Run at minimum:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Verify by code-path review that:
- blob-download failure handlers now await `getApiErrorBodyAsync(error)`
- touched pages import shared HTTP helpers instead of redefining equivalent ones
- retry/fatal-state behavior for the touched pages is preserved

Handoff Requirements
- Append your work log to `handoff/phase-02-wave-02-download-error-handling/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, blob-download flows audited, commands run, verification performed, open issues, and assumptions.
- If you discover a contract ambiguity between the review finding, repo reality, and this prompt, log it explicitly instead of silently inventing a new rule.

Done Criteria
- Blob-download error handling is standardized on the async parser where required.
- Reports export and Order PDF download preserve backend error messages.
- Duplicated local HTTP helper logic is removed from the delegated pages where the shared utility already covers it.
- Lint/build verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 2 Phase 2 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-028`, `F-032`)
- `stoqio_docs/17_UI_REPORTS.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-02-wave-02-download-error-handling/orchestrator.md`
- frontend handoff for this phase after the Frontend Agent finishes
- `frontend/src/utils/http.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/package.json`

Goal
- Lock automated coverage for blob-download failure handling and confirm the shared HTTP baseline cleanup does not regress the touched pages' retry/error behavior.

Current Repo Reality
- The repo currently has no frontend test runner, no frontend test script, and no existing frontend test files.
- If automated frontend coverage requires new tooling, you must add the smallest viable test harness needed for this phase.
- The Warehouse barcode flow already provides the correct blob-error handling reference behavior; Reports and Order PDF are the minimum required regressions to lock.

Non-Negotiable Test Rules
- Prefer the smallest viable mocked interaction test setup. Keep new tooling/config minimal and clearly scoped.
- Do not rewrite product behavior just to make tests easier. If a blocker exists, log the exact blocker.
- Do not relax the delegated expectation down to manual-only verification unless you first prove why automated coverage is not feasible in the current repo state.
- Keep ownership primarily on test infra/config and new test files. If you need a production-code change beyond what the Frontend Agent delivered, log the mismatch clearly instead of silently broadening scope.

Tasks
1. Add frontend tests or mocked interaction tests for blob-download failures:
- Reports export returns a blob JSON error -> correct toast text is shown
- Order PDF download returns a blob JSON error -> correct toast text is shown
2. Add or update tests/smoke checks to confirm the affected pages still follow the shared retry/error baseline after the helper cleanup without breaking existing behavior.
3. If no frontend test harness exists, add the smallest viable one needed to run the delegated tests.
4. Keep the new test surface as tight as possible:
- focus on blob-error preservation
- focus on retry/error regression around the touched cleanup paths
- avoid sprawling page-by-page rewrites

Verification
- Run the new frontend test command(s) you add.
- Also run:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Confirm the automated coverage proves:
- real backend blob-error `message` text survives in Reports export failure handling
- real backend blob-error `message` text survives in Order PDF failure handling
- helper cleanup does not break the touched pages' retry/fatal-state expectations

Handoff Requirements
- Append your work log to `handoff/phase-02-wave-02-download-error-handling/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record test infra additions, files changed, commands run, tests passed/failed, open issues, and assumptions.
- If you add a new frontend test harness, explain briefly why it was necessary and keep the change set minimal.
- If any delegated verification remains manual-only, say exactly what you found and why automated coverage was insufficient.

Done Criteria
- Automated coverage exists for the delegated blob-download failure scenarios.
- The delegated retry/error cleanup has regression protection.
- All new tests pass and are recorded in handoff.
