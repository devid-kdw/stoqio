## Phase Summary

Phase
- Wave 3 - Phase 6 - Backend Helper & Numbering Deduplication

Objective
- Remove the remaining backend helper duplication in `report_service.py` query parsing and centralize shared `IZL-####` DraftGroup numbering without changing runtime behavior.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-006`, `W3-007`)
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-004`, `DEC-INV-001`, `DEC-INV-005`, `DEC-BE-013`)
- `backend/app/utils/validators.py`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/app/models/draft_group.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`

Current Repo Reality
- `backend/app/services/report_service.py` still defines local `_parse_positive_int(...)` and `_parse_bool(...)` helpers even though `backend/app/utils/validators.py` already contains shared query-parsing utilities.
- The live report-service call sites that currently depend on those local helpers are:
- `_transaction_base_query(article_id=...)`
- `get_transaction_log(page=..., per_page=...)`
- `get_stock_overview(reorder_only=...)`
- Current report-service parsing semantics are not a drop-in match for the shared validator helpers:
- the local report helpers treat `(None, "")` as "use default" for `page`, `per_page`, and `reorder_only`
- `backend/app/utils/validators.py` currently defaults only on `None`
- report routes call the service layer directly and only catch `ReportServiceError`, so a raw `QueryValidationError` leak would change current error plumbing
- `IZL-####` DraftGroup numbering is currently duplicated in:
- `backend/app/api/drafts/routes.py` via `_next_draft_group_number()`
- `backend/app/services/inventory_service.py` via `_next_group_number()`
- Both current numbering implementations use the same effective semantics:
- scan existing `DraftGroup.group_number` values
- ignore non-matching strings such as `IZL-LEGACY-*`
- derive the next visible number from the maximum matching numeric suffix
- format the next value as `IZL-####`
- do not derive the visible number from `DraftGroup.id`
- Both daily outbound draft creation and inventory-shortage draft creation currently consume the same shared visible sequence because both scan the full `DraftGroup` table.
- Existing tests already lock important parts of that contract:
- `backend/tests/test_drafts.py::test_group_number_uses_max_existing_suffix_not_id`
- inventory-count completion coverage that confirms shortage groups receive `IZL-*` numbers
- but the repo does not yet clearly lock the centralized cross-caller sequence behavior after deduplication.

Contract Locks / Clarifications
- Runtime behavior must remain unchanged.
- Do not change report response shapes, pagination keys, ordering, status codes, error codes, or field names.
- Preserve the current blank-string/default behavior for report query parsing:
- `page=""` and `per_page=""` still fall back to their existing defaults
- `reorder_only=""` still falls back to `False`
- Keep report validation failures surfaced through `ReportServiceError`; do not leak `QueryValidationError` out of `report_service.py`.
- This phase is not a repo-wide validator cleanup. Limit deduplication scope to `report_service.py` plus the minimum shared wrapper/helper needed to preserve current semantics.
- Centralize only `IZL-####` DraftGroup numbering. Do not broaden into:
- `ORD-####` order-number logic
- a new DB sequence
- a `SystemConfig` counter for draft groups
- broader DraftGroup lifecycle/refactor work
- Preserve accepted `IZL-####` semantics exactly:
- use the maximum existing matching numeric suffix
- ignore non-matching group numbers
- keep the visible zero-padded `IZL-####` format
- keep one shared sequence across `DAILY_OUTBOUND` and `INVENTORY_SHORTAGE`
- Put the shared IZL helper in a lightweight module both route and service code can import without creating circular dependencies.
- No frontend changes are expected in this phase.

Delegation Plan
- Backend:
- replace report-service parser duplication through shared validator usage and/or thin service-level wrappers that preserve current semantics exactly
- extract one shared IZL numbering helper and switch both Draft Entry and Inventory Count to it
- Testing:
- add/update regression coverage for report query validation semantics and both numbering call sites
- rerun the full backend suite because the touched code sits in shared validation / shared numbering infrastructure

