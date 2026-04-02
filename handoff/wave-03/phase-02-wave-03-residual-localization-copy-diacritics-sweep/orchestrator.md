## Phase Summary

Phase
- Wave 3 - Phase 2 - Residual Localization / Copy / Diacritics Sweep

Objective
- Finish the residual localization cleanup in the app areas already known to contain English strings, mixed fallback copy, and missing Croatian diacritics.
- Preserve behavior exactly. This phase fixes user-visible copy consistency only.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-002`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1-4.6
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/18_UI_SETTINGS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/frontend.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/testing.md`

Current Repo Reality
- Wave 3 Phase 1 already established the runtime language/bootstrap foundation through `frontend/src/main.tsx`, `frontend/src/store/settingsStore.ts`, `frontend/src/i18n/index.ts`, and `frontend/src/utils/locale.ts`.
- The touched flows in this phase still contain specific user-visible English and/or no-diacritic strings in the current repo:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- English validation and fallback strings such as `Quantity must be greater than 0.`, `No batches available for this article.`, and multiple `Failed to ...` toasts remain.
- `frontend/src/pages/auth/SetupPage.tsx`
- success toast still says `Initial setup completed successfully.`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- both success toasts still say `Receipt recorded.`
- multiple user-visible strings still use English or mixed copy such as `Confirm Receipt`, `Batch code`, `Expiry date`
- multiple validation strings still miss diacritics, for example `Kolicina je obavezna.` and `Kolicina mora biti veca od 0.`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- several fallback/error strings still miss diacritics, for example `Ucitavanje detalja drafta nije uspjelo.`, `Kolicina mora biti veca od nule.`, and `Azuriranje kolicine nije uspjelo.`
- Shared connection/fatal-state baseline for these flows is already Croatian-first via `frontend/src/utils/http.ts` and/or local Croatian copy. This phase must not regress those surfaces back to English.
- Existing Phase 1 i18n keys currently cover shell/sidebar/bootstrap runtime chrome, not the full touched feature pages. Reuse those keys where directly applicable, but do not broaden this phase into a repo-wide translation sweep.
- Backend already has a centralized localized API-error path in `backend/app/utils/i18n.py` and `backend/app/utils/errors.py`, including existing coverage for `ORDER_LINE_REMOVED`, `ORDER_LINE_CLOSED`, `BATCH_EXPIRY_MISMATCH`, `RECEIVING_ADHOC_NOTE_REQUIRED`, and generic validation patterns. Backend scope here should stay narrowly targeted to directly relevant missing catalog entries only if audit proves they still surface as raw English in these flows.

Contract Locks / Clarifications
- This is a cleanup phase only. Do not change API contracts, route behavior, validation rules, save flows, success/error branching, or page logic.
- Fix user-visible copy consistency only.
- Keep machine-readable API `error` codes, enum values, response field names, TypeScript types, variable names, and internal identifiers unchanged and English.
- Do not broaden this into a repo-wide frontend translation pass or a repo-wide backend i18n sweep.
- Where the app already has existing Phase 1 i18n keys or shared Croatian-first copy for the same surface, reuse that path instead of creating a second hardcoded variant.
- Frontend may fix directly hardcoded page copy in the touched flows when no existing i18n/shared key exists and introducing a large new translation surface would broaden scope.
- Backend success responses are out of scope. Only patch missing localized backend error-message entries if a directly touched flow still relies on a raw English backend fallback message.
- Croatian diacritics must be correct on all touched user-visible strings changed in this phase.

Delegation Plan
- Frontend:
- sweep the targeted files and any directly used shared component for user-visible English / mixed / no-diacritic strings, fixing only copy consistency while preserving behavior
- Backend:
- audit directly related backend error localization for the touched flows and patch only narrowly missing catalog coverage if proven necessary
- Testing:
- add the smallest practical frontend regression coverage for the concrete copy fixes and document manual verification for each touched flow

