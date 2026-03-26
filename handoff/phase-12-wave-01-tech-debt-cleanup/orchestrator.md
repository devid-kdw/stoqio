## Phase Summary

Phase
- Wave 1 - Phase 12 - Tech Debt Cleanup

Objective
- Resolve three V1 testing-phase tech debt items without broadening into new feature work:
- centralize the shared frontend integer-UOM list
- make API error `message` strings localized to the active UI language
- remove ambiguity around the intentionally unused `backend/app/api/warehouse/` namespace folder

Source Docs
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`, plus relevant prior language/UI decisions)
- `frontend/src/api/client.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `backend/app/api/`
- `backend/app/services/`

Current Repo Reality
- The integer-UOM literal is not duplicated in only three places anymore. Matching frontend lists currently exist in:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- Frontend currently does not send the active UI language to the backend on API requests. `frontend/src/i18n/index.ts` initializes `hr` by default, and `frontend/src/store/settingsStore.ts` later updates the active language from Settings `default_language`.
- Backend API error payloads are assembled per-module through repeated `_error(...)` helpers in route files, but most human-readable business-error strings are created deeper in service-layer exceptions, not directly in the routes.
- `backend/app/api/warehouse/` currently contains only an empty `__init__.py`. Warehouse article functionality is served through the `/api/v1/articles` namespace, and no `warehouse` blueprint is registered.

Contract Locks / Clarifications
- This is a wave-specific follow-up under `phase-12-wave-01-*`. Do not mix it with the historical `phase-12-inventory-count` implementation scope.
- Tech debt #1 is locked as true centralization:
- use one shared frontend source of truth for the integer-UOM codes
- replace all current duplicate literals that represent the same concept, not only the three files named in the original feedback summary
- do not change quantity-display behaviour while deduplicating the source data
- The shared integer-UOM source should be `frontend/src/utils/uom.ts` and should export the requested constant:
- `export const INTEGER_UOMS: string[] = ["kom", "pak", "pár"];`
- Tech debt #2 is locked by `DEC-I18N-001`:
- API `message` strings must be localized to the active UI language, not fixed English and not fixed Croatian
- supported languages for this wave are `hr`, `en`, `de`, `hu`
- frontend must send the active language via `Accept-Language` on every API request
- backend localizes only the human-readable `message` field
- keep API response structure unchanged: `{ "error": "...", "message": "...", "details": {} }`
- keep machine-readable `error` codes, enum values, and field names in English
- fallback order for missing/unsupported language is:
- request `Accept-Language` primary tag when supported
- otherwise configured Settings `default_language` when available and supported
- otherwise `hr`
- Because current repo reality stores many error strings in the service layer, backend work must cover both route-local validation messages and service-generated API error messages. Do not limit the review to route files only.
- Prefer centralized backend localization infrastructure over ad hoc per-route replacements. This wave should not leave a new mix of translated and untranslated API error paths.
- Tech debt #3 is locked to the README option, not folder deletion:
- keep `backend/app/api/warehouse/` for structural consistency
- add `backend/app/api/warehouse/README.md` with the exact explanation requested by the user
- do not introduce a new warehouse blueprint or routing alias in this wave

Delegation Plan
- Backend:
- Implement locale-aware backend API error messages for supported UI languages and add the Warehouse-folder README clarification. Because there is no separate testing delegation in this wave, backend also owns targeted regression coverage and backend-suite verification for the localization change.
- Frontend:
- Create the shared integer-UOM constant, replace all current duplicate literals with imports from it, and send the active i18n language to the backend on every API request via `Accept-Language`.
- Testing:
- None. Verification is owned by the backend and frontend agents in their respective scopes.

