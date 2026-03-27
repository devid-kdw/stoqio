## Phase Summary

Phase
- Wave 2 - Phase 3 - Croatian-First Login/Setup/Fatal-State Localization

Objective
- Finish the Croatian-first migration for login/setup/fatal-state UX without changing flows, layout, or feature scope.
- Add the missing localized backend catalog entries for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` so receiving/order-line domain errors stop falling back to English.
- Keep this phase strictly limited to localization and consistency cleanup. No UX redesign, no behavior changes, no new features.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-029`, `F-031`, `F-033`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-02-wave-02-download-error-handling/orchestrator.md`
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/services/order_service.py`
- `backend/app/services/receiving_service.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_receiving.py`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`

Current Repo Reality
- `backend/app/utils/i18n.py` currently does not define catalog entries for `ORDER_LINE_REMOVED` or `ORDER_LINE_CLOSED`, even though both codes are already raised by backend services.
- `backend/app/services/order_service.py` raises both codes via `_ensure_line_open(...)`, and `backend/app/services/receiving_service.py` raises both codes during linked-order receipt validation.
- Static route trace confirms Orders and Receiving routes already pass service exceptions through `app.utils.errors.api_error(...)`, so this phase should not need backend route changes just to localize messages.
- `frontend/src/pages/auth/LoginPage.tsx` is still materially English-first for visible login copy and auth-failure fallback text.
- `frontend/src/components/layout/SetupGuard.tsx` still shows English fatal-state copy and an English admin-only setup-block toast.
- `frontend/src/utils/http.ts` still exports an English `CONNECTION_ERROR_MESSAGE`, which propagates into pages that already import the shared constant.
- The currently targeted fatal-state pages still contain English titles and retry labels:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx` already has a Croatian local connection message, but it is still a page-local duplicate instead of using the shared baseline.
- `frontend/src/pages/orders/OrdersPage.tsx` also still contains English fatal-state copy, but it is explicitly out of scope for this phase because the user requested a targeted sweep only.
- The current worktree already contains a frontend Vitest/RTL harness from the previous Wave 2 Phase 2 work. Even so, this phase's testing scope remains backend automated coverage plus manual frontend verification only. Do not broaden this phase into new or updated frontend automated tests.
- The repo is currently dirty from the prior phase. Agents must work with existing uncommitted changes and must not revert unrelated edits.

Contract Locks / Clarifications
- This phase touches only user-visible UI copy and localized backend catalog strings.
- The following must NOT be translated, renamed, or otherwise modified unless strictly required by existing code references:
- API error code strings such as `ORDER_LINE_REMOVED`, `ORDER_LINE_CLOSED`, `UNAUTHORIZED`
- TypeScript type names, interface names, enum values
- i18n key names in JSON locale files
- Python enum values in backend models
- `console.log` strings
- Any string that is not directly rendered to the user
- Backend scope is additive only for the i18n catalog:
- Add exactly two message catalog entries: `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED`
- Do not rename the codes themselves
- Do not alter existing catalog entries
- Do not change backend routes unless a direct trace proves localization bypasses `api_error(...)` (current trace says it does not)
- Frontend scope is limited to the explicitly identified login/setup/fatal-state/auth-bootstrap copy surfaces:
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx` only insofar as auth/bootstrap/fatal-state connection copy follows the shared Croatian baseline after the shared constant changes
- Do not broaden this into a full-app localization sweep. `OrdersPage`, unrelated empty states, success toasts, validation text outside the explicitly named surfaces, and broader i18n scaffolding are out of scope unless the user expands the phase.
- No UX redesign, no layout changes, no route changes, no flow changes, no new features.
- Shared fatal-state consistency should be achieved by converging onto the shared `frontend/src/utils/http.ts` constant wherever the local page copy is only a connection-error duplicate. If a local constant remains, the rationale must be logged explicitly.
- Testing scope for this phase:
- Add backend automated coverage for the missing localized order-line domain errors
- Do not create, add, or expand frontend automated tests for this phase
- Document clear manual frontend verification steps in `testing.md`

Delegation Plan
- Backend:
- add the two missing backend i18n catalog entries, confirm Orders/Receiving already go through `api_error(...)`, and leave a durable backend handoff
- Frontend:
- localize the explicitly named login/setup/fatal-state/auth-bootstrap surfaces only, converging targeted pages onto the shared Croatian connection-error baseline where appropriate
- Testing:
- add backend tests for localized `ORDER_LINE_REMOVED` / `ORDER_LINE_CLOSED` responses and document manual frontend verification only

Acceptance Criteria
- `backend/app/utils/i18n.py` contains localized entries for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` in `hr`, `en`, `de`, and `hu`.
- Orders and Receiving service exceptions for those codes still flow through the standard `api_error(...)` path without route-contract changes.
- The login page is Croatian-first for all visible text identified in the user brief:
- title
- subtitle/helper text
- username field label and placeholder
- password field label and placeholder
- submit button label
- inline missing-credentials validation message
- auth-failure fallback text
- `frontend/src/components/layout/SetupGuard.tsx` shows Croatian fatal-state title, message, and retry button, and no English connection fallback remains visible there.
- `frontend/src/utils/http.ts` exports a Croatian `CONNECTION_ERROR_MESSAGE`, and the targeted pages using it render Croatian fatal-state copy.
- The targeted page sweep is completed and limited to the requested surfaces:
- `DraftEntryPage.tsx`
- `ApprovalsPage.tsx`
- `ReceivingPage.tsx`
- `OrderDetailPage.tsx`
- targeted auth/bootstrap fallback strings visible to the user
- Receiving/order-line domain error toasts for removed/closed lines show localized Croatian backend messages rather than English fallback.
- Backend tests covering the new localized order-line domain errors pass.
- No API error codes, enum values, TypeScript type/interface names, or locale key names are renamed or translated.
- The phase leaves complete backend, frontend, testing, and orchestration handoff notes.

