## Phase Summary

Phase
- Wave 1 - Phase 6 - Inventory Count Batch Grouping

Objective
- Fix the active Inventory Count table UX by renaming the batch column correctly and restructuring batch-tracked articles into expandable parent rows with per-batch child rows.
- Keep the existing backend contract, per-line autosave, retry/fatal-error handling, and non-batch article workflow intact.

Source Docs
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/implementation/phase-12-inventory-count/orchestrator.md`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `frontend/src/api/inventory.ts`

Current Repo Reality
- The active count screen in `frontend/src/pages/inventory/InventoryCountPage.tsx` currently renders one flat table row per `InventoryCountLine`.
- The active count table header still shows `Serija` instead of `Batch`.
- Progress is currently computed directly from the flat `lines` array, so it already counts leaf count-lines rather than grouped article parents.
- Autosave already happens per `line_id` on blur through `PATCH /api/v1/inventory/{id}/lines/{line_id}` and must stay on that contract.
- The completed count detail screen also still uses a flat table, but this follow-up is scoped to the active count screen only.

Contract Locks / Clarifications
- No backend or API changes are needed. The existing `count.lines` payload remains the source of truth.
- Grouping for batch-tracked articles must be derived client-side from existing flat inventory lines.
- Countable/savable units remain the existing leaf lines:
- non-batch article row = one countable line
- each batch sub-row = one countable line
- parent rows for batch-tracked articles are display-only and must not send PATCH requests or own a counted-quantity input
- Batch article parent rows must show article number + description and a system-quantity summary in the form `N batches / X.XX UOM total` (formatted with the article's decimal-display rules).
- Child batch rows must show at minimum batch code, expiry date, system quantity, UOM, and counted-quantity input. Difference should continue to render at the leaf-row level.
- Existing filters must keep working. They apply to the countable leaf rows; a batch parent row should remain visible only if at least one of its child rows survives the current filter.
- The `X / Y counted` indicator and `Complete Count` enablement must continue to operate on countable leaf rows, not on parent article rows.
- Auto-save on blur must work identically for non-batch rows and batch child rows, including the existing retry-once-then-fatal-error behavior.
- Keep the completed detail/history table out of scope unless a minimal shared label refactor is unavoidable. No completed-count nesting is requested in this phase.

Delegation Plan
- Backend:
- None.
- Frontend:
- Rework the active Inventory Count table rendering in `InventoryCountPage.tsx` so batch-tracked items are grouped under expandable parent rows while preserving the current patch-by-line behavior and progress semantics.
- Testing:
- None.

Acceptance Criteria
- The active count table header shows `Batch` instead of `Series` / `Serija`.
- A batch-tracked article with two batches renders as one parent article row with an expand/collapse control and two child batch rows when expanded.
- A non-batch article continues to render as a single flat row with unchanged counted-quantity behavior.
- Entering a quantity in a batch child row auto-saves correctly and updates the progress indicator.
- The progress indicator counts leaf rows, so a three-batch article contributes three required counted rows.
- `Complete Count` remains disabled until every non-batch row and every batch child row has a counted quantity.
- The phase leaves a complete orchestration and frontend handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Frontend Agent only.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 6 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/orchestrator.md`
- `handoff/implementation/phase-12-inventory-count/orchestrator.md`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `frontend/src/api/inventory.ts`

Goal
- Fix the active Inventory Count table so batch-tracked articles are grouped into expandable parent rows with per-batch child rows, and rename the active-table batch column label to `Batch`.