Acceptance Criteria
- `backend/app/services/report_service.py` no longer contains duplicate local integer/bool query-parsing helpers.
- Report query behavior, error payloads, and blank-string/default semantics remain unchanged.
- `IZL-####` numbering logic exists in one shared place and is used by both draft-group callers.
- Daily outbound and inventory-shortage group creation still share the same visible numbering sequence.
- Numbering still ignores non-matching group numbers and still uses the maximum existing numeric suffix rather than row ids.
- Targeted and full backend tests pass.
- The phase leaves complete backend, testing, and orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first, then Testing after backend delivery is available. Testing depends on the final helper-extraction shape.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 6 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-006`, `W3-007`)
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-004`, `DEC-INV-001`, `DEC-INV-005`, `DEC-BE-013`)
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/orchestrator.md`
- `backend/app/utils/validators.py`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/app/models/draft_group.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`

Goal
- Remove duplicated backend helper logic in `report_service.py` and centralize shared `IZL-####` DraftGroup numbering without changing caller-visible behavior.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation files and `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/backend.md`.
- Do not edit backend test files in this phase. The testing agent owns backend test changes. If you discover a test gap that must be locked, document it clearly in your handoff.

Current Repo Reality You Must Respect
- `report_service.py` currently uses local `_parse_positive_int(...)` for:
- `article_id` in `_transaction_base_query()`
- `page` / `per_page` in `get_transaction_log()`
- `report_service.py` currently uses local `_parse_bool(...)` for:
- `reorder_only` in `get_stock_overview()`
- Current report-service helper semantics treat `(None, "")` as "use default" for the touched query params.
- Shared helpers in `app/utils/validators.py` already exist, but their current semantics and exception type are not a drop-in replacement for the service layer.
- `IZL-####` generation is currently duplicated in:
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- Accepted numbering semantics are already locked in the repo:
- max visible numeric suffix wins
- `DraftGroup.id` must not drive the visible number
- non-matching strings like `IZL-LEGACY-*` must be ignored
- both daily draft groups and inventory-shortage groups consume the same shared visible sequence

Non-Negotiable Contract Rules
- Keep all caller-visible behavior unchanged.
- Do not leak `QueryValidationError` out of `report_service.py`; routes currently expect `ReportServiceError`.
- Preserve report blank-string/default behavior exactly.
- Do not broaden this into a repo-wide validator cleanup or a broader Reports refactor.
- Do not change report filtering, pagination, ordering, export behavior, or statistics behavior.
- Do not touch order-number generation or invent a new storage-backed draft-group counter.
- Place the shared IZL helper somewhere both route and service code can import safely without circular imports.

Tasks
1. Replace the local report query-parser duplication with shared utility usage and/or thin service-level adapter helpers that preserve the current `ReportServiceError` contract exactly.
2. Remove the local `_parse_positive_int(...)` and `_parse_bool(...)` logic from `backend/app/services/report_service.py`.
3. Extract one shared helper for next visible `IZL-####` DraftGroup number generation.
4. Replace the duplicated numbering implementations in:
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
5. Preserve the exact numbering semantics already accepted in the repo.
6. Keep the change set narrow and implementation-focused.
7. Record any test gaps the testing agent should lock if you do not change tests yourself.

Verification
- Run at minimum:
- `rg -n 'def _parse_positive_int|def _parse_bool' backend/app/services/report_service.py`
- `rg -n '_next_draft_group_number|_next_group_number' backend/app -g '*.py'`
- `cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_drafts.py tests/test_inventory_count.py -q`
- Because this phase touches shared validation / shared-helper infrastructure, also run:
- `cd backend && venv/bin/python -m pytest -q`

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- every report-service parser call site that changed
- the chosen shared/helper strategy and why it preserves current semantics
- where the shared IZL helper now lives
- which old numbering call sites now use it
- files changed
- commands run
- tests run
- open issues or residual risk
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- No local duplicate integer/bool parser implementations remain in `report_service.py`.
- The IZL numbering helper exists in one shared place and both callers use it.
- Report behavior and numbering semantics remain unchanged.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 6 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-006`, `W3-007`)
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/orchestrator.md`
- backend handoff for this phase after backend finishes
- `backend/app/utils/validators.py`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`

Goal
- Lock regression coverage around the report-parser deduplication and shared `IZL-####` numbering centralization so the backend cleanup stays behaviorally identical.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files and `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/testing.md`.

Non-Negotiable Contract Rules
- This is a backend maintainability phase only. Do not broaden into product changes.
- Focus on proving behavior stayed the same after deduplication.
- Prefer behavioral regression coverage over brittle implementation-detail assertions.
- If you add a direct helper-level test for the centralized numbering utility, keep it small and do not use it as a substitute for caller-level regression coverage.

