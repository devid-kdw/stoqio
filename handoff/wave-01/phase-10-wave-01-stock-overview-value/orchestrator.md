## Phase Summary

Phase
- Wave 1 - Phase 10 - Stock Overview Value

Objective
- Add monetary value visibility to the Reports module's Stock Overview tab.
- Show per-article purchase value data and a warehouse-level total without disturbing the existing Phase 13 Reports baseline.
- Keep the change additive and limited to the on-screen Stock Overview contract/UI in this wave.

Source Docs
- `stoqio_docs/17_UI_REPORTS.md` § 3, § 10, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 3, § 15
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-REP-001`, `DEC-REP-002`, `DEC-BE-007`)
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`
- `backend/tests/test_reports.py`

Current Repo Reality
- The Reports module is already implemented and verified from Phase 13.
- `GET /api/v1/reports/stock-overview` currently returns:
  - `period`
  - `items[]`
  - `total`
- Stock Overview items currently expose quantity/coverage/reorder fields only; there are no value fields yet.
- The frontend Stock Overview table currently shows quantity, movement, coverage, reorder threshold, and status columns, but no currency/value columns and no warehouse-value summary card.
- `ArticleSupplier.last_price` exists and `Receiving.unit_price` exists, but neither is currently used by the Reports stock overview contract.
- Receiving can legitimately store `unit_price = NULL` for some ad-hoc receipts (`DEC-BE-007`), so "latest receiving row" and "latest known purchase price" are not equivalent unless the backend filters for a non-null price.
- Stock Overview export endpoints already exist, but the user request in this wave is about the read contract and on-screen report display only.

Contract Locks / Clarifications
- This is a wave-specific follow-up under `phase-10-wave-01-*`. Do not mix it with the historical `phase-10-identifier` trail.
- Scope is additive on `GET /api/v1/reports/stock-overview` and the Stock Overview screen only. Do not redesign other Reports tabs in this wave.
- The Stock Overview response keeps all current fields and gains:
  - per item:
    - `unit_value`
    - `total_value`
  - top level:
    - `summary: { "warehouse_total_value": number }`
- `unit_value` source priority is fixed:
  - the most recent `Receiving` row for the article with non-null `unit_price`, ordered newest first by `received_at` and then `id` as tiebreaker
  - otherwise the preferred supplier's `ArticleSupplier.last_price`
  - otherwise `null`
- Preferred-supplier fallback means exactly the preferred supplier link. Do not scan non-preferred supplier rows for a backup price in this wave.
- `total_value` is fixed as:
  - `stock × unit_value`
  - use the existing `stock` quantity from the Stock Overview logic
  - do not include `surplus` in the value calculation for this wave
  - return `null` only when `unit_value` is `null`
  - if `stock = 0` and `unit_value` is known, return numeric `0`, not `null`
- `warehouse_total_value` is the sum of all non-null item `total_value` values in the filtered report result set. If no items have price data, the sum should serialize as numeric `0`.
- Use Decimal arithmetic in the backend. The frontend will format values as 2-decimal currency for display.
- RBAC stays unchanged:
  - `GET /api/v1/reports/stock-overview` remains `ADMIN` + `MANAGER`
  - export endpoints remain as they are today
- Export column changes are not part of this wave unless the user broadens scope later. Keep the current export contract unchanged.
- The frontend summary card should use the backend `summary.warehouse_total_value` for the loaded stock-overview result and should not locally re-aggregate around the page-only drilldown filter.

Delegation Plan
- Backend:
- Extend the Stock Overview read contract with item-level monetary fields and a top-level summary while preserving current filters, ordering, and RBAC.
- Frontend:
- Add value columns and a warehouse-value summary callout to the Stock Overview tab using the additive backend contract and Croatian client copy.
- Testing:
- Extend backend Reports coverage for receiving-price priority, supplier fallback/no-price cases, and warehouse total aggregation.

Acceptance Criteria
- `GET /api/v1/reports/stock-overview` returns additive `unit_value` and `total_value` fields for each item.
- `GET /api/v1/reports/stock-overview` returns additive `summary.warehouse_total_value`.
- Most recent known receiving price wins over preferred-supplier `last_price`.
- Article with no receiving price and no preferred-supplier `last_price` returns `unit_value = null` and `total_value = null`.
- Stock Overview table shows `Unit value` and `Total value` columns formatted as currency, with `—` only for `null` values.
- Stock Overview shows a warehouse-value summary card/callout at the top.
- If at least one returned article has no price data, the summary card warns that the total excludes articles without price data.
- Existing Stock Overview filters, reorder-only toggle, local statistics drilldown, export buttons, and other Reports tabs remain intact.
- The phase leaves a complete orchestration, backend, frontend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the additive Stock Overview value contract is explicit before Frontend and Testing proceed.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 10 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/17_UI_REPORTS.md` § 3, § 10, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 3, § 15
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-REP-001`, `DEC-REP-002`, `DEC-BE-007`)
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/orchestrator.md`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`