Non-Negotiable Contract Rules
- No backend changes. Use the existing `ActiveCount.lines` / `InventoryCountLine` contract exactly as it is today.
- Group batch-tracked rows client-side from the existing flat `count.lines` data.
- Keep non-batch article rows as single flat countable rows with the current qty-input and auto-save behavior.
- For batch-tracked articles:
- render one parent article row with a chevron toggle
- render no counted-quantity input on the parent row
- when expanded, render one child row per batch line
- keep PATCH autosave on the existing child `line_id`
- Parent row system-quantity column must show a summary such as `3 batches / 75.00 kg total`, formatted with the article's `decimal_display` rules.
- Progress and completion semantics must operate on leaf count-lines only:
- each non-batch row counts as one required line
- each batch child row counts as one required line
- parent rows do not count toward `X / Y counted`
- Keep the existing retry-once-then-fatal-error behavior for autosave and complete flows.
- Keep existing discrepancy/uncounted filters working. Filters apply to leaf rows; only show a batch parent if at least one child row remains visible after filtering.
- Scope is the active count screen only. Do not redesign completed history/detail into nested rows for this phase.

Tasks
1. In the active count table, rename the batch column header from `Serija` / incorrect equivalent to `Batch`.
2. Restructure the active count table rendering in `frontend/src/pages/inventory/InventoryCountPage.tsx`:
- non-batch articles stay as single flat rows
- batch-tracked articles render as parent article rows with chevron expand/collapse
- expanded parent rows reveal one child row per batch line
3. Ensure the parent batch row shows:
- article number
- description
- no counted-quantity input
- system-quantity summary text in the form `N batches / total UOM`
4. Ensure each batch child row shows:
- batch code
- expiry date
- system quantity
- UOM
- counted-quantity input
- difference
5. Preserve per-line autosave on blur for both:
- non-batch flat rows
- batch child rows
6. Update the progress indicator and completion gating so they count leaf rows rather than visible parent rows.
7. Preserve the current filter behavior by applying filters to leaf rows and rendering only the parent groups that still contain visible children.

Verification
- Run at minimum:
- `cd frontend && npm run lint`
- `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover that the existing frontend-only scope is insufficient, stop and log the exact blocker instead of silently broadening into backend work.

Done Criteria
- Active count table shows `Batch` as the column label.
- Batch-tracked articles render as expandable parent rows with per-batch child rows.
- Progress and completion logic still operate correctly on leaf count-lines.
- Autosave still works on blur for every countable line.
- Verification is recorded in handoff.

## [2026-03-24 16:43] Orchestrator Validation - Wave 1 Phase 6 Inventory Count Batch Grouping

Status
- accepted pending manual browser smoke verification

Scope
- Reviewed the frontend-only delivery for the active Inventory Count table grouping follow-up.
- Verified the implementation against the delegated scope, current frontend contract, and required lint/build gates.

Docs Read
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 6
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/orchestrator.md`
- `handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/frontend.md`
- `handoff/implementation/phase-12-inventory-count/orchestrator.md`

Files Reviewed
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/frontend.md`

Commands Run
```bash
git status --short
git diff -- frontend/src/pages/inventory/InventoryCountPage.tsx handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/frontend.md handoff/wave-01/phase-06-wave-01-inventory-count-batch-grouping/orchestrator.md
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- No functional review findings were identified in the submitted frontend diff.
- Accepted scope alignment:
- active table header now uses `Batch`
- batch-tracked leaf lines are grouped client-side under expandable parent rows
- parent rows are display-only and do not introduce a new save path
- child rows preserve the existing `line_id`-based autosave path
- progress and completion logic still operate on the flat leaf `lines` array, which matches the required semantics
- current discrepancy/uncounted filters are applied at the leaf-row level and only keep parent groups that still have visible children
- Accepted containment:
- no backend/API changes were introduced
- completed-count detail/history nesting was not broadened into scope

Verification
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- The exact browser interaction matrix from the brief was not replayed in a live UI session from the sandbox, so expand/collapse ergonomics and blur-save timing remain manually verifiable only.
- The completed-count detail table still uses the older `Serija` label, which is acceptable for this wave because the delegated scope was limited to the active count screen.

Next Action
- Run a short manual browser smoke test on an active count containing both non-batch and multi-batch articles.
- If that smoke test matches the delegated matrix, treat this wave as closed.
