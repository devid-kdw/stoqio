# Phase 12 — Inventory Count Backend Handoff

## Status

COMPLETE. All 17 inventory count tests pass. Full suite: 202 passed, 0 failed.

---

## Scope

Implemented the complete Inventory Count backend:
- Start count (snapshot active articles)
- List count history (paginated, newest first)
- Get active count with lines
- Get count detail (read-only, completed counts)
- Update counted quantity per line (with UOM validation)
- Complete count (automatic discrepancy processing: NO_CHANGE / SURPLUS_ADDED / SHORTAGE_DRAFT_CREATED)

---

## Docs Read

- `stoqio_docs/16_UI_INVENTORY_COUNT.md` — full
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 4 (Stock & Surplus), § 5 (Draft workflow)
- `stoqio_docs/05_DATA_MODEL.md` §§ 8–11, 16–18 (Stock, Surplus, Draft, DraftGroup, Transaction, InventoryCount, InventoryCountLine)
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `memory/MEMORY.md`
- `handoff/decisions/decision-log.md`

---

## Files Changed

| File | Action |
|------|--------|
| `backend/app/services/inventory_service.py` | Created — full service layer |
| `backend/app/api/inventory_count/__init__.py` | Created — blueprint package |
| `backend/app/api/inventory_count/routes.py` | Created — 6 endpoints |
| `backend/app/api/__init__.py` | Updated — registered inventory_bp |
| `backend/tests/test_inventory_count.py` | Created — 17 integration tests |

---

## Commands Run

```
backend/venv/bin/pytest backend/tests/test_inventory_count.py -q
# 17 passed in 0.47s

backend/venv/bin/pytest backend/tests -q
# 202 passed in 7.83s
```

---

## Tests

17 tests covering:
- RBAC: non-admin rejected (403)
- History empty before any count
- Active returns `{"active": null}` when none exists
- Start count: creates IN_PROGRESS count, snapshots all active articles
- Second start blocked while one is IN_PROGRESS (400, COUNT_IN_PROGRESS)
- Active count returned with all lines, correct system_quantity values
- Update line: negative qty rejected, non-integer for integer UOM rejected, decimal for decimal UOM accepted
- Update all lines: sets counts to trigger each resolution path
- Complete count: success with SURPLUS_ADDED / SHORTAGE_DRAFT_CREATED / NO_CHANGE summary
- Surplus row created + INVENTORY_ADJUSTMENT Transaction written
- Draft + DraftGroup created for shortages (IZL-#### numbering)
- Line resolutions set correctly on completion
- History shows completed count
- Active returns null after completion
- Count detail endpoint: correct summary + all lines with resolutions
- Update on completed count rejected (400, COUNT_NOT_IN_PROGRESS)
- Complete with uncounted lines rejected (400, UNCOUNTED_LINES)
- 404 for non-existent count

---

## Decisions Made

### DEC-INV-001: Shortage Draft Grouping

- **Date**: 2026-03-14
- **Decision**: One `DraftGroup` per count completion (all shortage drafts for the count share one group). Reuses the `IZL-####` sequence from the Drafts module. `operational_date` = UTC date of completion.
- **Why**: Compatible with existing Approvals module grouping. Inventory shortages appear as a single pending group in Approvals, which matches the UX intent (admin reviews all shortages from one count together).
- **Impact**: Backend only. Frontend Approvals screen needs no changes — existing approval flow handles `INVENTORY_SHORTAGE` draft_type.

### DEC-INV-002: Batch article with no stock → one NULL-batch line

- **Decision**: If a batch-tracked article has no stock rows at snapshot time, one line is created with `batch_id=NULL` and `system_quantity=0`. This ensures all active articles appear in every count.
- **Why**: Spec says "Include active articles even if quantity is zero." Without this, a batch article that has never had receiving would be silently excluded.
- **Impact**: Backend snapshot logic only.

### DEC-INV-003: GET /api/v1/inventory/active — no active count returns 200 `{"active": null}`

- **Decision**: Returns HTTP 200 with `{"active": null}` rather than 404 when no count is in progress.
- **Why**: Frontend determines screen layout based on presence/absence of an active count. A 200 with a null sentinel is simpler for the frontend to handle than a 404 branch.
- **Impact**: Frontend agent must check `response.active !== null` rather than HTTP status.

---

## Open Issues / Risks

- **Batch article snapshot with zero-quantity stock rows**: If a batch article has stock rows with `quantity=0` (but they exist), those rows are included in the snapshot. This is correct behaviour — the item was received and has been depleted; it should still be counted.
- **Race condition on count completion**: If two admins complete the same count concurrently, both would try to commit. The `status` check at start of `complete_count` mitigates this for the second call, but no row-level lock is applied. Low risk for a single-user WMS.
- **Surplus accumulation**: `complete_count` accumulates into existing Surplus rows (does not reset them). This matches the domain rule that surplus is a cumulative pool consumed first.

---

## Next Recommended Step

Frontend agent: implement `frontend/src/pages/inventory/` and connect to all 6 endpoints per `stoqio_docs/16_UI_INVENTORY_COUNT.md`.