Validation Notes
- 2026-03-27 17:49:31 CET — Orchestrator review completed.
- Accepted:
- `backend/app/utils/i18n.py` now contains localized catalog entries for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` in `hr`, `en`, `de`, and `hu`.
- Orders and Receiving route tracing remains clean: service exceptions still flow through the standard `api_error(...)` path in `backend/app/api/orders/routes.py` and `backend/app/api/receiving/routes.py`.
- Targeted login/setup/fatal-state copy is Croatian-first on the requested frontend surfaces, and `frontend/src/utils/http.ts` now provides a Croatian shared `CONNECTION_ERROR_MESSAGE`.
- Runtime verification re-run by orchestrator:
- `cd backend && venv/bin/python -m pytest tests/test_receiving.py tests/test_i18n.py` -> 40 passed
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- Findings:
- Existing frontend automated tests are now red because `frontend/src/pages/__tests__/fatal-error-smoke.test.tsx` still expects the old English `Connection error.` text for `DraftEntryPage` and `ApprovalsPage`. Re-running `cd frontend && CI=true npm run test` fails with 2 failing assertions and 15 passing tests. This is a real regression in the currently present test suite, even though this phase did not authorize expanding frontend automation.
- `frontend/src/pages/receiving/ReceivingPage.tsx` includes one out-of-scope copy edit: the linked-order warning was changed to `Ova narudžbenica je već zatvorena.` even though the phase explicitly limited `ReceivingPage` changes to fatal-state / connection-error copy only.
- Residual risk:
- `handoff/phase-03-wave-02-croatian-first-localization/testing.md` documents the manual frontend verification checklist, but those browser checks were not executed in this review environment.
- 2026-03-27 17:51:38 CET — Follow-up fixes implemented directly by Orchestrator on user request.
- Orchestrator updated `frontend/src/pages/__tests__/fatal-error-smoke.test.tsx` so the existing frontend smoke tests now assert the current Croatian fatal-state copy instead of the previous English text.
- Orchestrator reverted the out-of-scope `ReceivingPage` linked-order warning copy change in `frontend/src/pages/receiving/ReceivingPage.tsx` back to its previous text so the phase stays within the requested localization surface.
- Verification re-run by Orchestrator after the follow-up fixes:
- `cd frontend && CI=true npm run test` -> 4 files passed, 17 tests passed
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Next Action
- Phase is accepted.
- No further action is required for this phase unless the user wants to broaden the Croatian-first sweep beyond the currently scoped surfaces.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 2 Phase 3 of the STOQIO WMS project.

You are not alone in the codebase. The repo is currently dirty from the prior phase. Do not revert or overwrite unrelated edits made by other agents or the user. Your ownership is limited to backend localization code, relevant backend tests only if truly needed to support your backend change, and `handoff/phase-03-wave-02-croatian-first-localization/backend.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-033`)
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-03-wave-02-croatian-first-localization/orchestrator.md`
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/services/order_service.py`
- `backend/app/services/receiving_service.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_receiving.py`

Goal
- Add the missing localized backend catalog entries for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` without changing route or service contracts.

