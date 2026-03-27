# Frontend Handoff — Wave 2 Phase 1: DraftGroup PARTIAL Persistence

## Status

**COMPLETE (audit-only)** — No code changes required. All done criteria met through code-path verification and successful lint/build.

---

## Scope

Audit `frontend/src/api/approvals.ts`, `ApprovalsPage.tsx`, and `DraftGroupCard.tsx` to confirm `PARTIAL` is treated as a first-class approval-group status in all type definitions, badge rendering, and tab-segmentation logic. Verify no status-mapping path silently narrows to a 3-status assumption.

---

## Docs Read

- `stoqio_docs/10_UI_APPROVALS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-APP-001)
- `handoff/phase-06-approvals/orchestrator.md`
- `handoff/phase-06-approvals-followup/orchestrator.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/backend.md`
- `frontend/src/api/approvals.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

---

## Files Changed

None. All three files already satisfy the locked contract. No changes required.

---

## Audit Results

### `frontend/src/api/approvals.ts`

- `ApprovalsDraftGroup.status`: `'PENDING' | 'APPROVED' | 'PARTIAL' | 'REJECTED' | string` — PARTIAL present ✓
- `ApprovalsAggregatedRow.status`: `'PENDING' | 'APPROVED' | 'PARTIAL' | 'REJECTED' | string` — PARTIAL present ✓
- `getPending()` calls `/approvals?status=pending`; `getHistory()` calls `/approvals?status=history` — segmentation is endpoint-driven, not client-side ✓
- No code in this file assumes only 3 statuses ✓

### `frontend/src/pages/approvals/ApprovalsPage.tsx`

- Pending tab populates exclusively from `approvalsApi.getPending()` ✓
- History tab populates exclusively from `approvalsApi.getHistory()` ✓
- No client-side status filtering: the page renders whatever the backend returns per endpoint ✓
- Tabs switch by string value, no status enum dependency ✓

### `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

- **Group header badges** (lines 338–341): All 4 statuses handled explicitly:
  - `PENDING` → yellow badge ✓
  - `APPROVED` → green badge ✓
  - `REJECTED` → red badge ✓
  - `PARTIAL` → orange badge ✓
- **Row-level status badge** (lines 453–458): Color ternary chain defaults unknown/PARTIAL to `'orange'` ✓
- **`handleGroupResolution`** (lines 157–166): Triggers `onGroupResolved()` when `nextDetail.rows?.some(row => row.status === 'PENDING')` is false. For a PARTIAL group (all rows resolved to APPROVED or REJECTED), this correctly fires and refreshes the pending list ✓
- **Row background dimming** (line 403): `row.status !== 'PENDING' && !isHistory` grays out already-resolved rows within a partially resolved pending group — correct behavior ✓
- **Action buttons** (line 465): Actions shown only when `row.status === 'PENDING'` — resolved rows in a partially resolved group show no actions ✓
- No path assumes only 3 group statuses ✓

---

## Commands Run

```bash
cd frontend && npm run lint -- --max-warnings=0
# → exit 0, 0 warnings, 0 errors

cd frontend && npm run build
# → ✓ built in 2.59s, 0 errors, 0 type errors
```

---

## Tests

No frontend unit/integration tests exist for approvals in this repo. Lint and build are the verification gates per the orchestrator prompt. Both pass clean.

---

## Open Issues / Risks

- The `| string` escape at the end of both status unions is a pre-existing pattern. It prevents exhaustive-switch type errors for unknown future statuses but does not regress PARTIAL handling — PARTIAL is still explicitly listed and matched first.
- No frontend-specific risks introduced by this phase.

---

## Assumptions

- Backend handoff (backend.md) confirms history segmentation is now driven by the authoritative persisted `DraftGroup.status`. The frontend does not need to replicate this logic — it trusts the backend endpoint segmentation.
- `PARTIAL` will never appear in `Draft.status` (only `DraftGroup.status`), consistent with backend assumptions. The frontend only renders row-level status strings as-is without mapping them to group statuses.

---

## Next Recommended Step

- Testing agent: baseline coverage for PARTIAL persistence exists in `TestPartialStatusPersistence` (backend.md). No additional frontend-specific test tasks identified.
- Orchestrator: mark frontend done criteria as met; proceed to testing agent review and final orchestrator validation note.
