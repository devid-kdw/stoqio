## Phase Summary

Phase
- Phase 12 - Inventory Count

Objective
- Deliver the Inventory Count module end to end:
- start a new count from the current system snapshot
- enter counted quantities line by line with autosave
- complete the count with automatic surplus / shortage handling
- keep the result compatible with the existing Approvals flow

Source Docs
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 4
- `stoqio_docs/05_DATA_MODEL.md` § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Delegation Plan
- Backend:
- Implement inventory service + routes, wire automatic discrepancy processing, register the blueprint, and add backend coverage.
- Frontend:
- Replace the `/inventory` placeholder with the real Inventory Count page and wire it to the backend contract.
- Testing:
- Verify backend integration coverage for the full count lifecycle and keep the backend suite green.

Acceptance Criteria
- ADMIN can start exactly one active count at a time.
- Active count lines snapshot the current system quantity for every active article, with batch-aware rows for batch-tracked items.
- Counted quantities save per line and completion is blocked until all lines are counted.
- Completion creates `SURPLUS_ADDED`, `SHORTAGE_DRAFT_CREATED`, or `NO_CHANGE` outcomes correctly.
- Shortage drafts appear in the existing Approvals pipeline without extra frontend/backend changes in that module.
- Phase 12 leaves a complete handoff trail across orchestration, backend, frontend, and testing.

Validation Notes
- Initial post-agent review found four issues:
- `system_quantity` was snapshot from `Stock` only and ignored existing `Surplus`, which broke the documented `system_total` inventory rule.
- shortage `DraftGroup.operational_date` was written as the raw UTC date instead of the location operational timezone used elsewhere in the drafts/approvals workflow.
- frontend start / autosave / complete flows did not follow the global retry-then-full-page-error pattern on network/server failures.
- this phase folder was missing `orchestrator.md`, so the required orchestration trace was incomplete.

Next Action
- Apply orchestrator remediation, rerun backend/frontend verification, then reassess whether Phase 12 can be formally closed.

## Orchestrator Follow-Up - 2026-03-14 CET

Status
- Follow-up remediation applied directly by orchestrator after Phase 12 review.

Accepted Work
- Backend, frontend, and testing agent deliveries remain accepted as the Phase 12 baseline after remediation.

Rejected / Missing Items
- The original backend snapshot logic treated `system_quantity` as stock-only instead of stock plus surplus.
- The original inventory-generated shortage `DraftGroup` used UTC date semantics rather than the location operational timezone.
- The original frontend mutation flows for Inventory Count degraded to toasts on network/server failures instead of following the global retry/error-state contract.
- The phase lacked the required `orchestrator.md` closeout record.
- The testing handoff overstated coverage for inactive-article exclusion and frozen snapshots before those regressions were actually covered in code.

Orchestrator Changes
- `backend/app/services/inventory_service.py`
- `backend/tests/test_inventory_count.py`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`
- `handoff/decisions/decision-log.md`
- `handoff/implementation/phase-12-inventory-count/orchestrator.md`

What Changed
- Inventory snapshots now use the full on-hand system quantity (`stock + surplus`) per article/batch, including surplus-only batch rows, so count discrepancies compare against the documented system total.
- Inventory-generated shortage draft groups now use the location operational timezone for `operational_date`, matching the Draft Entry / Approvals grouping semantics.
- Inventory line payloads now expose `decimal_display`, and the frontend uses that metadata for quantity formatting and input stepping.
- Inventory frontend mutation flows now retry once on network/server errors and escalate to the page-level error state after a second failure instead of staying on stale UI with a toast only.
- Regression tests now explicitly cover surplus-inclusive snapshots, inactive-article exclusion, frozen snapshots, and timezone-aware shortage grouping.

Verification
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q`
- `backend/venv/bin/pytest backend/tests -q`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Residual Notes
- `handoff/implementation/phase-12-inventory-count/testing.md` still contains the original agent wording that said some scenarios were covered before the orchestrator-added regressions existed. This orchestrator note is the canonical closeout record and supersedes that stale claim without rewriting the testing agent file.

Next Action
- Phase 12 can be treated as formally closed if the rerun verification remains green after these orchestrator fixes.

## Final Validation - 2026-03-14 CET

Status
- Verification rerun completed successfully after orchestrator remediation.

Validation Result
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q` -> `20 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `205 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Closeout Decision
- Phase 12 is formally closed.

Residual Risks
- No open blockers remain from the Phase 12 review.

Next Action
- Proceed to the next planned phase with the remediated Phase 12 baseline as the new reference state.