Acceptance Criteria
- `frontend/src/utils/uom.ts` exists and is the single source of truth for the integer-UOM codes.
- The duplicated `["kom", "pak", "pár"]` frontend literals used for integer-UOM behaviour are removed in favour of the shared source.
- Draft Entry, Approvals, and Receiving quantity display/step/scale behaviour remains unchanged after the refactor.
- Frontend API requests include the active UI language in `Accept-Language`.
- Backend API error payloads keep the same structure and status codes, but `message` is localized for supported languages.
- At minimum, one `404` path and one `409` path return Croatian messages when `Accept-Language: hr`, and a non-HR supported language returns that language's message on the same error paths.
- `backend/app/api/warehouse/README.md` exists with the requested explanation, and the folder is no longer ambiguous.
- The phase leaves a complete orchestration, backend, and frontend handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent and Frontend Agent in parallel using the locked `Accept-Language` contract from this handoff.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 12 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001` and prior language-related decisions)
- `handoff/phase-12-wave-01-tech-debt-cleanup/orchestrator.md`
- `backend/app/api/`
- `backend/app/services/`
- `backend/tests/`

Goal
- Resolve the backend side of this wave's tech debt by making API error `message` strings locale-aware and by documenting the intentionally unused `backend/app/api/warehouse/` namespace folder.

Non-Negotiable Contract Rules
- Keep API error payload shape unchanged:
- `{ "error": "...", "message": "...", "details": {} }`
- Keep status codes unchanged.
- Keep machine-readable `error` codes in English and stable.
- Only the human-readable `message` field becomes localized in this wave.
- Supported languages are:
- `hr`
- `en`
- `de`
- `hu`
- Locale resolution contract for this wave:
- primary source: request `Accept-Language`
- interpret the primary supported tag (`hr`, `en`, `de`, `hu`) from the header
- if missing or unsupported, fall back to configured Settings `default_language` when available and supported
- otherwise fall back to `hr`
- Current repo reality matters:
- many user-facing error messages are created in service-layer exceptions, not only in route files
- do not restrict the audit to `routes.py` files only
- Prefer a centralized localization path for API errors:
- add shared backend infrastructure for resolving translated error messages
- avoid one-off manual replacements in scattered route handlers unless truly unavoidable
- Do not change success payloads, enum serialization, field names, or route namespaces in this wave.
- For `backend/app/api/warehouse/`, choose the README path only:
- keep the folder/package
- add `backend/app/api/warehouse/README.md`
- use the exact text:
- `This folder is intentionally empty. Warehouse article data is served through /api/v1/articles. This folder is retained for structural consistency.`
- Do not delete the folder in this wave.

Tasks
1. Add centralized backend support for locale-aware API error-message resolution.
2. Apply that localization path to current API error responses produced through the existing route/service error flow.
3. Audit the backend for user-facing API error messages that are still hardcoded to a single language and move them onto the localized path.
4. Keep the existing API `error` code and `details` behaviour intact while localizing `message`.
5. Add `backend/app/api/warehouse/README.md` with the exact explanatory text above.
6. Add or update targeted backend regression coverage for at minimum:
- one `404` error path localized by `Accept-Language`
- one `409` error path localized by `Accept-Language`
- fallback behaviour for missing or unsupported language
7. If existing backend tests assert exact old message text, update only the assertions affected by this wave; do not broaden unrelated test expectations.
8. If you discover a blocker in the current service-error structure that prevents reliable localization for some dynamic messages, log it immediately in handoff and add the smallest backend refactor needed to make the localization deterministic.

Suggested Implementation Direction
- Use stable translation keys derived from existing API `error` codes and structured `details` where possible.
- For dynamic messages (for example messages that include a field name, batch code, quantity, or article description), prefer template-based localization with placeholders from structured data instead of trying to post-process arbitrary already-formatted English strings.
- Keep route modules thin; shared localization logic belongs in a backend utility/helper layer.

Verification
- Run at minimum:
- `backend/venv/bin/pytest backend/tests -q`
- Also run any smaller targeted test subset you add for localized error coverage and record it.
- Manually or programmatically verify at minimum:
- the same `404` endpoint path returns Croatian when `Accept-Language: hr`
- the same `404` endpoint path returns a non-HR supported language when requested
- one `409` endpoint path also follows the selected language
- missing or unsupported language falls back deterministically according to the locked contract

Handoff Requirements
- Append your work log to `handoff/phase-12-wave-01-tech-debt-cleanup/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, sample localized verification paths used, open issues, and assumptions.
- If you need a cross-agent contract clarification beyond `DEC-I18N-001`, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- API error `message` strings are localized for supported request languages.
- Status codes, `error` codes, and payload structure remain unchanged.
- Warehouse folder ambiguity is resolved via README.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 12 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/phase-12-wave-01-tech-debt-cleanup/orchestrator.md`
- `frontend/src/api/client.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/warehouse/warehouseUtils.ts`

Goal
- Resolve the frontend side of this wave's tech debt by centralizing the integer-UOM list and sending the active UI language to the backend on every API request.

Non-Negotiable Contract Rules
- Create `frontend/src/utils/uom.ts`.
- Export the requested shared constant:
- `export const INTEGER_UOMS: string[] = ["kom", "pak", "pár"];`
- Treat this as the single source of truth for integer-UOM behaviour in the frontend.
- Current repo reality includes more than the three originally named duplicates. Replace all current duplicate literals that represent the same integer-UOM concept, including the existing `FALLBACK_INTEGER_UOMS` variants, with imports from the shared source.
- Do not change quantity formatting behaviour while deduplicating the data source.
- At minimum, preserve existing behaviour on:
- Draft Entry
- Approvals
- Receiving
- Keep the rest of the touched modules behaviourally unchanged as well:
- Orders
- Employees
- Reports
- Warehouse utils
- Add the active UI language to every API request via `Accept-Language`.
- Use the currently active frontend i18n language, not a hardcoded value.
- Normalize to the supported app languages (`hr`, `en`, `de`, `hu`) before sending if needed.
- Do not change route paths, payload shapes, auth behaviour, or 401 refresh semantics while updating the API client header logic.

Tasks
1. Create `frontend/src/utils/uom.ts` with the shared `INTEGER_UOMS` constant.
2. Replace the current duplicate integer-UOM literals/import patterns across the frontend with that shared source.
3. Update `frontend/src/api/client.ts` so each request sends the active UI language in `Accept-Language`.
4. Use current repo reality for language selection:
- read from the active i18n instance used by the app
- ensure requests after Settings language changes also send the updated language automatically
5. Keep formatting/step/decimal-scale behaviour unchanged on the affected pages and helpers.
6. Do not broaden this into a larger frontend i18n refactor or a user-facing language-picker feature.

Verification
- Run at minimum:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Verify via code/search and targeted reasoning that:
- the duplicated literal integer-UOM list no longer exists outside the shared util
- Draft Entry, Approvals, and Receiving still use the same integer-vs-decimal behaviour
- API requests now attach `Accept-Language` from the active i18n language

Handoff Requirements
- Append your work log to `handoff/phase-12-wave-01-tech-debt-cleanup/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, verification performed, open issues, and assumptions.
- If you discover the backend needs a different language-header contract than this handoff states, log it immediately instead of inventing a new one silently.

