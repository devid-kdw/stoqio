## Phase Summary

Phase
- Wave 1 - Phase 8 - Inventory Shortage Approval Status

Objective
- Surface the approval state of inventory-generated shortage drafts on the Inventory Count history list so users can see whether shortages from a completed count are still pending, fully approved, partially rejected, or fully rejected.

Source Docs
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8, § 9
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 11, § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-001` through `DEC-INV-007`)
- `handoff/phase-12-inventory-count/orchestrator.md`
- `handoff/phase-06-wave-01-inventory-count-batch-grouping/orchestrator.md`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/tests/test_inventory_count.py`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Current Repo Reality
- `GET /api/v1/inventory` currently returns completed counts with `id`, `status`, `type`, `started_by`, `started_at`, `completed_at`, `total_lines`, `discrepancies`, and `opening_count_exists`.
- `GET /api/v1/inventory/{id}` currently returns count header fields, `summary` (`total_lines`, `no_change`, `surplus_added`, `shortage_drafts_created`), and full line detail, but no approval-state summary for shortage drafts.
- The Inventory Count history UI currently shows only date, started by, total lines, discrepancies, and completed/opening badges.
- Inventory-generated shortage drafts are created during `complete_count(...)` with `draft_type = INVENTORY_SHORTAGE` and grouped into one count-specific `DraftGroup`, but there is no explicit `inventory_count_id` foreign key on `Draft`.
- Inventory Count remains ADMIN-only in both the locked RBAC doc and the current repo. The user goal mentions warehouse staff visibility, but no RBAC or route-access change is requested in this wave.

Contract Locks / Clarifications
- This is a wave-specific follow-up under `phase-08-wave-01-*` only. Do not mix it with the original `phase-08-orders` implementation trail.
- No RBAC change in this wave. Inventory Count route access remains ADMIN-only unless the user explicitly broadens scope later.
- `shortage_drafts_summary` is additive on both:
  - `GET /api/v1/inventory`
  - `GET /api/v1/inventory/{id}`
- Summary shape is fixed:
  - `{ "total": int, "approved": int, "rejected": int, "pending": int }`
- Status mapping is based on current `Draft.status` values:
  - `DRAFT` -> `pending`
  - `APPROVED` -> `approved`
  - `REJECTED` -> `rejected`
- `total` must equal `approved + rejected + pending`.
- If a count produced no shortage drafts, all summary values must be zero.
- No schema migration or new FK should be introduced in this wave. The backend must derive the summary from the existing inventory-shortage draft creation contract already used by `complete_count(...)`.
- Because no explicit `inventory_count_id` exists on `Draft`, the linking logic must stay within current repo reality:
  - use the existing deterministic inventory-shortage draft linkage created by `complete_count(...)`
  - do not invent a new persistent relation in this phase
- Frontend history indicator logic is:
  - `total = 0` -> no additional indicator
  - `pending > 0` -> yellow pending indicator
  - `pending = 0` and `rejected = 0` -> green all-approved indicator
  - `rejected > 0` -> red rejected indicator, with partial-vs-full distinction when useful
- Client-rendered indicator copy should follow the project's Croatian UI default, even though the user prompt described the states in English.
- Backend detail endpoint must expose the new field in this wave even though no new detail-screen UI is required yet. Frontend type alignment for detail is still expected.

Delegation Plan
- Backend:
- Add `shortage_drafts_summary` to inventory history/detail responses using the existing inventory-shortage draft linkage, with no schema changes.
- Frontend:
- Extend inventory API typings and render shortage approval-status indicators in the history list only.
- Testing:
- Extend backend inventory-count coverage for zero-shortage and mixed-status summaries, and reverify the module.

