## Phase Summary

Phase
- Wave 3 - Phase 1 - Runtime Language Switching + Locale Foundation

Objective
- Fix the broken Settings language-switch behavior so a saved `default_language` has an immediate visible effect in the current authenticated session and remains active across route transitions and authenticated reload/bootstrap.
- Establish the shared frontend i18n and locale-formatting foundation needed for later Wave 3 localization cleanup without broadening this phase into a full repo-wide translation pass.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-001`)
- `stoqio_docs/18_UI_SETTINGS.md` § 1-3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1, § 4.4, § 4.7
- `stoqio_docs/07_ARCHITECTURE.md` § 3-4
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-02/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`
- `frontend/src/i18n/index.ts`
- `frontend/src/main.tsx`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/settings.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`

Current Repo Reality
- `frontend/src/i18n/index.ts` still initializes i18n with `lng: 'hr'`, `fallbackLng: 'en'`, and all four locale JSON files are effectively empty.
- `frontend/src/store/settingsStore.ts` already calls `i18n.changeLanguage(...)` after `GET /settings/shell` and after `PUT /settings/general`, but that only affects surfaces already using translation keys.
- `frontend/src/main.tsx` bootstraps auth before render, but it does not preload shell settings or language before the first authenticated shell render path begins.
- `AppShell.tsx`, `Sidebar.tsx`, the bootstrap loading state in `main.tsx`, and other shared UI surfaces still contain hardcoded Croatian copy.
- Reusable/page utilities across Warehouse, Orders, Reports, Identifier, Employees, Receiving, Inventory, Approvals, and Settings still hardcode `hr-HR` date/number formatting.
- Backend settings persistence already appears to use `SystemConfig.default_language` through `settings_service.get_general_settings()`, `get_shell_settings()`, and `update_general_settings()`, but this phase still requires a serializer/route audit so stale language values cannot leak through any Settings payload.

Contract Locks / Clarifications
- The persisted source of truth for the installation language remains `SystemConfig.default_language`. Do not introduce a user-specific language preference or replace backend persistence with browser-only storage.
- This phase is about runtime language switching and shared locale infrastructure, not a full translation of every domain string in every page.
- Any shared or shell-level UI surface touched for runtime correctness must move to i18n-driven copy instead of adding more hardcoded strings.
- Locale file rules for this phase are locked as follows:
- `hr.json` must be complete for every key used anywhere in the app after this phase's changes.
- `en.json` must be complete for the same key set used by the shared runtime foundation touched in this phase.
- `de.json` and `hu.json` must exist as valid JSON, but they do not need translated keys in this phase. Croatian fallback is preferred over guessed translations.
- Do not rename enum values, API error codes, response field names, internal identifiers, or existing timezone/quantity-precision semantics.
- Locale-aware formatting may change only the locale used for rendering. It must not change which values are shown, which timezone is applied, or how quantity precision decisions are made.
- Keep the existing `Accept-Language` request-header contract from `DEC-I18N-001`. If the frontend fallback chain needs small alignment for runtime correctness, do it without changing backend error-code semantics.
- Do not broaden backend scope into the later Wave 3 `/settings/shell` auth-consistency hardening item (`W3-003`) unless you discover it directly blocks this phase.

Delegation Plan
- Backend:
- audit Settings payloads and persistence to guarantee canonical `default_language` round-trips with no stale serializer path
- Frontend:
- make runtime language selection follow persisted shell/general settings, introduce the shared translation/formatting foundation, and migrate the authenticated UI chrome needed for visible switching
- Testing:
- lock frontend language-lifecycle and locale-formatting coverage, and record manual cross-page verification steps

Acceptance Criteria
- `GET /api/v1/settings/general` returns the canonical persisted `default_language`.
- `GET /api/v1/settings/shell` returns the same canonical persisted `default_language`.
- `PUT /api/v1/settings/general` returns the updated canonical `default_language` immediately after persistence.
- Saving Settings -> General changes the visible authenticated UI chrome in the same session without logout or hard reload.
- After navigating across routes, the selected language remains active.
- After a hard reload with a valid stored refresh token, the selected language is active again by the time the authenticated shell meaningfully renders.
- Shared runtime locale helpers exist for date, datetime, and numeric formatting.
- The reusable/shared formatter paths touched in this phase no longer hardcode Croatian locale formatting.
- `hr.json` and `en.json` contain the keys required by the shared runtime foundation introduced in this phase.
- `de.json` and `hu.json` remain valid JSON and fall back cleanly instead of showing raw key strings.
- No enum values, API error codes, internal identifiers, or timezone/precision semantics are renamed or redesigned.
- The phase leaves a complete orchestration, backend, frontend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend and Frontend in parallel. Backend should lock the canonical `default_language` contract while Frontend implements the runtime language/bootstrap/foundation work. Testing should run after those deliveries are available.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 1 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-001`)
- `stoqio_docs/18_UI_SETTINGS.md` § 1-3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`

Goal
- Guarantee that the backend returns the canonical persisted `default_language` consistently across the Settings payloads used by the frontend runtime language lifecycle.

Non-Negotiable Contract Rules
- Keep `SystemConfig.default_language` as the persisted source of truth.
- Audit and confirm canonical `default_language` behavior on:
- `GET /api/v1/settings/general`
- `GET /api/v1/settings/shell`
- `PUT /api/v1/settings/general`
- If any route, serializer, or helper can return a stale language value after save, fix it.
- Do not redesign Settings persistence or add a second language source.
- Do not broaden this into the later Wave 3 `/settings/shell` active-user/auth hardening task unless you find a bug that directly blocks this phase.
- Keep all response shapes, field names, status codes, error codes, and RBAC unchanged unless a minimal bug fix is required for canonical language round-tripping.

Tasks
1. Audit the `settings_service` and `settings` routes end-to-end for how `default_language` is read, normalized, persisted, and returned.
2. Confirm that `GET /api/v1/settings/general` returns the canonical persisted `default_language`.
3. Confirm that `GET /api/v1/settings/shell` returns the same canonical persisted `default_language`.
4. Confirm that `PUT /api/v1/settings/general` returns the newly persisted canonical value immediately after save.
5. If you find any stale serializer/helper path, fix it with the smallest backend change set necessary.
6. Add or update targeted backend tests only if needed to lock the canonical round-trip behavior.
7. Do not broaden into frontend-driven localization work or unrelated settings cleanup.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q`
- If you touch shared settings code with wider impact, run any additional targeted subset you changed and record it.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and whether the backend contract was already correct or required fixes.
- If you discover a new cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- The backend returns canonical `default_language` consistently from the settings endpoints used by the frontend language lifecycle.
- No stale language payload path remains.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 3 Phase 1 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-001`)
- `stoqio_docs/18_UI_SETTINGS.md` § 1-3
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4.1, § 4.4, § 4.7
- `stoqio_docs/07_ARCHITECTURE.md` § 3-4
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-02/phase-07-wave-02-installation-wide-shell-branding/orchestrator.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- backend handoff for this phase after backend finishes
- `frontend/src/i18n/index.ts`
- `frontend/src/main.tsx`
- `frontend/src/store/authStore.ts`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/settings.ts`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/shared/FullPageState.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- any shared/page formatter helpers you touch