Done Criteria
- The frontend integer-UOM list is centralized to one shared source.
- Current duplicate literals are removed in favour of that shared source.
- API requests carry the active UI language in `Accept-Language`.
- Verification is recorded in handoff.

## [2026-03-26 17:24] Orchestrator Validation - Wave 1 Phase 12 Tech Debt Cleanup

Status
- changes_requested

Scope
- Reviewed the delivered backend and frontend work for the Phase 12 Wave 1 tech-debt cleanup.
- Re-ran backend and frontend verification, then performed additional targeted API checks against the new localization layer.
- Compared the delivered behaviour against the locked `DEC-I18N-001` contract and the phase acceptance criteria.

Docs Read
- `handoff/phase-12-wave-01-tech-debt-cleanup/orchestrator.md`
- `handoff/phase-12-wave-01-tech-debt-cleanup/backend.md`
- `handoff/phase-12-wave-01-tech-debt-cleanup/frontend.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)

Files Reviewed
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/tests/test_i18n.py`
- `frontend/src/api/client.ts`
- `frontend/src/utils/uom.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/employees/EmployeeDetailPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `backend/app/api/warehouse/README.md`

Commands Run
```bash
git status --short
sed -n '1,260p' handoff/phase-12-wave-01-tech-debt-cleanup/backend.md
sed -n '1,260p' handoff/phase-12-wave-01-tech-debt-cleanup/frontend.md
git diff -- backend/app/utils/i18n.py backend/app/utils/errors.py backend/app/api/approvals/routes.py backend/app/api/articles/routes.py backend/app/api/auth/routes.py backend/app/api/drafts/routes.py backend/app/api/employees/routes.py backend/app/api/inventory_count/routes.py backend/app/api/orders/routes.py backend/app/api/receiving/routes.py backend/app/api/reports/routes.py backend/app/api/settings/routes.py backend/app/api/setup/routes.py backend/app/services/article_service.py backend/app/services/order_service.py backend/app/services/receiving_service.py backend/app/services/settings_service.py backend/app/api/warehouse/README.md backend/tests/test_i18n.py frontend/src/api/client.ts frontend/src/utils/uom.ts frontend/src/pages/drafts/DraftEntryPage.tsx frontend/src/pages/approvals/components/DraftGroupCard.tsx frontend/src/pages/receiving/ReceivingPage.tsx frontend/src/pages/orders/orderUtils.ts frontend/src/pages/employees/EmployeeDetailPage.tsx frontend/src/pages/reports/reportsUtils.ts frontend/src/pages/warehouse/warehouseUtils.ts
backend/venv/bin/pytest backend/tests/test_i18n.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
venv/bin/python - <<'PY'
# targeted review probe from backend/:
# 1) GET /api/v1/orders?page=abc with Accept-Language: en
# 2) GET /api/v1/auth/me with Accept-Language: hr after deactivating the token user
PY
venv/bin/python - <<'PY'
# targeted review probe from backend/:
# GET /api/v1/orders with a VIEWER token + Accept-Language: hr
PY
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_i18n.py -q` -> `11 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `334 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- Targeted review probes reproduced two remaining backend contract gaps despite the green suite.

Accepted Work
- Frontend integer-UOM centralization is correctly applied:
- `frontend/src/utils/uom.ts` is now the single literal source
- the previously duplicated `["kom", "pak", "pár"]` list no longer appears outside that shared util
- the affected Draft Entry / Approvals / Receiving / Orders / Employees / Reports / Warehouse helpers all now import the shared source
- Frontend request wiring now sends `Accept-Language` from the active i18n language in `frontend/src/api/client.ts`.
- Backend added a shared localization path through `backend/app/utils/i18n.py` and `backend/app/utils/errors.py`.
- `backend/app/api/warehouse/README.md` was added with the required clarification text.

Blocking Findings
- Backend localization is incomplete on auth/RBAC error paths. `backend/app/utils/auth.py` still returns hardcoded English `UNAUTHORIZED` and `FORBIDDEN` payloads, and `backend/app/api/auth/routes.py` still hardcodes the inactive-user `UNAUTHORIZED` response on `/auth/refresh` and `/auth/me` instead of using the shared localized error helper. Review probes confirmed `Accept-Language: hr` still returns English on those paths.
- The new localization layer regresses many detailed validation messages into a generic message. In `backend/app/utils/i18n.py`, any unkeyed `VALIDATION_ERROR` now resolves to the generic catalog entry (`"Validation error."` / localized equivalent) instead of preserving the specific fallback text. Review probe: `GET /api/v1/orders?page=abc` with `Accept-Language: en` returned `{"message": "Validation error."}` rather than a field-specific message like `"page must be a valid integer."` translated to the requested language. This affects many route/service parsers that still emit specific validation text without `_msg_key`.

Closeout Decision
- Frontend portion is acceptable.
- Backend portion is not yet acceptable.
- Phase 12 Wave 1 is not formally closed.

Next Action
- Send the backend portion back for remediation of:
- all remaining auth/RBAC error paths that bypass the shared localization helper
- the generic `VALIDATION_ERROR` fallback regression so field-specific validation guidance remains specific after localization
- After that remediation, rerun the same verification set and reassess closeout.

## [2026-03-26 17:40] Orchestrator Remediation + Final Validation - Wave 1 Phase 12 Tech Debt Cleanup

Status
- accepted

Scope
- Implemented the remaining backend remediation directly as orchestrator after the prior validation findings.
- Re-ran the full backend suite, frontend lint/build gates, and the same targeted manual probes that previously reproduced the bugs.
- Reassessed the phase against the locked acceptance criteria after the remediation landed.

Files Changed By Orchestrator
- `backend/app/utils/i18n.py`
- `backend/app/utils/auth.py`
- `backend/app/api/auth/routes.py`
- `backend/tests/test_i18n.py`
- `handoff/phase-12-wave-01-tech-debt-cleanup/orchestrator.md`

What Changed
- Closed the remaining auth/RBAC localization gap:
- `backend/app/utils/auth.py` now routes `UNAUTHORIZED` and `FORBIDDEN` responses through the shared localized error helper instead of returning hardcoded English payloads
- `backend/app/api/auth/routes.py` now routes the inactive-user `UNAUTHORIZED` responses on `/auth/me` and `/auth/refresh` through the same localized helper
- Removed the `VALIDATION_ERROR` specificity regression:
- `backend/app/utils/i18n.py` now preserves detailed validation fallback text instead of collapsing all unkeyed `VALIDATION_ERROR` cases to the generic catalog message
- common validation patterns such as required / integer / number / >0 / >=0 / ISO date / `'true'|'false'` / `one of:` / required query param are now localized while staying field-specific
- Expanded localization regression coverage in `backend/tests/test_i18n.py`:
- explicit forbidden-path localization coverage
- explicit unauthorized helper localization coverage
- explicit field-specific validation-message coverage for `GET /api/v1/orders?page=abc` in both English and Croatian

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_i18n.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
venv/bin/python - <<'PY'
# targeted review probe from backend/:
# 1) GET /api/v1/orders?page=abc with Accept-Language: en
# 2) GET /api/v1/orders with a VIEWER token + Accept-Language: hr
# 3) GET /api/v1/auth/me with an inactive token user + Accept-Language: hr
PY
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_i18n.py -q` -> `15 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `338 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- Targeted manual probes now return the expected localized messages:
- `GET /api/v1/orders?page=abc` with `Accept-Language: en` -> `page must be a valid integer.`
- `GET /api/v1/orders` as `VIEWER` with `Accept-Language: hr` -> `Nema ovlasti za pristup ovom resursu.`
- `GET /api/v1/auth/me` with inactive token user and `Accept-Language: hr` -> `Korisnik nije pronađen ili je račun neaktivan.`

Closeout Decision
- The prior blocking findings are resolved.
- Backend and frontend portions are both accepted.
- Phase 12 Wave 1 is formally closed.

Next Action
- Proceed to the next Wave 1 phase using this remediated Phase 12 baseline.