Goal
- Extend the Stock Overview backend contract with monetary value data while preserving the accepted Phase 13 Reports baseline.

Non-Negotiable Contract Rules
- This wave changes `GET /api/v1/reports/stock-overview` only. Keep the route path, current filters, RBAC, and error semantics unchanged.
- Preserve all current response fields and add:
  - per item:
    - `unit_value`
    - `total_value`
  - top level:
    - `summary: { "warehouse_total_value": number }`
- `unit_value` source priority is fixed:
  - most recent `Receiving` row for that article with non-null `unit_price`, ordered by `received_at DESC, id DESC`
  - otherwise preferred supplier's `ArticleSupplier.last_price`
  - otherwise `null`
- Do not use a newer `Receiving` row with `unit_price = NULL` to erase an older known price. The receiving source must mean "most recent non-null purchase price."
- Preferred-supplier fallback means the preferred link only. Do not scan non-preferred supplier links for a backup price.
- `total_value = stock × unit_value`
  - use the same stock quantity already exposed as `stock`
  - do not include `surplus` or `total_available` in the calculation
  - return `null` only when `unit_value` is `null`
  - if stock is zero and price exists, return numeric zero
- `summary.warehouse_total_value` equals the sum of all non-null item `total_value` values in the filtered result set.
- Keep using Decimal arithmetic; do not switch this calculation to float math internally.
- Export endpoints are not in scope for new columns in this wave. Do not expand the stock-overview export headers unless you discover a blocker and log it first.

Tasks
1. Add a backend helper in `backend/app/services/report_service.py` that resolves each article's `unit_value` using the locked source priority.
2. Extend stock overview item serialization to include:
   - `unit_value`
   - `total_value`
3. Extend `get_stock_overview(...)` to include:
   - additive `summary.warehouse_total_value`
4. Preserve all existing Stock Overview behavior:
   - date/category validation
   - reorder-only filtering
   - existing item ordering
   - existing quantity and coverage calculations
5. Keep `backend/app/api/reports/routes.py` thin and unchanged except where strictly necessary to expose the additive response shape.
6. Do not broaden scope into other Reports endpoints or unrelated report exports.