Goal
- Make the authenticated UI actually respond to saved Settings language changes at runtime and across authenticated reload/bootstrap, while creating the shared frontend localization/formatting foundation needed for later Wave 3 cleanup.

Current Repo Reality You Must Respect
- `i18n` still starts from a hardcoded `lng: 'hr'`.
- Locale JSON files are currently empty.
- Shell settings already call `i18n.changeLanguage(...)`, but much of the visible UI chrome and formatting still bypass i18n.
- Many formatter utilities hardcode `hr-HR`.
- This phase is foundational, not a full translation sweep of every page.

Non-Negotiable Contract Rules
- The active authenticated-session UI language must come from the persisted system setting, not from a one-time hardcoded assumption.
- Saving Settings -> General must update the active i18n language immediately in the current session without logout or reload.
- Authenticated bootstrap with a stored refresh token must apply the selected language before or during the first meaningful shell render so the app does not visually remain in the old language until later interaction.
- Do not introduce a new browser-only source of truth that can diverge from `SystemConfig.default_language`.
- Shared components and authenticated UI chrome touched in this phase must use translation keys instead of hardcoded copy.
- Do not rename enum values, API error codes, response field names, variable names, or internal identifiers.
- Locale-file rules for this phase:
- `hr.json` complete for every key used after your changes
- `en.json` complete for the same shared/runtime key set
- `de.json` and `hu.json` valid JSON only; no guessed translations required
- Croatian fallback must be preferred over raw keys for missing `de`/`hu` translations.
- Locale-aware formatting helpers must change only locale selection, not quantity precision rules or timezone semantics.
- Do not broaden this into a repo-wide page-by-page translation pass; focus on runtime correctness plus the shared chrome/foundation required to make the language switch visibly work.

