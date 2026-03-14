# Phase 12 — Inventory Count Frontend

## Status

COMPLETE

---

## Scope

Implemented the full Inventory Count UI for `/inventory`:
- `frontend/src/api/inventory.ts` — all 6 API methods with TypeScript types
- `frontend/src/pages/inventory/InventoryCountPage.tsx` — full page with 3 internal sub-components
- `frontend/src/routes.tsx` — replaced placeholder with lazy-loaded `InventoryCountPage`

---

## Docs Read

- `stoqio_docs/16_UI_INVENTORY_COUNT.md` — full
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` §4, §5
- `handoff/README.md`
- `memory/MEMORY.md`
- `handoff/phase-12-inventory-count/backend.md`
- `handoff/phase-11-employees/frontend.md` — UI patterns reference

---

## Files Changed

| File | Action |
|------|--------|
| `frontend/src/api/inventory.ts` | Created — 6 typed API methods + all response types |
| `frontend/src/pages/inventory/InventoryCountPage.tsx` | Created — full page with HistoryView, ActiveCountView, CompletedDetailView |
| `frontend/src/routes.tsx` | Updated — lazy import + Suspense for `/inventory` |

---

## Commands Run

```
cd frontend && npm run lint -- --max-warnings=0   # 0 errors, 0 warnings
cd frontend && npm run build                       # ✓ built in 1.98s
```

---

## Tests

No frontend unit tests (consistent with project baseline). Lint + build used as verification.

---

## Feature Summary

### `api/inventory.ts`
- `getActive()` — handles the `{"active": null}` / active-count-object duality from DEC-INV-003
- `history(page, perPage)` — paginated COMPLETED counts
- `start()` — POST /inventory (returns void; caller fetches active separately)
- `detail(id)` — read-only count with full lines and summary
- `updateLine(countId, lineId, countedQuantity)` — PATCH counted qty
- `complete(countId)` — POST complete, returns `{ id }`

### `InventoryCountPage.tsx` — view state machine
- On mount: check active count → if IN_PROGRESS show `ActiveCountView`, else load history → show `HistoryView`
- Initial load uses `FullPageState` (loading/error); transitions use toasts for inline errors
- `runWithRetry()` used on all network calls
- Croatian copy throughout

### `HistoryView`
- "Pokreni novu inventuru" button with loading state
- Inline `Alert` for 400 conflict error (active count already in progress)
- History table: Datum, Pokrenuo, Broj stavki, Broj odstupanja, Status
- Empty state: "Nema evidentiranih inventura."
- Pagination (50/page)
- Row click → load detail → CompletedDetailView

### `ActiveCountView`
- Header: started by, started at, live progress counter (`X / N prebrojano`)
- `Tooltip`-wrapped "Završi inventuru" button (disabled + pointerEvents:none until all counted)
- Tooltip text: "Sve stavke moraju biti prebrojane prije završetka."
- Filter checkboxes: "Samo odstupanja" / "Samo neprebrojano" — client-side, no re-fetch
- Lines table with `NumberInput` (hideControls, size=xs, w=110) per row
- Real-time difference calculation: updated on every keystroke from local edit state
- Row tinting: neutral (uncounted), green (no diff), blue (surplus), yellow (shortage)
- Autosave on blur via PATCH; row-level saving spinner in rightSection
- On blur: revert to saved value if input is empty/invalid/unchanged
- Negative values rejected with toast
- Backend validation errors (e.g. integer UOM) shown as toast; value reverted
- Confirmation modal before complete (spec text verbatim)
- On complete: fetch `GET /inventory/{id}` → CompletedDetailView

### `CompletedDetailView`
- "Natrag" button → triggers `initPage()` (reloads active/history)
- Metadata header: started by, started at, completed at
- Summary widget (SimpleGrid 4-col): total, no_change (green), surplus_added (blue), shortage_drafts_created (yellow)
- Resolution filter Select: All / NO_CHANGE / SURPLUS_ADDED / SHORTAGE_DRAFT_CREATED (client-side)
- Read-only lines table with Resolution column (`ResolutionBadge` component)
- Row tinting by resolution: green / blue / yellow

### RBAC
- Route protected by `ProtectedRoute allowedRoles={['ADMIN']}` (unchanged from placeholder)
- No frontend RBAC logic needed; backend enforces ADMIN-only on all 6 endpoints

---

## Open Issues / Risks

- No UOM decimal metadata on lines (the `InventoryCountLine` type doesn't include `decimal_display`). Client allows decimal input for all UOMs; integer-only enforcement is handled by the backend (returns 400 with message if violated), shown as toast + value reverted. This is acceptable per spec.
- The `start()` method does two network calls (POST then GET active). If the GET active fails after a successful POST, the user sees an error toast but the count was created. On retry, `initPage()` will find the active count via GET active and show it correctly.
- No unit tests (consistent with project baseline).

---

## Next Recommended Step

Testing agent: validate full end-to-end flow — start count, fill all lines, complete, verify resolution display, verify history row opens completed detail.