Acceptance Criteria
- Inventory history items expose `shortage_drafts_summary` for completed counts.
- Inventory detail payload exposes the same `shortage_drafts_summary`.
- Count with no shortages returns zero summary values and shows no extra history indicator.
- Count with at least one pending shortage draft shows a yellow pending indicator in history.
- Count whose shortage drafts are all approved shows a green all-approved indicator in history.
- Count with at least one rejected shortage draft shows a red rejected indicator in history, with partial/full rejected distinction if implemented.
- Existing Inventory Count active flow, completed-detail line table, and shortage draft creation semantics remain unchanged.
- The phase leaves a complete orchestration, backend, frontend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the additive list/detail contract is explicit before Frontend and Testing proceed.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 8 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8, § 9
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 11, § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-001` through `DEC-INV-007`)
- `handoff/phase-12-inventory-count/orchestrator.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/tests/test_inventory_count.py`

Goal
- Extend the Inventory Count list/detail backend contract so completed counts expose the approval state of their inventory-generated shortage drafts.

Non-Negotiable Contract Rules
- Add `shortage_drafts_summary` to both:
  - `GET /api/v1/inventory`
  - `GET /api/v1/inventory/{id}`
- Summary shape is fixed:
  - `{ "total": int, "approved": int, "rejected": int, "pending": int }`
- Map draft statuses as:
  - `Draft.status = DRAFT` -> `pending`
  - `Draft.status = APPROVED` -> `approved`
  - `Draft.status = REJECTED` -> `rejected`
- If no inventory-generated shortage drafts exist for the count, return all zeros.
- Keep existing endpoints ADMIN-only. No RBAC change in this phase.
- Do not add a new database column, migration, or explicit foreign key in this wave.
- Current repo reality has no `inventory_count_id` on `Draft`; derive the linkage from the existing inventory shortage creation contract already emitted by `complete_count(...)`.
- Preserve the existing count summary fields and response shapes otherwise; this is additive, not a redesign of list/detail payloads.

Tasks
1. Implement a backend helper for `shortage_drafts_summary` in `backend/app/services/inventory_service.py`.
2. Extend `list_counts(...)` so each completed history item includes the new summary field.
3. Extend `get_count_detail(...)` so the detail payload includes the same summary field.
4. Keep the implementation within current repo reality:
  - derive the count's inventory shortage drafts from the existing completion flow
  - do not introduce schema changes for this wave
5. Extend `backend/tests/test_inventory_count.py` to cover at minimum:
  - completed count with no shortages -> all zero summary values
  - completed count with mixed shortage statuses (for example 1 approved, 1 pending) -> correct summary counts
  - detail payload includes `shortage_drafts_summary`
6. If a rejected-state case needs explicit coverage to protect the frontend badge logic, add it.
7. Record any cross-agent contract clarification in `handoff/decisions/decision-log.md` before finalizing if needed.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q`
- If you touch broader shared inventory/approvals behavior, run additional targeted tests and record them.

Handoff Requirements
- Append your work log to `handoff/phase-08-wave-01-inventory-shortage-approval-status/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and assumptions.

Done Criteria
- Inventory history items include `shortage_drafts_summary`.
- Inventory detail includes `shortage_drafts_summary`.
- No schema changes were introduced.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 8 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8, § 9
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/phase-12-inventory-count/orchestrator.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Goal
- Show shortage-draft approval status indicators on the Inventory Count history list without disturbing the active-count workflow or completed-detail screen.

Locked Repo Reality
- Inventory Count is currently ADMIN-only and that stays unchanged in this wave.
- The history list currently shows only date, starter, line count, discrepancies, and badges for completed/opening counts.
- Backend detail is also being extended in this wave, but no new detail-screen indicator is required unless a minimal shared type update makes that natural.

Non-Negotiable Contract Rules
- Update inventory API typings so both `HistoryItem` and `CountDetail` understand the additive `shortage_drafts_summary` field.
- History list behavior:
  - if `shortage_drafts_summary.total === 0`, render no extra indicator
  - if `total > 0` and `pending > 0`, render a yellow pending indicator
  - if `total > 0` and `pending === 0` and `rejected === 0`, render a green all-approved indicator
  - if `total > 0` and `rejected > 0`, render a red rejected indicator
- If useful, distinguish partial vs full rejection in the red-state label:
  - partial = `approved > 0`
  - full = `approved === 0`
- Keep client-rendered copy in Croatian by default, even though the product request described the states in English.
- Do not redesign the table structure or active-count view in this wave.
- Preserve current retry/fatal-error behavior for inventory history loading.

Tasks
1. Extend `frontend/src/api/inventory.ts` with the new `shortage_drafts_summary` typing shared by history/detail payloads.
2. Update the history list UI in `frontend/src/pages/inventory/InventoryCountPage.tsx` so completed rows render the shortage approval-status indicator according to the new summary.
3. Keep the existing completed/opening badges; the shortage indicator is additive.
4. Do not broaden the feature into the active-count screen.
5. No detail-screen UI change is required unless a minimal shared presentation is clearly helpful and remains tightly scoped.

Verification
- Run at minimum:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/phase-08-wave-01-inventory-shortage-approval-status/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests/build verification, open issues, and assumptions.
- If the backend contract differs from this brief, log the mismatch in handoff before finalizing.

Done Criteria
- Inventory history rows render the correct shortage approval-status indicator from backend summary data.
- Counts with no shortages render no additional indicator.
- Existing Inventory Count behaviors remain intact.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 8 of the STOQIO WMS project.

Read before testing:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 11
- `handoff/README.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `backend/tests/test_inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`