Tasks
1. Audit the current language lifecycle end-to-end:
- app bootstrap in `main.tsx`
- shell settings load in `settingsStore.ts` / `AppShell.tsx`
- Settings -> General save flow
- route transitions
- hard reload with stored refresh token
2. Remove the current hardcoded `lng: 'hr'` assumption as the effective runtime source for authenticated sessions.
3. Ensure the saved/persisted language becomes the active i18n language in the current session immediately after General settings save.
4. Ensure the authenticated bootstrap path applies the saved language before or during the first meaningful shell render.
5. Introduce a consistent localization pattern for shared/authenticated UI chrome:
- sidebar labels
- shell/loading/fatal-state text touched for runtime correctness
- shared controls/messages you touch while fixing the runtime flow
6. Expand locale JSON files as needed:
- `hr.json` complete for keys used in this phase
- `en.json` complete for keys used in this phase
- `de.json` and `hu.json` valid JSON infrastructure only
7. Create shared locale-aware helpers for:
- date formatting
- datetime formatting
- numeric formatting
8. Replace hardcoded `hr-HR` formatting in reusable/shared helpers and page utilities you touch with the new locale-aware helpers.
9. Keep the existing quantity precision logic and timezone semantics unchanged.
10. Make the smallest coherent change set that establishes this runtime foundation cleanly; leave deeper residual copy cleanup for Wave 3 Phase 2 unless a touched surface would otherwise remain obviously broken.

Verification
- Run at minimum:
- `cd frontend && CI=true npm run test`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- By code-path review and/or targeted tests, verify:
- saved General settings change the active i18n language immediately
- authenticated shell/bootstrap no longer meaningfully renders in the stale language after reload
- shared formatting helpers use the active locale instead of hardcoded `hr-HR`

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, assumptions, and which UI chrome/components were intentionally migrated in this phase.
- If you discover the backend language payload contract differs from this handoff, log the mismatch instead of silently inventing a new frontend source of truth.

Done Criteria
- Saving Settings language visibly changes the authenticated UI chrome in the same session.
- Authenticated reload/bootstrap honors the saved language.
- Shared locale-aware formatting helpers exist and replace the hardcoded locale paths you touched.
- The new i18n keys exist in `hr.json` and `en.json`, while `de.json` / `hu.json` stay valid fallback shells.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 1 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-001`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `frontend/src/store/settingsStore.ts`
- `frontend/src/i18n/index.ts`
- `frontend/src/main.tsx`
- existing frontend test files under `frontend/src/**/__tests__`
- any new locale-formatting helper file(s)

Goal
- Lock regression coverage for the runtime language lifecycle and the new locale-aware formatting helpers, then record the manual verification flow for cross-page language switching.

Non-Negotiable Test Rules
- Focus on runtime language behavior and shared formatting helpers, not on translating every page in the application.
- Do not rewrite large areas of unrelated test scaffolding.
- If backend changes were required for canonical `default_language` round-tripping, add only the smallest targeted backend assertion needed; otherwise keep the main testing focus on frontend behavior.

Tasks
1. Add or update frontend tests covering at minimum:
- loading shell settings applies `default_language`
- applying saved General settings changes the active i18n language
- authenticated bootstrap/runtime path honors the persisted language when shell settings load
2. Add tests for the new locale-aware formatting helpers:
- date formatting
- datetime formatting
- numeric formatting
3. Record manual verification steps for:
- log in as ADMIN
- open Settings -> General
- change `default_language`
- save and remain on the page
- observe visible UI change
- navigate to another route
- hard reload while still authenticated
- confirm the selected language remains active
4. If the frontend implementation narrows the phase scope to specific shared shell surfaces, make sure the tests reflect that locked runtime scope rather than inventing a broader translation contract.

Verification
- Run at minimum:
- `cd frontend && CI=true npm run test`
- If you add any backend assertion for the settings payload contract, also run:
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q`

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, manual verification steps, open issues, and any remaining areas intentionally deferred to Wave 3 Phase 2.