Verification
- Extend backend tests as needed.
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_reports.py -q`
- If you touch shared report behavior beyond that file, run any additional targeted regressions and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-10-wave-01-stock-overview-value/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover a cross-agent contract clarification while implementing, add it to `handoff/decisions/decision-log.md` before finalizing backend work.

Done Criteria
- Stock Overview items expose `unit_value` and `total_value`.
- Stock Overview top-level payload exposes `summary.warehouse_total_value`.
- Receiving-price priority, preferred-supplier fallback, and no-price null behavior follow the locked contract.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 10 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/17_UI_REPORTS.md` § 3, § 9, § 10, § 11
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`

Goal
- Add on-screen monetary value visibility to the Stock Overview tab without disturbing the accepted Phase 13 Reports UX.

Non-Negotiable Contract Rules
- Keep the Reports route, tab layout, existing filters, existing export buttons, and other report tabs unchanged.
- Update the Stock Overview API typings to understand:
  - per item:
    - `unit_value`
    - `total_value`
  - top level:
    - `summary.warehouse_total_value`
- Add two Stock Overview table columns:
  - `Vrijednost / jed.`
  - `Ukupna vrijednost`
- Display values as Croatian-formatted currency with euro suffix, e.g. `12,50 €`.
- Show `—` only when the backend value is `null`. Numeric zero must render as currency (`0,00 €`), not as `—`.
- Add a summary card/callout near the top of the Stock Overview section showing the warehouse total in Croatian, for example:
  - `Ukupna vrijednost skladišta: X.XXX,XX €`
- If any returned article has `unit_value === null`, add a note in the card/callout that the total excludes articles without price data.
- The summary card should use the backend `summary.warehouse_total_value` for the loaded stock-overview result; do not locally re-sum the page-only statistics drilldown subset.
- Keep MANAGER behavior unchanged: read-only Reports access, no export buttons.

Tasks
1. Extend `frontend/src/api/reports.ts` with the additive Stock Overview value fields and summary object.
2. Add a small currency-formatting helper in `frontend/src/pages/reports/reportsUtils.ts` if it keeps the Reports page clean.
3. Update `frontend/src/pages/reports/ReportsPage.tsx`:
   - add the new summary card/callout at the top of the Stock Overview section
   - add the two new value columns to the Stock Overview table
   - render `—` only for null values
4. Keep the existing stock table empty state, loading behavior, retry/fatal-error behavior, and local reorder/drilldown filters intact.
5. Do not redesign the Stock Overview layout beyond the minimal additions needed for the new value information.

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-10-wave-01-stock-overview-value/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If the backend contract differs from this brief, log the mismatch before finalizing.

Done Criteria
- Stock Overview table shows per-item unit and total value columns.
- Stock Overview shows the warehouse total summary callout.
- Null-vs-zero display behavior is correct.
- Existing Reports UX stays intact.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 10 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `backend/tests/test_reports.py`
- `backend/app/services/report_service.py`
- `backend/app/api/reports/routes.py`

Goal
- Lock backend regression coverage for the additive Stock Overview value contract.

Tasks
1. Extend `backend/tests/test_reports.py`.
2. Cover at minimum:
   - Stock Overview item includes `unit_value` and `total_value`
   - article with no receiving history and no preferred-supplier price -> `unit_value = null`, `total_value = null`
   - `summary.warehouse_total_value` equals the sum of non-null item `total_value` values
3. Add targeted coverage for source priority:
   - most recent non-null receiving price wins over preferred-supplier `last_price`
   - if there is no usable receiving price, preferred-supplier `last_price` is used
4. If the backend implementation treats a newer null-priced receiving as stronger than an older known price, add/keep explicit coverage proving that is incorrect.
5. Reuse the existing Reports fixture/setup patterns; do not rewrite unrelated Reports scaffolding.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_reports.py -q`
- If you run broader regressions, record them too.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-10-wave-01-stock-overview-value/testing.md`.
- Use the section shape required by `handoff/README.md`.
- If you find a contract mismatch, log it immediately in handoff with the precise failing behavior.

Done Criteria
- Backend coverage exists for item-level value fields, null-price behavior, source priority, and warehouse total aggregation.
- Verification is recorded in handoff.

## [2026-03-24 22:06] Orchestrator Validation - Wave 1 Phase 10 Stock Overview Value

Status
- accepted

Scope
- Reviewed backend, frontend, and testing deliveries for Wave 1 Phase 10.
- Compared the delivered code against the locked additive Stock Overview value contract.
- Re-ran targeted and full verification to confirm no Reports/UI regressions were introduced.

Docs Read
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/orchestrator.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/backend.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/frontend.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/testing.md`
- `handoff/implementation/phase-13-reports/orchestrator.md`

Files Reviewed
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`
- `frontend/src/api/reports.ts`
- `frontend/src/pages/reports/ReportsPage.tsx`
- `frontend/src/pages/reports/reportsUtils.ts`

Commands Run
- `backend/venv/bin/pytest backend/tests/test_reports.py -q`
- `backend/venv/bin/pytest backend/tests -q`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Validation Result
- `backend/venv/bin/pytest backend/tests/test_reports.py -q` -> `34 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `323 passed, 1 warning`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Accepted Work
- Backend correctly extends `GET /api/v1/reports/stock-overview` with additive per-item `unit_value` / `total_value` fields and top-level `summary.warehouse_total_value`.
- Source priority is implemented as delegated:
  - newest non-null receiving price wins
  - preferred-supplier `last_price` is the fallback
  - no-price articles return `null` values
- `total_value` is correctly based on `stock` only, not `surplus` or `total_available`.
- Frontend correctly adds the two value columns and a warehouse-total summary callout without disturbing the accepted Phase 13 Reports layout or MANAGER read-only behavior.
- Currency formatting handles `null` vs numeric zero correctly.
- Backend regression coverage in `backend/tests/test_reports.py` now locks the new value contract and the null-priced-receiving edge case.

Findings
- None. No blocking bugs, contract mismatches, or verification failures were found in the delivered Phase 10 wave changes.

Residual Notes
- Stock Overview XLSX/PDF exports intentionally remain unchanged in this wave and therefore do not include the new value columns. This matches the locked scope for the phase.

Next Action
- Wave 1 Phase 10 can be treated as formally closed. The current baseline is ready for the next wave/phase.
