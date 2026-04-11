# Backend Handoff — Wave 9 Phase 3: Identifier Order Visibility

**Date**: 2026-04-11
**Finding**: W9-F-007

## Status

✅ Complete — all backend changes implemented and verified.

## Scope

Implemented role-sensitive Identifier serialization per W9-F-007:

1. **Removed** `surplus` from all Identifier responses.
2. **Added** order visibility fields: `is_ordered`, `ordered_quantity`, `latest_purchase_price`.
3. **Role gating**:
   - `ADMIN` and `MANAGER`: `stock` (exact), `is_ordered`, `ordered_quantity`, `latest_purchase_price`
   - `WAREHOUSE_STAFF` and `VIEWER`: `in_stock` (boolean), `is_ordered` (boolean only — no quantity or price)
4. **Ordered quantity definition**: sum of `(ordered_qty − received_qty)` across all OPEN `OrderLine` rows on OPEN `Order` rows for the article.
5. **Latest purchase price hierarchy** (documented in `14_UI_IDENTIFIER.md`):
   - Tier 1: Most recent `Receiving.unit_price` by `received_at DESC`
   - Tier 2: Preferred `ArticleSupplier.last_price`
   - Tier 3: Any `ArticleSupplier.last_price` by `last_ordered_at DESC`
   - Fallback: `null`

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-03-wave-09-identifier-order-visibility/orchestrator.md`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_aliases.py`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/14_UI_IDENTIFIER.md`
- `backend/app/models/order.py`
- `backend/app/models/order_line.py`
- `backend/app/models/enums.py`
- `backend/app/models/receiving.py`
- `backend/app/models/article_supplier.py`

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/article_service.py` | Added `_build_identifier_ordered_map`, `_build_identifier_latest_purchase_price_map`; rewrote `_serialize_identifier_item` with new role contract; updated `search_identifier_articles` to compute and pass ordered/price data; added Order/OrderLine/enum imports |
| `backend/tests/test_articles.py` | Updated two existing Identifier tests to match new contract; added `identifier_order_data` fixture and `TestIdentifierOrderVisibility` class with 7 new tests; added Order/OrderLine imports |
| `stoqio_docs/14_UI_IDENTIFIER.md` | Rewrote section 4 (role matrix), updated search result card fields, updated response examples, added edge case for WAREHOUSE_STAFF, documented ordered quantity definition and price hierarchy |
| `stoqio_docs/03_RBAC.md` | Added two Identifier field-level visibility rows to the permissions matrix |

## Commands Run

```
backend/venv/bin/python -m pytest backend/tests/test_articles.py -q --tb=short
→ 59 passed

backend/venv/bin/python -m pytest backend/tests/test_aliases.py -q --tb=short
→ 8 passed
```

## Tests

### Updated existing tests

| Test | Change |
|------|--------|
| `test_identifier_search_returns_alias_match_with_boolean_stock_for_staff` | Renamed from `..._exact_quantities`; now asserts `in_stock`, `is_ordered`, absence of `stock`/`surplus`/`ordered_quantity`/`latest_purchase_price` |
| `test_identifier_search_viewer_receives_in_stock_and_is_ordered_only` | Renamed from `..._in_stock_only`; now also asserts `is_ordered` and absence of qty/price fields |

### New tests in `TestIdentifierOrderVisibility`

| Test | Coverage |
|------|----------|
| `test_admin_sees_exact_stock_ordered_qty_and_purchase_price` | ADMIN gets `stock`, `is_ordered`, `ordered_quantity`, `latest_purchase_price`; no `surplus`, no `in_stock` |
| `test_manager_sees_same_shape_as_admin` | MANAGER gets identical shape to ADMIN |
| `test_warehouse_staff_sees_boolean_only` | WAREHOUSE_STAFF gets `in_stock` + `is_ordered` only; no exact quantities or prices |
| `test_viewer_sees_boolean_only` | VIEWER gets same boolean-only shape as WAREHOUSE_STAFF |
| `test_ordered_quantity_sums_across_multiple_open_orders` | Verifies summing across two OPEN orders (15 + 10 = 25); closed order with 99 qty is excluded |
| `test_latest_purchase_price_from_receiving` | Verifies price comes from most recent Receiving (4.30 > 4.20) |
| `test_alias_match_still_works_with_new_contract` | Alias search resolves correctly and returns ADMIN shape fields |

## Open Issues / Risks

- **WAREHOUSE_STAFF loses exact stock in Identifier.** This is an explicit product-direction override confirmed in W9-F-007 user feedback. Previous baseline gave WAREHOUSE_STAFF exact quantities.
- **Price hierarchy per-article loop.** The `_build_identifier_latest_purchase_price_map` function queries per article-id in a loop (not a single batched query). For typical Identifier result sets (<20 articles) this is negligible, but could be optimized with a window-function CTE if result sets grow large.
- **Frontend must adapt to new response shape.** The frontend worker should update `IdentifierPage.tsx` and `identifierUtils.ts` to stop rendering `Višak`, start rendering `is_ordered` / `ordered_quantity` / `latest_purchase_price`, and gate display by role.

## Next Recommended Step

Frontend worker implements the Identifier card UI changes to match the new backend contract.