Acceptance Criteria
- The previously identified English strings are gone from the touched flows.
- The previously identified no-diacritic strings are corrected in the touched flows.
- Any additional user-visible English / mixed / no-diacritic strings discovered in the specifically targeted files are also fixed.
- The touched flows still behave exactly the same functionally.
- No backend/API identifiers, error-code names, enum values, TypeScript types, or internal identifiers were translated accidentally.
- The phase leaves a complete orchestration, frontend, backend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Frontend and Backend in parallel. Testing should follow after those deliveries are available.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 3 Phase 2 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-002`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1-4.6
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/18_UI_SETTINGS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/frontend.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/orchestrator.md`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- any directly used shared component you touch, especially:
- `frontend/src/components/layout/SetupGuard.tsx`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/utils/http.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/i18n/locales/hr.json`
- `frontend/src/i18n/locales/en.json`

Goal
- Finish the residual localization cleanup in the currently identified flows by removing user-visible English strings, mixed fallback copy, and missing Croatian diacritics, without changing behavior.

Non-Negotiable Contract Rules
- This phase is copy cleanup only. Do not change functional behavior.
- Do not change API calls, route logic, payload shapes, validation conditions, success/error branching, or data flow.
- Keep backend/API error-code names, enum values, TypeScript types, variable names, and internal identifiers unchanged.
- Fix only user-visible copy in the targeted flows and any directly touched shared component used by those flows.
- Reuse existing Phase 1 i18n keys or shared Croatian-first copy where they already exist for the same surface.
- Do not broaden this into a repo-wide localization pass.
- If a touched string is a frontend fallback shown when `apiError.message` is absent, fix only the fallback text; keep backend-message pass-through behavior intact.

Minimum Mandatory Fixes
1. In `frontend/src/pages/drafts/DraftEntryPage.tsx`, fix:
- `Quantity must be greater than 0.`
2. In `frontend/src/pages/auth/SetupPage.tsx`, fix:
- `Initial setup completed successfully.`
3. In `frontend/src/pages/receiving/ReceivingPage.tsx`, fix:
- both `Receipt recorded.` success toasts
4. In `frontend/src/pages/approvals/components/DraftGroupCard.tsx`, fix:
- `Ucitavanje...`
- `Kolicina...`
- `Azuriranje...`
5. Fix any identified no-diacritic Receiving validation strings such as:
- `Kolicina je obavezna.`
- `Kolicina mora biti veca od 0.`

Required Sweep
1. Audit these files for any additional user-visible English / mixed / no-diacritic strings and fix them:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- any shared component used directly by those flows
2. Current repo reality strongly suggests you should also review and fix, if still user-visible:
- Draft Entry English fallbacks such as:
- `No batches available for this article.`
- `Failed to add entry. Please try again.`
- `Failed to update draft note.`
- `Failed to update entry.`
- `Failed to delete entry.`
- Receiving labels/buttons/table headings such as:
- `Confirm Receipt`
- `Batch code`
- `Expiry date`
- Setup/SetupGuard shared flow copy if you touch those surfaces and find mixed or duplicate wording
- Approvals fallback/warning strings that still miss Croatian diacritics
3. Where the app now has existing Phase 1 i18n keys from the runtime-language work, use them instead of adding fresh hardcoded strings for the same shared surface.
4. For page-specific strings in these targeted flows where no existing i18n/shared key exists, use Croatian-first copy consistent with the UI specs and current repo conventions.
5. Keep the change set coherent and minimal. Do not expand into unrelated pages just because they also have localization debt.

Verification
- Run at minimum:
- `cd frontend && CI=true npm run test`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Also run a focused repo search proving the known strings are gone, for example over the touched files for:
- `Receipt recorded`
- `Initial setup completed successfully`
- `Quantity must be greater than 0`
- `Ucitavanje`
- `Kolicina`
- `Azuriranje`
- `Confirm Receipt`
- `Batch code`
- `Expiry date`

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, assumptions, and which strings/surfaces were intentionally fixed in this phase.
- If you discover a touched backend-driven message that still requires backend catalog work, log it clearly instead of silently working around it with a misleading frontend-only translation.

Done Criteria
- The known English strings in the touched flows are gone.
- The known no-diacritic strings in the touched flows are corrected.
- Any additional user-visible English / mixed / no-diacritic strings found in the targeted sweep are fixed.
- Functional behavior remains unchanged.
- Verification is recorded in handoff.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 2 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-002`)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/11_UI_RECEIVING.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/orchestrator.md`
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/services/receiving_service.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/api/setup/routes.py`
- any directly relevant test file you touch

Goal
- Audit whether the touched Draft Entry, Setup, Receiving, and Approvals flows still rely on raw English backend fallback messages where a localized catalog entry should exist, and patch only directly relevant missing backend i18n coverage if needed.

Current Repo Reality You Must Respect
- The backend already has a centralized localized API-error path.
- Existing catalog coverage already includes:
- `ORDER_LINE_REMOVED`
- `ORDER_LINE_CLOSED`
- `BATCH_EXPIRY_MISMATCH`
- `RECEIVING_ADHOC_NOTE_REQUIRED`
- generic validation templates for required / integer / number / >0 / >=0 / ISO date / query-param rules
- This means backend work may legitimately be zero or near-zero if the touched flows already localize correctly through the existing pattern.