Current Repo Reality
- `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` are already emitted by `order_service.py` and `receiving_service.py`.
- Orders and Receiving routes already catch service exceptions and pass them through `api_error(...)`, so backend message localization should remain a catalog-only change unless your code trace proves otherwise.
- The frontend depends on the backend `message` field staying localized while `error` codes remain English and stable.

Non-Negotiable Contract Rules
- Add catalog entries for exactly these two codes only:
- `ORDER_LINE_REMOVED`
- `ORDER_LINE_CLOSED`
- Each catalog entry must contain translations for:
- `hr`
- `en`
- `de`
- `hu`
- Suggested Croatian strings:
- `ORDER_LINE_REMOVED`: `Stavka narudžbe je uklonjena.`
- `ORDER_LINE_CLOSED`: `Stavka narudžbe je već zatvorena.`
- Do not rename the error codes.
- Do not alter existing catalog entries.
- Do not change Python enum values, service error codes, route URLs, response shape, or any non-user-facing strings.
- Confirm by code trace that the affected Orders/Receiving routes already go through `api_error(...)`. Do not perform unnecessary route edits if the trace is clean.

Tasks
1. Add localized message catalog entries in `backend/app/utils/i18n.py` for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED`.
2. Confirm that Orders and Receiving routes which surface these codes already pass through the standard `api_error(...)` path.
3. Keep backend changes minimal and localized to this phase scope.
4. Append your work log to `handoff/phase-03-wave-02-croatian-first-localization/backend.md` using the section shape required by `handoff/README.md`.

Verification
- Run the smallest relevant backend verification you need for your change.
- If you run backend tests, record exact commands and results.
- If you rely on route tracing instead of route edits, record that explicitly in handoff.

Done Criteria
- `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` exist in the backend message catalog for `hr`, `en`, `de`, and `hu`.
- Route tracing confirms standard localized `api_error(...)` handling already applies.
- No backend contract drift was introduced.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 2 Phase 3 of the STOQIO WMS project.

You are not alone in the codebase. The repo is currently dirty from the prior phase. Do not revert or overwrite unrelated edits made by other agents or the user. Your ownership is limited to the targeted localization files below and `handoff/phase-03-wave-02-croatian-first-localization/frontend.md`.

Owned product files
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx` only if needed for the targeted auth/bootstrap/fatal-state strings after the shared constant update

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-029`, `F-031`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-03-wave-02-croatian-first-localization/orchestrator.md`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`

Goal
- Finish the Croatian-first migration for the specifically requested login/setup/fatal-state/auth-bootstrap surfaces without changing structure, behavior, or scope.

Current Repo Reality
- `LoginPage.tsx` is still English-first for visible login copy and fallback auth error text.
- `SetupGuard.tsx` still uses English fatal-state copy and an English admin-only setup-block toast.
- `frontend/src/utils/http.ts` still exports an English `CONNECTION_ERROR_MESSAGE`, which keeps targeted fatal-state pages mixed-language.
- `ReceivingPage.tsx` already has a Croatian local connection message, but it remains a page-local duplicate instead of the shared baseline.
- `OrdersPage.tsx` also has English fatal-state copy, but it is explicitly out of scope for this phase and must not be swept opportunistically.

Non-Negotiable Contract Rules
- This phase touches only user-visible UI copy on the explicitly requested surfaces.
- Do not translate or rename:
- API error code strings
- TypeScript type names
- interface names
- enum values
- locale JSON key names
- variables, props, or function names
- `console.log` strings
- any non-rendered/internal string
- Do not redesign the login page, setup wrappers, or fatal-state layouts.
- Do not change route flow, retry logic, form structure, field wiring, or behavior.
- Do not broaden this into a full-app localization sweep.
- Do not touch `frontend/src/pages/orders/OrdersPage.tsx` in this phase.
- On targeted pages, change only the specifically identified fatal-state / connection-error / auth-bootstrap strings. Leave unrelated copy alone unless the user-visible string is directly named in the brief.
- If a targeted page has a local duplicate `CONNECTION_ERROR_MESSAGE` and the shared Croatian constant now matches the intended wording, remove the local duplicate and import from `frontend/src/utils/http.ts`.

Tasks
1. Translate all visible login-page copy in `frontend/src/pages/auth/LoginPage.tsx` to Croatian:
- page title
- subtitle/helper text
- username field label and placeholder
- password field label and placeholder
- submit button label
- missing-credentials inline validation message
- auth failure toast / fallback error text
2. Translate the admin-only setup-block toast text in login/setup bootstrap surfaces if it remains visible to the user in English.
3. Update `frontend/src/components/layout/SetupGuard.tsx` so the fatal-state title, message, and retry button are Croatian.
4. Update `frontend/src/utils/http.ts` so `CONNECTION_ERROR_MESSAGE` is Croatian.
5. Apply the Croatian fatal-state baseline to the targeted page sweep only:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx` only where auth/bootstrap/fatal-state connection copy is visible to the user
6. In `ReceivingPage.tsx`, if the local connection constant becomes equivalent to the shared Croatian baseline, remove the local duplicate and import from `frontend/src/utils/http.ts`.
7. Do not touch any other page copy beyond the scope above.
8. Append your work log to `handoff/phase-03-wave-02-croatian-first-localization/frontend.md` using the section shape required by `handoff/README.md`.