Goal
- Lock backend regression coverage for the new shortage approval-status summary on inventory history/detail payloads.

Tasks
1. Extend `backend/tests/test_inventory_count.py` to cover at minimum:
  - history list for a completed count with no shortages -> `shortage_drafts_summary.total = 0`
  - history list for a completed count with two shortage drafts in mixed states (for example 1 approved, 1 pending) -> correct summary counts
  - detail payload includes `shortage_drafts_summary`
2. If the backend implementation could accidentally miscount rejected shortages or unrelated inventory-shortage drafts from another count, add explicit coverage for that too.
3. Reuse the existing inventory count fixture/setup patterns where practical; do not rewrite unrelated test scaffolding.
4. Run the relevant backend tests and record the results.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q`
- If you run broader backend verification, record it too.

Handoff Requirements
- Append your work log to `handoff/phase-08-wave-01-inventory-shortage-approval-status/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and assumptions.
- If you find a contract mismatch, log it immediately in handoff with the precise failing behavior.

Done Criteria
- Backend coverage exists for zero-shortage, mixed-status shortage summaries, and detail payload exposure.
- Verification is recorded in handoff.

## [2026-03-24 20:43] Orchestrator Validation - Wave 1 Phase 8 Inventory Shortage Approval Status

Status
- accepted

Scope
- Reviewed backend, frontend, and testing delivery for Wave 1 Phase 8.
- Re-ran targeted verification and the full backend suite to confirm the additive shortage-summary change does not regress existing inventory or approval behavior.

Docs Read
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/backend.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/frontend.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/testing.md`

Files Reviewed
- `backend/app/services/inventory_service.py`
- `backend/tests/test_inventory_count.py`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Commands Run
```bash
git diff -- backend/app/services/inventory_service.py backend/tests/test_inventory_count.py frontend/src/api/inventory.ts frontend/src/pages/inventory/InventoryCountPage.tsx
backend/venv/bin/pytest backend/tests/test_inventory_count.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Validation Notes
- No functional review findings were identified in the delivered scope.
- Accepted backend scope alignment:
- `GET /api/v1/inventory` now exposes additive `shortage_drafts_summary` on completed history items
- `GET /api/v1/inventory/{id}` exposes the same additive summary on detail payloads
- no schema or migration change was introduced
- accepted linkage approach stays within current repo reality by deriving inventory shortage drafts from the deterministic `client_event_id` pattern emitted during count completion
- Accepted frontend scope alignment:
- history rows render additive shortage approval-status badges without disturbing the active-count screen
- counts with `total = 0` show no extra indicator
- pending / approved / rejected badge states are rendered according to the backend summary
- existing completed and opening badges remain intact
- Accepted testing/result:
- module-level inventory tests pass with new summary coverage
- full backend suite remains green after the additive change

Verification
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q` -> passed (`33 passed`)
- `backend/venv/bin/pytest backend/tests -q` -> passed (`309 passed, 1 warning`)
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- The backend summary derivation depends on the existing `client_event_id` pattern for inventory-generated shortage drafts (`inv-count-{count_id}-line-{line_id}`). That is acceptable for this wave and explicitly documented, but future agents must preserve or deliberately migrate that linkage if they refactor inventory shortage draft creation.
- Manual browser smoke validation is still advisable for the exact badge copy and visual prominence in the inventory history list, but no code-level blocker remains.

Next Action
- Treat Wave 1 Phase 8 as closed.
