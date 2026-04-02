# Testing Handoff — Phase 13 Wave 1: Article Statistics & Dark Mode

- Date: 2026-03-26
- Agent: testing

---

## Status

COMPLETE. Backend test coverage for the new article-stats contract is locked and verified. Frontend dark-mode verification is noted as manual.

---

## Scope

- Locked backend coverage for `GET /api/v1/articles/{id}/stats`.
- Ensure stock_history assertions for period filtering, structure, and ordering.
- Note frontend test status for dark-mode.

---

## Docs Read

- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/05_DATA_MODEL.md` § 16
- `handoff/README.md`
- `handoff/wave-01/phase-13-wave-01-article-stats-dark-mode/backend.md` (backend handoff)
- `backend/tests/test_articles.py`

---

## Files Changed

| File | Change |
|------|--------|
| `backend/tests/test_articles.py` | Extended `TestArticleStats::test_period_30_excludes_older_seeded_rows` with assertions validating `stock_history` structure, ordering, and period filtering (verifying opening balance fold for out-of-period rows vs literal row values for in-period rows). |

---

## Commands Run

```bash
backend/venv/bin/pytest backend/tests/test_articles.py -q
# Result: 40 passed in 1.07s

backend/venv/bin/pytest backend/tests -q
# Result: 343 passed in 18.09s
```

---

## Tests

| Test | Result |
|------|--------|
| `TestArticleStats::test_200_response_shape` | PASSED |
| `TestArticleStats::test_article_with_no_transactions_returns_empty_histories` | PASSED |
| `TestArticleStats::test_period_30_excludes_older_seeded_rows` | PASSED (Extended for `stock_history`) |
| `TestArticleStats::test_invalid_period_returns_400` | PASSED |
| `TestArticleStats::test_viewer_gets_403` | PASSED |

Note: Frontend dark-mode and browser-based verification remains manual-only, as no dedicated UI automation (e.g. Playwright) is currently configured in this workflow.

---

## Open Issues / Risks

- None backend-wise.
- Frontend regression relies purely on manual checks for dark-mode toggle behavior and stat chart rendering.

---

## Next Recommended Step

Return to orchestrator / user for final validation and wave closure.