Done Criteria
- Automated coverage exists for the runtime language lifecycle touched in this phase.
- Automated coverage exists for the locale-aware formatting helpers introduced in this phase.
- Manual cross-page language-switch verification steps are documented in handoff.
- Verification is recorded cleanly.

## [2026-04-02 21:45 CEST] Orchestrator Validation - Phase Not Accepted Yet

Status
- changes_requested

Scope
- Reviewed the backend, frontend, and testing handoffs for Wave 3 Phase 1.
- Inspected the delivered code changes against the locked runtime-language and locale-foundation contract.
- Re-ran the claimed verification gates for frontend tests/lint/build and backend settings coverage.

Docs Read
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/backend.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/frontend.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/testing.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/decisions/decision-log.md` (`DEC-I18N-001`)
- `frontend/src/i18n/index.ts`
- `frontend/src/main.tsx`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/store/__tests__/settingsStore.test.ts`
- `frontend/src/utils/locale.ts`
- `frontend/src/utils/locale.test.ts`
- `backend/tests/test_settings.py`

Files Reviewed
- `frontend/src/i18n/index.ts`
- `frontend/src/main.tsx`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/i18n/locales/hr.json`
- `frontend/src/i18n/locales/en.json`
- `frontend/src/i18n/locales/de.json`
- `frontend/src/i18n/locales/hu.json`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/store/__tests__/settingsStore.test.ts`
- `frontend/src/utils/locale.ts`
- `frontend/src/utils/locale.test.ts`
- `backend/tests/test_settings.py`

Commands Run
```bash
git status --short
git diff -- backend/tests/test_settings.py frontend/src/main.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/Sidebar.tsx frontend/src/pages/settings/SettingsPage.tsx frontend/src/pages/approvals/components/DraftGroupCard.tsx frontend/src/pages/reports/reportsUtils.ts frontend/src/pages/warehouse/warehouseUtils.ts frontend/src/pages/orders/orderUtils.ts frontend/src/pages/identifier/identifierUtils.ts frontend/src/pages/employees/EmployeeDetailPage.tsx frontend/src/pages/receiving/ReceivingPage.tsx frontend/src/pages/inventory/InventoryCountPage.tsx frontend/src/utils/locale.ts frontend/src/utils/locale.test.ts frontend/src/store/__tests__/settingsStore.test.ts frontend/src/i18n/locales/hr.json frontend/src/i18n/locales/en.json
rg -n "hr-HR|toLocale(Date|String)|Intl\\.(DateTimeFormat|NumberFormat)" frontend/src -g '*.ts' -g '*.tsx'
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
```

Validation Result
- `cd frontend && CI=true npm run test` -> `7 passed, 30 tests passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> failed
- build error:
- `src/store/__tests__/settingsStore.test.ts(46,60): error TS2345: Argument of type '{ location_name: string; default_language: string; }' is not assignable to parameter of type 'SettingsGeneral'. Property 'timezone' is missing...`
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` -> `48 passed`

Accepted Work
- Backend audit and regression lock are good:
- the canonical `default_language` round-trip is now explicitly covered in `backend/tests/test_settings.py`
- no backend serializer or persistence drift was found for this phase
- Frontend correctly introduced one shared locale utility entrypoint and removed the previously scattered hardcoded `hr-HR` formatting paths from the touched modules.
- Frontend shell surfaces moved part of the authenticated chrome onto translation keys (`main.tsx`, `AppShell.tsx`, `Sidebar.tsx`).