Verification
- Run at minimum:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Confirm by code-path review that:
- login visible copy is Croatian-first
- targeted fatal-state screens no longer show English `Connection error` / `Try again`
- shared `CONNECTION_ERROR_MESSAGE` is Croatian
- no unrelated page sweep was performed

Done Criteria
- The explicitly requested login/setup/fatal-state/auth-bootstrap strings are Croatian.
- The targeted pages converge on the shared Croatian connection-error baseline where appropriate.
- No unrelated UI copy, type names, enum values, or code identifiers were translated.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 2 Phase 3 of the STOQIO WMS project.

You are not alone in the codebase. The repo is currently dirty from the prior phase. Do not revert or overwrite unrelated edits made by other agents or the user. Your ownership is limited to backend test files plus `handoff/phase-03-wave-02-croatian-first-localization/testing.md`.

Owned test files
- relevant backend test files under `backend/tests/`
- `handoff/phase-03-wave-02-croatian-first-localization/testing.md`

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-033`, plus `F-029`/`F-031` for manual FE verification context)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-03-wave-02-croatian-first-localization/orchestrator.md`
- backend/frontend handoffs for this phase after those agents finish
- `backend/tests/test_i18n.py`
- `backend/tests/test_receiving.py`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`

Goal
- Add backend automated coverage for the missing localized order-line domain errors and document manual frontend verification for the Croatian-first login/setup/fatal-state cleanup.

Current Repo Reality
- Backend i18n coverage already exists in `backend/tests/test_i18n.py` for multiple localized error paths, so extending existing backend localization patterns is preferred over inventing a separate test style.
- `backend/tests/test_receiving.py` already exercises removed/closed order-line edge cases, but it does not yet lock Croatian localized message expectations for both `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED`.
- The current worktree already contains a frontend test harness from the prior phase, but this phase explicitly does not use or expand frontend automated tests.

Non-Negotiable Test Rules
- Add backend automated tests confirming `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` return a non-empty localized `message` for Croatian requests.
- Test at minimum with `Accept-Language: hr`.
- Do not create, add, or modify frontend automated tests in this phase.
- Frontend verification for this phase must be documented as manual steps in handoff notes.
- Do not change production code unless you discover and explicitly log a blocker that makes the delegated testing impossible.
- Keep your ownership on backend tests and documentation.

Tasks
1. Add backend tests confirming `ORDER_LINE_REMOVED` returns a Croatian localized `message` field when `Accept-Language: hr` is sent.
2. Add backend tests confirming `ORDER_LINE_CLOSED` returns a Croatian localized `message` field when `Accept-Language: hr` is sent.
3. Prefer extending existing backend localization or receiving/order tests rather than creating a sprawling new suite.
4. Document manual frontend verification steps in `handoff/phase-03-wave-02-croatian-first-localization/testing.md` for:
- login page visible Croatian copy
- login network/auth failure Croatian fallback
- `SetupGuard` Croatian fatal state when server is unavailable
- Croatian fatal states on Draft Entry, Approvals, Receiving, and Order Detail
- Croatian receiving toasts for removed and closed order-line errors
5. Run the relevant backend test command(s) and record exact results.

Verification
- Run the smallest relevant backend test slice that proves the new localization coverage.
- Record exact commands run and pass/fail counts.
- Do not add frontend automation for this phase.

Done Criteria
- Backend automated coverage exists for Croatian localized `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` responses.
- Manual frontend verification steps are clearly documented in handoff.
- No frontend automated test scope was added or expanded for this phase.
