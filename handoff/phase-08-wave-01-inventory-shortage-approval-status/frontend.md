# Frontend Handoff — Wave 1 Phase 8 Inventory Shortage Approval Status

Reserved for frontend agent entries. Append only.

## Entry — 2026-03-24

### Status
Complete

### Scope
Extend `frontend/src/api/inventory.ts` with the `ShortageApprovalSummary` type and add
`shortage_drafts_summary?` to both `HistoryItem` and `CountDetail`. Add a
`ShortageApprovalBadge` component to `InventoryCountPage.tsx` and render it additively in
the history list Status cell. No changes to the active-count or detail-screen flows.

### Docs Read
- `stoqio_docs/16_UI_INVENTORY_COUNT.md` § 4, § 8, § 9
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/phase-12-inventory-count/orchestrator.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- `handoff/phase-08-wave-01-inventory-shortage-approval-status/backend.md`

### Backend Contract Match
Backend emits `shortage_drafts_summary: { total, approved, rejected, pending }` on both
`GET /api/v1/inventory` (history list items) and `GET /api/v1/inventory/{id}` (detail).
Contract matches the orchestrator spec exactly. No mismatch to log.

Linkage strategy (from backend.md): drafts are identified by `client_event_id LIKE
'inv-count-{count_id}-line-%'`. Frontend does not need to know this detail.

### Files Changed
- `frontend/src/api/inventory.ts` — added `ShortageApprovalSummary` interface;
  added optional `shortage_drafts_summary?: ShortageApprovalSummary` on `HistoryItem`
  and `CountDetail`
- `frontend/src/pages/inventory/InventoryCountPage.tsx` — imported
  `ShortageApprovalSummary`; added `ShortageApprovalBadge` pure component;
  rendered badge in `HistoryView` Status column `<Group>` for each history row

### Badge Logic (Croatian copy)
| Condition | Badge |
|-----------|-------|
| `total === 0` | (none) |
| `pending > 0` | 🟡 "Na čekanju (N)" |
| `pending === 0 && rejected === 0` | 🟢 "Odobreno" |
| `rejected > 0 && approved > 0` | 🔴 "Djelomično odbijeno" |
| `rejected > 0 && approved === 0` | 🔴 "Odbijeno" |

### Commands Run
- `cd frontend && npm run lint -- --max-warnings=0` → passed (0 warnings, 0 errors)
- `cd frontend && npm run build` → passed (`InventoryCountPage-*.js` 16.27 kB)

### Tests
Lint and TypeScript build (`tsc -b`) serve as static verification. No frontend unit tests
exist for this module (consistent with project baseline). Backend regression tests for
the new field were added and passed in the backend agent's entry (32 passed).

### Open Issues / Risks
- `shortage_drafts_summary` is typed as optional on `HistoryItem` and `CountDetail` as a
  defensive measure. If the backend guarantee that the field is always present for
  completed counts is later formalised, the type can be tightened without UI changes.

### Assumptions
- The backend always returns `shortage_drafts_summary` for completed count history items
  and detail payloads as of this wave. Optional typing is defensive, not because the
  field is missing.
- The `client_event_id` pattern used by the backend to link drafts to counts is stable
  per the backend agent's assumption (logged in backend.md).

### Next Recommended Step
- Testing agent can proceed to add any remaining backend regression coverage if not yet
  done.
- Orchestrator can proceed to formal closeout of Wave 1 Phase 8.

