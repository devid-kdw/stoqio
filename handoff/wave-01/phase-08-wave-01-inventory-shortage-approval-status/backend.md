# Phase 08 Wave 01 — Inventory Shortage Approval Status — Backend

## Entry — 2026-03-24

### Status
Complete

### Scope
Add `shortage_drafts_summary` to `GET /api/v1/inventory` (history list) and `GET /api/v1/inventory/{id}` (detail) endpoints for completed inventory counts.

### Docs Read
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8, § 9
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 11, § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-INV-001 through DEC-INV-007)
- `handoff/implementation/phase-12-inventory-count/orchestrator.md`
- `handoff/wave-01/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`

### Files Changed
- `backend/app/services/inventory_service.py` — added `_get_shortage_drafts_summary()` helper; extended `list_counts()` and `get_count_detail()` to include `shortage_drafts_summary`
- `backend/tests/test_inventory_count.py` — added `DraftStatus` import + 4 new tests for zero-shortage, mixed-status, rejected-state, and detail coverage

### Commands Run
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py -q` → 32 passed

### Tests
| Test | Covers |
|------|--------|
| `test_shortage_drafts_summary_no_shortages` | Zero-shortage count → all-zero summary |
| `test_shortage_drafts_summary_mixed_statuses` | Approve one draft → approved ≥ 1, total invariant holds |
| `test_shortage_drafts_summary_rejected_state` | Reject all drafts → rejected = total, pending = 0 |
| `test_shortage_drafts_summary_in_detail` | Detail endpoint includes `shortage_drafts_summary` with correct types and invariant |

### Linkage Strategy
Shortage drafts are linked to a count via the deterministic `client_event_id` pattern emitted by `complete_count(...)`: `inv-count-{count_id}-line-{line_id}`. The helper queries `Draft` rows with `draft_type = INVENTORY_SHORTAGE` and `client_event_id LIKE 'inv-count-{count_id}-line-%'`. No schema change, migration, or FK was introduced.

### Summary Shape
```json
{
  "total": int,
  "approved": int,
  "rejected": int,
  "pending": int
}
```

Status mapping: `Draft.status=DRAFT` → pending, `APPROVED` → approved, `REJECTED` → rejected.

### Open Issues / Risks
- None. No schema changes introduced.

### Assumptions
- The `client_event_id` pattern `inv-count-{count_id}-line-{line_id}` is stable and will not be changed by other agents without coordination.

### Next Recommended Step
- Frontend agent can proceed to render shortage approval-status indicators on the history list using `shortage_drafts_summary`.
- Testing agent can proceed to add any additional regression coverage.