Minimum Required Coverage
1. Reports query parsing:
- lock the current blank-string/default behavior for the touched report query params
- lock the current invalid-value error contract for the touched report query params
- ensure the response/error semantics still route through the accepted report contract
2. Draft-group numbering:
- confirm daily draft-group creation still uses the next visible `IZL-####` number
- confirm inventory-shortage draft-group creation still uses the same shared visible sequence
- confirm non-matching group numbers do not affect the next visible numeric suffix
- confirm numbering is still driven by max existing matching suffix, not row ids
3. Run the targeted suites and the full backend suite after the backend refactor lands.

Testing Guidance
- Extend the existing backend suites first:
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- For report validation coverage, explicitly think about:
- `page`
- `per_page`
- `reorder_only`
- blank-string handling vs invalid-value handling
- For numbering coverage, explicitly think about:
- existing daily draft groups
- existing inventory-shortage groups
- legacy non-matching `group_number` values such as `IZL-LEGACY-*`
- shared sequence behavior across both callers
- Do not add brittle assertions that merely restate the implementation shape unless they are needed to lock the accepted behavior.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_drafts.py tests/test_inventory_count.py -q`
- `cd backend && venv/bin/python -m pytest -q`
- Confirm the backend delivery removed the local report parser helpers and centralized the IZL numbering helper, either by your own repo search or by reviewing the backend delivery.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which report-validation behaviors were explicitly locked
- which numbering behaviors were explicitly locked
- residual risk, if any

Done Criteria
- Regression coverage exists for the touched report-validation and numbering behaviors.
- Targeted and full backend suites are green.
- Verification is recorded in handoff.

## [2026-04-03 16:31 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend and testing work for Wave 3 Phase 6.
- Compared the agent handoffs against the actual repo diff.
- Re-ran the requested verification matrix for the touched backend-helper and numbering scope.

Docs Read
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/backend.md`
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/testing.md`
- `handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/orchestrator.md`
- `backend/app/services/report_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- `backend/app/utils/draft_numbering.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`

Commands Run
```bash
git status --short
git diff -- backend/app/services/report_service.py backend/app/api/drafts/routes.py backend/app/services/inventory_service.py backend/app/utils/draft_numbering.py backend/tests/test_reports.py backend/tests/test_drafts.py backend/tests/test_inventory_count.py handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/backend.md handoff/wave-03/phase-06-wave-03-backend-helper-and-numbering-deduplication/testing.md
rg -n 'def _parse_positive_int|def _parse_bool' backend/app/services/report_service.py
rg -n '_next_draft_group_number|_next_group_number' backend/app -g '*.py'
cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_drafts.py tests/test_inventory_count.py -q
cd backend && venv/bin/python -m pytest -q
```

Findings
- None.

Validation Result
- Passed:
- `backend/app/utils/draft_numbering.py` now holds the shared `next_izl_group_number()` helper, and both former duplicate callers now use it:
- `backend/app/api/drafts/routes.py`
- `backend/app/services/inventory_service.py`
- repo search confirms the previous duplicate numbering helpers are gone:
- `rg -n '_next_draft_group_number|_next_group_number' backend/app -g '*.py'` -> no results
- `report_service.py` still contains `_parse_positive_int(...)` and `_parse_bool(...)` by name, but they are now thin service-layer adapters over the shared validator utilities rather than standalone duplicated parsing implementations
- blank-string/default semantics remain preserved for the touched report query params through those adapters
- backend tests now explicitly lock the intended regression surfaces:
- report blank-string/default and invalid-value validation for `reorder_only`, `page`, and `per_page`
- draft numbering ignoring non-matching `IZL-*` strings
- inventory-shortage group creation using the shared visible `IZL-####` sequence
- `cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_drafts.py tests/test_inventory_count.py -q` -> `130 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `455 passed in 61.72s`

Closeout Decision
- Wave 3 Phase 6 is accepted and closed.

Residual Notes
- No residual implementation or regression issues were found in this phase.

Next Action
- Treat the current worktree and this orchestrator closeout as the accepted Wave 3 Phase 6 baseline.
- Proceed to Wave 3 Phase 7 - Revoked Token Retention Cleanup.