Non-Negotiable Contract Rules
- Do not do a repo-wide backend i18n sweep in this phase.
- Do not change route behavior, payload shapes, error-code names, status codes, or auth/RBAC behavior.
- Patch only missing catalog entries or translation-template wiring directly relevant to the touched Draft Entry / Setup / Receiving / Approvals flows.
- Keep machine-readable `error` codes, enum values, and field names unchanged and English.
- If no backend change is actually needed after audit, record that explicitly in handoff instead of inventing unnecessary work.

Tasks
1. Audit the backend messages directly surfaced by the touched flows:
- Draft Entry
- Setup
- Receiving
- Approvals
2. Check whether any directly user-visible backend message in those flows still falls back to raw English when it should localize through the existing i18n layer.
3. Pay special attention to directly relevant receiving/approval/draft validation or service messages that may bypass the current template layer.
4. If you find a clearly user-facing missing entry or missing template mapping, add the smallest targeted fix in the existing backend i18n pattern.
5. Add or update targeted backend tests only if backend changes are required.
6. Do not broaden into unrelated modules or a general cleanup of the full backend message catalog.

Verification
- If backend changes are required, run the smallest relevant targeted backend test slice you changed, at minimum including the impacted i18n/service coverage.
- If no backend code changes are required, still run at least one directly relevant targeted verification slice and record why the current backend contract was already sufficient.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and whether the backend catalog already covered the touched flows or required a targeted patch.
- If you discover a new cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- Any genuinely missing backend-localized entries directly affecting the touched flows are patched.
- Or, if no patch is needed, the audit clearly documents that the current backend i18n layer already covers those touched flows.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 2 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-002`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- any touched shared component or frontend test file you extend

Goal
- Lock focused regression coverage for the concrete copy fixes in this phase where practical, and record a clear manual verification path for each touched flow.

Non-Negotiable Test Rules
- Focus only on the concrete strings and touched flows from this phase.
- Do not build a sprawling new integration harness for unrelated localization debt.
- Prefer the smallest stable assertions that prove the specific copy regression is fixed.
- Do not change application behavior just to make tests easier.

Tasks
1. Add or update frontend tests for the concrete strings fixed in this phase where practical.
2. Prefer small, stable coverage such as:
- validation/helper output assertions
- rendered button/label/fallback text in the touched components
- targeted component tests over broad snapshot churn
3. Document manual verification for each touched flow:
- Draft line edit validation
- Setup success toast
- Linked receipt success toast
- Ad-hoc receipt success toast
- Approvals draft detail fetch / quantity edit errors
4. Confirm Croatian diacritics render correctly in the touched screens.
5. If backend changes were made for this phase, run the relevant targeted backend verification or record the backend agent's verification result in your handoff.

Verification
- Run at minimum:
- `cd frontend && CI=true npm run test`
- If you add or rely on any backend coverage for this phase, run the smallest relevant backend test slice too.
- By code and manual verification notes, confirm:
- the previously identified English strings are gone from the touched flows
- the previously identified no-diacritic strings are fixed
- the touched flows still behave exactly the same functionally
- no internal/API identifiers were translated accidentally

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, manual verification steps, open issues, and any residual risk.

Done Criteria
- Practical regression coverage exists for the concrete copy fixes made in this phase.
- Manual verification is documented for each touched flow named above.
- Croatian diacritics are explicitly confirmed on the touched screens.
- Verification is recorded in handoff.

## [2026-04-02 22:31 CET] Orchestrator Review - Phase Not Accepted Yet

Status
- changes requested

Scope
- Reviewed the delivered frontend, backend, and testing work for Wave 3 Phase 2.
- Compared agent handoffs against the actual modified code.
- Re-ran the requested verification matrix for the touched frontend/backend scope.

Docs Read
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/frontend.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/backend.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/testing.md`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`
- `backend/app/utils/i18n.py`
- `backend/tests/test_i18n.py`

Commands Run
```bash
git status --short
git diff -- backend/app/utils/i18n.py backend/tests/test_i18n.py frontend/src/pages/approvals/components/DraftGroupCard.tsx frontend/src/pages/auth/SetupPage.tsx frontend/src/pages/drafts/DraftEntryPage.tsx frontend/src/pages/receiving/ReceivingPage.tsx frontend/src/pages/__tests__/localized-copy-smoke.test.tsx
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest tests/test_i18n.py tests/test_drafts.py -q
rg -n '>(Batch|Confirm Receipt|Expiry date|Initial setup completed successfully|Receipt recorded|Quantity must be greater than 0|No batches available|Article not found|Failed to)|"(Batch|Confirm Receipt|Expiry date|Initial setup completed successfully|Receipt recorded|Quantity must be greater than 0|No batches available|Article not found|Failed to)[^"]*"' frontend/src/pages/drafts/DraftEntryPage.tsx frontend/src/pages/auth/SetupPage.tsx frontend/src/pages/receiving/ReceivingPage.tsx frontend/src/pages/approvals/components/DraftGroupCard.tsx
```

Findings
- Blocking:
- The newly added frontend regression test file does not satisfy the repo lint/build baseline, so the phase currently fails the required verification matrix. `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx` contains an unused `SetupPage` import and multiple `any` usages that trip ESLint, and TypeScript build also fails on the unused import. Evidence:
- [localized-copy-smoke.test.tsx:5](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/__tests__/localized-copy-smoke.test.tsx#L5)
- [localized-copy-smoke.test.tsx:14](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/__tests__/localized-copy-smoke.test.tsx#L14)
- [localized-copy-smoke.test.tsx:75](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/__tests__/localized-copy-smoke.test.tsx#L75)
- [localized-copy-smoke.test.tsx:83](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/__tests__/localized-copy-smoke.test.tsx#L83)
- `cd frontend && npm run lint -- --max-warnings=0` failed with 7 errors, and `cd frontend && npm run build` failed with `TS6133: 'SetupPage' is declared but its value is never read.`
- Medium:
- The required frontend sweep is still incomplete because Receiving history still shows an English table heading, `Batch`, inside the targeted file. This means the phase acceptance criterion “additional user-visible English strings discovered in the specifically targeted files are also fixed” is not yet met. Evidence:
- [ReceivingPage.tsx:1376](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/receiving/ReceivingPage.tsx#L1376)

Validation Result
- Passed:
- `cd frontend && CI=true npm run test` -> `9 passed / 35 passed`
- `cd backend && venv/bin/python -m pytest tests/test_i18n.py tests/test_drafts.py -q` -> `90 passed`
- Backend targeted i18n patch for `INVALID_STATUS` is correct and verified.
- Failed:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Closeout Decision
- Wave 3 Phase 2 is not accepted yet.

Next Action
- Frontend/testing follow-up is required before acceptance:
- fix the lint/build-breaking issues in `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`
- complete the targeted Receiving sweep by replacing the remaining English `Batch` history heading
- rerun `CI=true npm run test`, `npm run lint -- --max-warnings=0`, and `npm run build`

## [2026-04-02 22:31 CEST] Orchestrator Direct Fix + Final Validation

Status
- accepted

Scope
- Applied the remaining acceptance fixes directly as orchestrator after the review findings above.
- This note is the source of truth for future agents: the final Phase 2 closeout changes below were implemented by the orchestrator, not by the originally delegated frontend/testing agents.

Files Changed By Orchestrator
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`

