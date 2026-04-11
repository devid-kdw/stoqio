# Wave 9 Phase 3 — Frontend Handoff

Date: 2026-04-11

## Status

Complete. Surplus removed, ordered/price fields added, role-aware card rendering in place. Lint and build pass.

## Scope

- W9-F-007: Identifier result cards no longer show `Višak`.
- ADMIN/MANAGER now see: exact stock quantity, `Naručeno` (boolean), `Naručena količina`, `Zadnja nabavna cijena`.
- WAREHOUSE_STAFF/VIEWER now see: `Dostupnost` (boolean), `Naručeno` (boolean) — no quantities, no price.

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-03-wave-09-identifier-order-visibility/orchestrator.md`
- `frontend/src/api/identifier.ts`
- `frontend/src/pages/identifier/IdentifierPage.tsx`
- `frontend/src/pages/identifier/identifierUtils.ts`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/14_UI_IDENTIFIER.md`

## Files Changed

### `frontend/src/api/identifier.ts`

- Removed `surplus: number` from `IdentifierSearchQuantityItem`.
- Added `is_ordered: boolean`, `ordered_quantity: number`, `latest_purchase_price: number | null`
  to `IdentifierSearchQuantityItem` (ADMIN/MANAGER shape).
- Added `is_ordered: boolean` to `IdentifierSearchAvailabilityItem` (WAREHOUSE_STAFF/VIEWER shape).
- Added doc comments on each interface to clarify which role group each variant serves.

### `frontend/src/pages/identifier/identifierUtils.ts`

- Added `formatIdentifierPrice(price: number | null | undefined): string`.
  Uses `Intl.NumberFormat` with 2–4 decimal places and the active locale.
  Returns `'—'` for null/undefined (consistent with other Identifier field rendering).

### `frontend/src/pages/identifier/IdentifierPage.tsx`

- Imported `formatIdentifierPrice` from `identifierUtils`.
- Replaced the quantity card's `Višak` field with the new role-aware layout:
  - **ADMIN/MANAGER card** (quantity item): `Kategorija`, `JM`, `Na stanju`, `Naručeno`, `Naručena količina`, `Zadnja nabavna cijena` — 6 fields wrap to two rows of 4 on the `lg` grid breakpoint.
  - **WAREHOUSE_STAFF/VIEWER card** (availability item): `Kategorija`, `JM`, `Dostupnost`, `Naručeno` — 4 fields in one row on `lg`.
- Alias badge and alias footer copy are unchanged.

### Docs

- `stoqio_docs/14_UI_IDENTIFIER.md` — already fully updated during Wave 9 intake (sections 4, 9, 10).
  No further changes needed.
- `stoqio_docs/03_RBAC.md` — Identifier rows for exact quantity/ordered visibility already reflect
  the new role matrix (updated by parallel backend phase). No change needed here.

## Commands Run

```
cd frontend && npm run lint    → clean
cd frontend && npm run build   → clean (TypeScript + Vite, 29 chunks, ✓ built in 3.87s)
```

## Tests

- No new unit tests added. The type and rendering changes are structural; they will be covered
  by the integration tests the testing worker is responsible for.
- TypeScript compiler validated all new type usages at build time — no type errors.

## Open Issues / Risks

- The frontend discriminates between quantity and availability items via `'in_stock' in item`
  (function `isAvailabilityOnlyResult`). This relies on the backend never including `in_stock` in
  the ADMIN/MANAGER response shape. The parallel backend worker must not add `in_stock` to the
  quantity response.
- `latest_purchase_price` is rendered as a plain number (e.g. `4.3000`). No currency symbol is
  shown — consistent with the rest of the app (no currency symbol is established in the codebase).
  If a currency symbol should be added globally, that is a separate task.

## Next Recommended Step

Orchestrator validates this phase against the backend worker's delivery: confirm the new response
shapes exactly match `IdentifierSearchQuantityItem` and `IdentifierSearchAvailabilityItem` before
marking W9-F-007 complete.
