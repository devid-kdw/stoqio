---
agent: backend
date: 2026-04-11
phase: wave-09/phase-04-wave-09-reports-statistics-and-price-movement
---

## Status

Done — all tests pass (67 passed, 0 failed).

## Scope

W9-F-005 — warehouse-wide article price-movement report endpoint  
W9-F-009 — reorder-zone drilldown endpoint (backend support only)  
W9-F-010 — movement statistics: Croatian note + optional article_id/category filters

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-04-wave-09-reports-statistics-and-price-movement/orchestrator.md`
- `backend/app/api/reports/routes.py`
- `backend/app/services/report_service.py`
- `backend/tests/test_reports.py`
- `stoqio_docs/17_UI_REPORTS.md`
- `backend/app/models/receiving.py`
- `backend/app/models/article.py`
- `backend/app/models/category.py`
- `backend/app/models/transaction.py`

## Files Changed

### `backend/app/services/report_service.py`

- **`_MOVEMENT_NOTE`** — updated from English to Croatian (W9-F-010).
- **`get_movement_statistics(range_key, *, article_id, category)`** — extended with two new optional keyword-only parameters:
  - `article_id`: validates as positive integer, verifies article existence (404 if not found), then filters `Transaction.article_id`.
  - `category`: looks up `Category` by key (404 if not found), collects all article IDs in that category (active + inactive for full history), then filters. Empty category returns zero-filled buckets immediately.
  - Default behavior (no filter) is unchanged — whole-warehouse mode.
- **`_build_price_movement_item(article, latest_price, previous_price, last_change_date)`** — new helper that constructs a single price-movement item dict.  Date serialisation uses `str(last_change_date)[:10]` to handle both `date` and `datetime` values returned by SQLite.
- **`get_price_movement_statistics()`** — new function (W9-F-005). Fetches all active articles and their Receiving rows (non-null `unit_price`) in one chronological query. Walks rows linearly to detect per-article price changes. Groups results into: changed (sorted by `last_change_date DESC`), unchanged, no-price. Returns `{items, total}`.
- **`get_reorder_drilldown_statistics(status)`** — new function (W9-F-009 backend support). Validates `status` ∈ {RED, YELLOW, NORMAL} (400 otherwise). Returns active articles matching the requested reorder zone with stock/surplus/threshold/uom fields.

### `backend/app/api/reports/routes.py`

- **`get_movement_statistics`** — now passes `article_id` and `category` from query params to the service.
- **`get_price_movement_statistics`** — new route `GET /api/v1/reports/statistics/price-movement`, `ADMIN` + `MANAGER`.
- **`get_reorder_drilldown_statistics`** — new route `GET /api/v1/reports/statistics/reorder-drilldown?status=RED|YELLOW|NORMAL`, `ADMIN` + `MANAGER`.

### `backend/tests/test_reports.py`

- Updated existing `test_movement_statistics_return_seeded_month_delta` note assertion to Croatian.
- Updated RBAC access test paths list to include `price-movement` and `reorder-drilldown?status=NORMAL`.
- Added 15 new tests:
  - `test_movement_statistics_note_is_croatian`
  - `test_movement_statistics_filter_by_article_id` — asserts March bucket exact values (inbound 50.0, outbound 16.0) for REP13-001.
  - `test_movement_statistics_filter_by_category` — asserts March bucket values for `rep13_general` (inbound 1260.0, outbound 1016.0).
  - `test_movement_statistics_unknown_article_id_returns_404`
  - `test_movement_statistics_unknown_category_returns_404`
  - `test_movement_statistics_invalid_article_id_returns_400`
  - `test_price_movement_statistics_manager_can_access`
  - `test_price_movement_statistics_article_with_change_leads_list` — REP13-001 must appear first with latest=20.0, previous=12.5, delta=7.5, delta_pct=60.0, last_change_date=2026-03-01.
  - `test_price_movement_statistics_unchanged_articles_follow_changed`
  - `test_price_movement_statistics_item_shape`
  - `test_reorder_drilldown_returns_red_articles` — REP13-002 in result.
  - `test_reorder_drilldown_returns_yellow_articles` — REP13-001 in result.
  - `test_reorder_drilldown_item_shape`
  - `test_reorder_drilldown_invalid_status_returns_400`
  - `test_reorder_drilldown_missing_status_returns_400`

### `stoqio_docs/17_UI_REPORTS.md`

- Section 6.4: updated note copy to Croatian, added filter documentation (article + category).
- Section 6.5: updated reorder-zone click behavior (opens collapsible drilldown block within Statistics; no tab switch).
- Section 6.6: added new Section E — Price Movement spec (columns, sort logic, visibility).
- Section 6.8: added layout behaviour note (collapsed by default, no tab switch for drilldown).
- Section 10: added all Statistics endpoints to the API table.

## Commands Run

```
backend/venv/bin/python -m pytest backend/tests/test_reports.py -q --tb=short
```

Result: **67 passed in 0.94s**

## Tests

| Requirement | Test | Result |
|-------------|------|--------|
| Movement default warehouse mode still works | `test_movement_statistics_return_seeded_month_delta` | pass |
| Movement note is Croatian | `test_movement_statistics_note_is_croatian` | pass |
| Movement filters correctly by article | `test_movement_statistics_filter_by_article_id` | pass |
| Movement filters correctly by category | `test_movement_statistics_filter_by_category` | pass |
| Price-movement sorts by most recent actual change first | `test_price_movement_statistics_article_with_change_leads_list` | pass |
| Unchanged/no-price articles remain included lower in list | `test_price_movement_statistics_unchanged_articles_follow_changed` | pass |
| MANAGER can access new read endpoints | RBAC test paths + `test_price_movement_statistics_manager_can_access` | pass |
| Reorder-drilldown status filtering and auth | `test_reorder_drilldown_returns_red_articles`, `test_reorder_drilldown_returns_yellow_articles`, `test_reorder_drilldown_item_shape`, `test_reorder_drilldown_invalid_status_returns_400`, `test_reorder_drilldown_missing_status_returns_400` | pass |

## Open Issues / Risks

- **Date serialisation**: SQLite returns `DateTime(timezone=True)` columns as naive Python `datetime` objects in tests. The `_build_price_movement_item` helper uses `str(last_change_date)[:10]` to normalise to an ISO date string safely. This is intentional and robust across all SQLAlchemy backends.
- **Category movement filter includes inactive articles**: When filtering by category, all articles (active + inactive) in the category are included in the article ID set. This gives complete historical movement data. If the product wants only active articles, this is a one-line change.
- **Price-movement uses Receiving only**: The price-movement report derives prices exclusively from `Receiving.unit_price`. Articles with prices only in `ArticleSupplier.last_price` or `initial_average_price` appear as "no-price" rows. This is consistent with the spec: "last known price from receiving records".

## Next Recommended Step

Frontend worker implements:
- Statistics subsection collapse (W9-F-008)
- Movement chart Croatian note + article/category filter controls (W9-F-010)
- Reorder drilldown inline block using `GET /api/v1/reports/statistics/reorder-drilldown?status={}` (W9-F-009)
- New Price Movement section using `GET /api/v1/reports/statistics/price-movement` (W9-F-005)