Blocking Findings
- Build-breaking test regression:
- the new test in `frontend/src/store/__tests__/settingsStore.test.ts:46` calls `applyGeneralSettings(...)` with an object missing the required `timezone` field from `SettingsGeneral`
- this causes `npm run build` to fail under TypeScript, so the phase does not meet its own verification gate
- the testing handoff claims the build passed, but the actual rerun does not confirm that claim
- Contract drift in fallback-language behavior:
- `frontend/src/i18n/index.ts:17` still sets `fallbackLng: 'en'` while `frontend/src/i18n/locales/de.json` and `frontend/src/i18n/locales/hu.json` remain empty objects
- for this phase, the locked contract was `de -> hr` and `hu -> hr` fallback so users see Croatian rather than guessed English when DE/HU translations are intentionally absent
- with the current config, selecting `de` or `hu` falls back to English resources instead of Croatian, so the accepted Wave 3 Phase 1 locale-fallback requirement is not yet satisfied

Open Risks
- The new frontend tests cover the store-level language transitions and locale helpers, but the promised authenticated bootstrap-path verification remains indirect. No test currently exercises the `main.tsx` startup flow end-to-end; that is acceptable only after the blocking issues above are fixed and the resulting runtime path is re-verified.

Closeout Decision
- Wave 3 Phase 1 is not accepted yet.

Next Action
- Frontend:
- fix the TypeScript build break in `frontend/src/store/__tests__/settingsStore.test.ts`
- align i18n fallback behavior so empty `de` / `hu` resources fall back to Croatian as locked in this phase
- Testing:
- re-run and re-record the real frontend build result after the test fix
- update test coverage and handoff notes so bootstrap/fallback claims match the actual implementation
- After those fixes, re-run:
- `cd frontend && CI=true npm run test`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q`

## [2026-04-02 21:52 CEST] Orchestrator Direct Fix + Final Validation

Status
- accepted

Scope
- Implemented the Phase 1 blocker fixes directly in the shared workspace after the earlier validation findings.
- Re-ran the frontend and backend verification gates.
- Re-reviewed the testing handoff open-risk notes to determine which ones could be safely closed within Phase 1 without broadening into the planned Phase 2 copy sweep.

Files Changed By Orchestrator
- `frontend/src/i18n/index.ts`
- `frontend/src/i18n/index.test.ts`
- `frontend/src/store/__tests__/settingsStore.test.ts`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`

Fixes Applied
- Closed blocking frontend build regression:
- `frontend/src/store/__tests__/settingsStore.test.ts` now passes a full `SettingsGeneral`-shaped object to `applyGeneralSettings(...)`, including `timezone`
- this removes the TypeScript mismatch that had been breaking `npm run build`
- Closed blocking fallback-contract drift:
- `frontend/src/i18n/index.ts` no longer falls back to English for missing shared runtime keys
- the fallback chain now resolves missing keys through Croatian, which matches the locked Phase 1 rule for intentionally empty `de.json` and `hu.json`
- Added regression coverage for the fixed fallback contract:
- new `frontend/src/i18n/index.test.ts` asserts that `de` and `hu` both fall back to Croatian for shared runtime keys

Testing Open-Risk Review
- Closed:
- `de.json` / `hu.json` empty-resource fallback risk is now resolved by the runtime fallback change plus regression coverage
- Still intentionally deferred to Wave 3 Phase 2:
- the broader hardcoded nested page copy / deeper modal-description cleanup remains outside the minimal Phase 1 runtime-foundation scope
- I reviewed that risk and chose not to expand this closeout into a page-by-page translation sweep because that is exactly the scope already reserved for Phase 2

Commands Run
```bash
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
```

Validation Result
- `cd frontend && CI=true npm run test` -> `8 files passed, 32 tests passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` -> `48 passed`

Closeout Decision
- The earlier blockers are resolved.
- Wave 3 Phase 1 is formally accepted.

Residual Notes
- Phase 1 now cleanly establishes the runtime language-switching and locale-formatting foundation.
- The remaining deeper hardcoded page/module copy noted by testing is still a real cleanup theme, but it belongs to the already planned Wave 3 Phase 2 localization sweep rather than this foundation phase.

Next Action
- Treat the current worktree and this orchestrator closeout as the accepted Wave 3 Phase 1 baseline.
- Proceed to Wave 3 Phase 2 for the broader residual localization / copy / diacritics cleanup.
