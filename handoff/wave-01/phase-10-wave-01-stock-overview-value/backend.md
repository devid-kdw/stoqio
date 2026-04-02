# Backend Handoff — Wave 1 Phase 10: Stock Overview Value

## Status
Done

## Scope
Extended `GET /api/v1/reports/stock-overview` with per-item monetary value fields and a top-level `summary.warehouse_total_value`. No other endpoints or exports were changed.

## Docs Read
- `stoqio_docs/17_UI_REPORTS.md` § 3, § 10, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 3, § 15
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-REP-001, DEC-REP-002, DEC-BE-007)
- `handoff/implementation/phase-13-reports/orchestrator.md`
- `handoff/wave-01/phase-10-wave-01-stock-overview-value/orchestrator.md`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`
- `backend/app/models/receiving.py`
- `backend/app/models/article_supplier.py`

## Files Changed
- `backend/app/services/report_service.py`
  - Added `from app.models.receiving import Receiving` import.
  - Added `_VALUE_QUANT = Decimal("0.01")` constant.
  - Added `_resolve_unit_value_map(article_ids)` helper: queries Receiving for most-recent non-null `unit_price` per article (ordered `received_at DESC, id DESC`), then falls back to preferred `ArticleSupplier.last_price`, then `None`.
  - Extended `_serialize_stock_overview_item` signature with `unit_value: Decimal | None` param; computes `total_value = stock_total * unit_value` (null when `unit_value` is null, numeric zero when stock is zero and price exists); serializes both fields with `_VALUE_QUANT`.
  - Extended `get_stock_overview`: calls `_resolve_unit_value_map`, passes `unit_value` into serializer, accumulates `warehouse_total_value` in Decimal arithmetic across included items, adds `summary.warehouse_total_value` to the response.
- `backend/tests/test_reports.py`
  - Added `from app.models.receiving import Receiving` import.
  - Added module-scoped `reports_value_data` fixture: sets preferred supplier `last_price` for REP13-001 (15.00), adds preferred supplier link with `last_price=8.75` for REP13-003, seeds three Receiving rows for REP13-001 (oldest non-null 12.50 on 2026-01-01, newer non-null 20.00 on 2026-03-01, newest null on 2026-03-20).
  - Added `test_stock_overview_response_includes_value_fields_and_summary` (shape check, no price data dependency).
  - Added `test_stock_overview_value_receiving_price_wins_over_supplier_last_price`.
  - Added `test_stock_overview_value_null_receiving_does_not_erase_older_known_price`.
  - Added `test_stock_overview_value_preferred_supplier_fallback_when_no_receiving_price`.
  - Added `test_stock_overview_value_null_when_no_price_data`.
  - Added `test_stock_overview_value_total_value_uses_stock_not_surplus`.
  - Added `test_stock_overview_summary_warehouse_total_excludes_null_price_articles`.

## Commands Run
```
backend/venv/bin/pytest backend/tests/test_reports.py -q
```

## Tests
34 passed, 0 failed, 0 errors.

New value-contract tests cover:
- Item fields `unit_value` and `total_value` present in response shape.
- Receiving price (most recent non-null) wins over preferred supplier `last_price`.
- Newer null-priced Receiving row does not erase an older known price.
- Preferred supplier `last_price` used when no receiving price exists.
- Article with no price returns `unit_value=null`, `total_value=null`.
- `total_value` is computed from `stock` only (not `surplus` or `total_available`).
- `summary.warehouse_total_value` equals the sum of non-null item `total_value` values; null-price articles excluded.

## Open Issues / Risks
- Export endpoints (`/stock-overview/export`) are unchanged per contract. The XLSX/PDF headers do not include `unit_value` / `total_value` columns. If export scope is broadened later, the export function in `report_service.py` and the existing export tests will need updating.
- No new decisions were required; existing `DEC-BE-007` (null `unit_price` on ad-hoc receipts) is consistent with the filtering applied in `_resolve_unit_value_map`.

## Next Recommended Step
Delegate to the Frontend Agent to add the value columns and warehouse-total summary card to the Stock Overview tab using this contract.
