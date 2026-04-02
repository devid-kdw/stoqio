# Backend Handoff — Phase 13 Wave 1: Article Statistics

- Date: 2026-03-26
- Agent: backend

---

## Status

COMPLETE. Item A (article statistics endpoint) implemented and all tests green.

---

## Scope

Item A only — `GET /api/v1/articles/{id}/stats`. Dark-mode work (Item B) not touched.

---

## Docs Read

- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/05_DATA_MODEL.md` § 16 (Transaction)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (first 80 lines)
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `backend/app/models/transaction.py`
- `backend/app/models/receiving.py`
- `backend/app/models/enums.py`
- `backend/app/models/article.py`

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/article_service.py` | Added `date, timedelta` to datetime imports; added `TxType` to enum imports; added `from app.models.receiving import Receiving`; implemented `get_article_stats()` function (after `list_article_transactions`) |
| `backend/app/api/articles/routes.py` | Added `GET /articles/<id>/stats` route with `@require_role("ADMIN", "MANAGER")` and `_parse_positive_int` for `period` param (default 90) |
| `backend/tests/test_articles.py` | Added `stats_article_data` module-scoped fixture; added `TestArticleStats` class with 5 tests |

---

## Commands Run

```
backend/venv/bin/pytest backend/tests/test_articles.py -q
# Result: 40 passed in 1.08s (35 pre-existing + 5 new)
```

---

## Tests

| Test | Result |
|------|--------|
| `TestArticleStats::test_200_response_shape` | PASSED |
| `TestArticleStats::test_article_with_no_transactions_returns_empty_histories` | PASSED |
| `TestArticleStats::test_period_30_excludes_older_seeded_rows` | PASSED |
| `TestArticleStats::test_invalid_period_returns_400` | PASSED |
| `TestArticleStats::test_viewer_gets_403` | PASSED |

---

## Endpoint Contract

```
GET /api/v1/articles/{id}/stats?period={N}
Roles: ADMIN, MANAGER
Query params:
  period  — positive integer (days); default 90; invalid → 400 VALIDATION_ERROR
Response 200:
{
  "article_id": int,
  "period_days": int,
  "outbound_by_week": [{"week": "YYYY-MM-DD", "quantity": float}, ...],
  "inbound_by_week":  [{"week": "YYYY-MM-DD", "quantity": float}, ...],
  "price_history":    [{"date": ISO str, "unit_price": float}, ...],
  "stock_history":    [{"date": ISO str, "balance": float}, ...]
}
Errors: 404 ARTICLE_NOT_FOUND, 403 FORBIDDEN, 400 VALIDATION_ERROR
```

---

## Implementation Decisions

### outbound_by_week
- Sources: `Transaction.tx_type IN (STOCK_CONSUMED, SURPLUS_CONSUMED)` only.
- Excludes: `PERSONAL_ISSUE`, `INVENTORY_ADJUSTMENT`, `OUTBOUND`, `STOCK_RECEIPT`, `WRITEOFF`.
- Quantities are stored as negative algebraic values; the bucket value is `abs(quantity)` (positive consumption figure).

### Weekly buckets
- Monday-based (`date.weekday() == 0` → Monday).
- Window: `monday_of(cutoff_date)` to `monday_of(today)`, inclusive.
- Zero-filled for all weeks in the window regardless of activity.
- ISO date strings (`YYYY-MM-DD`), oldest-first.

### price_history
- Source: `Receiving` rows with `unit_price IS NOT NULL`.
- Rows with `unit_price = NULL` are omitted entirely — no null-to-zero coercion.
- Ordered by `received_at ASC, id ASC` (oldest-first).

### stock_history rule (exact rule for frontend reference)
**Opening balance** = algebraic `SUM(Transaction.quantity)` for this `article_id` where `occurred_at < cutoff_dt` (all `tx_type` values included, no filtering by type).
**Running balance** = opening balance + cumulative `Transaction.quantity` for window rows, walked in `occurred_at ASC, id ASC` order.
One data point per transaction row: `{"date": occurred_at.isoformat(), "balance": running_balance}`.
This ensures the series is consistent with the actual Transaction audit trail regardless of tx_type.
Note: `stock_history` is returned but not consumed by the frontend in this wave.

---

## Open Issues / Risks

- `stock_history` opening balance includes all tx_types (including INVENTORY_ADJUSTMENT, WRITEOFF, PERSONAL_ISSUE) which is consistent with the audit trail but means the balance may diverge from the `Stock` table total if external corrections exist. Front-end should be advised if they want to reconcile these.
- The `period` window uses `date.today()` in UTC. If the server runs in a non-UTC timezone, `date.today()` could mismatch `occurred_at` comparisons (which use UTC datetimes). This is acceptable for v1 since the server is expected to run in UTC.

---

## Next Recommended Step

Frontend agent: implement the article stats chart component consuming `GET /api/v1/articles/{id}/stats`. The `stock_history` field is present in the response but does not need to be rendered in this wave.