Direct Fixes Applied
- Replaced the last remaining English Receiving history table heading, `Batch`, with the Croatian label `Šarža`.
- Removed the unused `SetupPage` import from the localized smoke test.
- Replaced `any`-based smoke-test typing with concrete API response types and typed `vi.importActual(...)` usage so the repo baseline passes without weakening lint/type rules.

Commands Run
```bash
cd frontend && npx eslint src/pages/__tests__/localized-copy-smoke.test.tsx
rg -n "<Table.Th>Šarža</Table.Th>|<Table.Th>Batch</Table.Th>" frontend/src/pages/receiving/ReceivingPage.tsx
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest tests/test_i18n.py tests/test_drafts.py -q
```

Validation Result
- Passed:
- `cd frontend && CI=true npm run test` -> `9 passed / 35 passed`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- `cd backend && venv/bin/python -m pytest tests/test_i18n.py tests/test_drafts.py -q` -> `90 passed`
- The previously identified English `Batch` heading is gone from the touched Receiving flow.
- The localized smoke test now satisfies ESLint and TypeScript build rules.
- Functional behavior for the touched flows remains unchanged; only copy consistency and test typing hygiene were adjusted.
- No internal/API identifiers were translated in this follow-up.

Closeout Decision
- Wave 3 Phase 2 is accepted and closed.
