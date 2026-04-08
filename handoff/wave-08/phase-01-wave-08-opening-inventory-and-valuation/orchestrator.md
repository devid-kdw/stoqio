## Phase Summary

Phase
- Wave 8 - Phase 1 - Backend Opening Inventory and Valuation

Objective
- Remediate backend behavior for W8-F-001, W8-F-003, and W8-F-004:
  opening inventory must initialize stock instead of surplus, opening inventory must support
  existing batch entry for batch-tracked articles, and article setup must persist a starting
  average purchase price that can seed `Stock.average_price`.

Source Docs
- `handoff/README.md`
- `handoff/wave-08/README.md`
- `handoff/Findings/wave-08-user-feedback.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-008`, `DEC-PRICE-001`, `DEC-PRICE-002`)
- `backend/app/services/inventory_service.py`
- `backend/app/services/article_service.py`
- `backend/app/services/receiving_service.py`
- `backend/app/services/report_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/models/article.py`
- `backend/app/models/batch.py`
- `backend/app/models/stock.py`
- `backend/app/models/surplus.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/enums.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_reports.py`
- `stoqio_docs/05_DATA_MODEL.md`

Current Repo Reality
- `InventoryCount.type` supports `REGULAR | OPENING`, but opening completion currently uses the
  regular surplus/shortage path.
- `start_count(OPENING)` snapshots active articles. For a batch-tracked article with no existing
  stock rows, it creates one placeholder line with `batch_id = NULL`.
- There is no endpoint for adding real existing batch rows during opening inventory.
- `Stock.average_price` is the canonical weighted-average field for actual stock buckets.
- `Article` has no persisted setup/default price field. Warehouse article create/update has no
  initial price payload field.
- Reports stock value currently prioritizes latest non-null `Receiving.unit_price`, then preferred
  `ArticleSupplier.last_price`, then `null`; it does not use `Stock.average_price`.

Contract Locks / Clarifications
- Opening inventory is physical setup performed by warehouse staff. It must capture quantities and
  batches, not prices.
- ADMIN/procurement sets the starting purchase/average price during article setup.
- Add a persisted article-level setup price field named `initial_average_price` unless a clearly
  better local pattern is found. It should be nullable `Numeric(14, 4)`.
- Article create/update/detail should accept and serialize `initial_average_price`.
- Opening completion must not create `Surplus` rows or shortage drafts for opening quantities.
- Opening completion should create/update canonical `Stock` rows as an absolute opening baseline:
  `Stock.quantity = counted_quantity`.
- When opening completion writes a `Stock` row, set `Stock.average_price` from
  `Article.initial_average_price` when present. If absent, preserve an existing stock row's
  `average_price`; for a new stock row with no setup price, use `0.0000`.
- For batch-tracked article opening setup, add an endpoint:
  `POST /api/v1/inventory/{count_id}/opening-batch-lines`
  with payload:
  ```json
  {
    "article_id": 123,
    "batch_code": "24001",
    "expiry_date": "2026-12-31",
    "counted_quantity": 10
  }
  ```
  It must be allowed only when the count is `OPENING` and `IN_PROGRESS`, and only for articles
  with `has_batch = true`.
- The endpoint should validate `batch_code` and `expiry_date` consistently with Receiving:
  reuse an existing batch for the same article/code when expiry matches; return
  `BATCH_EXPIRY_MISMATCH` on conflicting expiry; create the batch when missing.
- The endpoint should create an `InventoryCountLine` for the batch with `system_quantity = 0`,
  `counted_quantity = payload.counted_quantity`, `difference = payload.counted_quantity`, and the
  article base UOM. Return the refreshed active-count payload so the frontend can replace its line
  state.
- If the opening count has an uncounted placeholder line for that batch-tracked article
  (`batch_id IS NULL`, `system_quantity = 0`, `counted_quantity IS NULL`), remove it when the first
  real batch line is added so the count can be completed without counting a fake no-batch line.
- Add a line resolution for opening rows, e.g. `OPENING_STOCK_SET`, and include an
  `opening_stock_set` counter in count summaries. If adding the enum is too invasive, document the
  alternative clearly before proceeding; do not report opening quantities as `SURPLUS_ADDED`.
- Report stock overview should use current `Stock.average_price` for valuation when current stock
  quantity is positive. For article-level values across multiple stock rows, compute a weighted
  article unit value from stock rows: `sum(quantity * average_price) / sum(quantity)`. Preserve
  existing fallback behavior for rows without usable stock average price.
- Preserve regular inventory behavior for `REGULAR` counts.
- Preserve receiving weighted-average behavior.

File Ownership
- `backend/app/models/article.py`
- `backend/app/models/enums.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/article_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/report_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/migrations/versions/*.py` (new migrations only)
- `backend/tests/test_articles.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_reports.py`
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/wave-08/phase-01-wave-08-opening-inventory-and-valuation/backend.md`

Delegation Plan
- Backend worker implements backend/model/API/report/test/doc changes for this phase.

Acceptance Criteria
- New article create/update accepts `initial_average_price` and serializes it in article detail.
- Opening inventory completion creates/updates `Stock`, does not create `Surplus`, and does not
  create shortage drafts from opening count differences.
- Opening inventory batch endpoint creates/reuses `Batch` rows and count lines with validation.
- Opening completion uses article setup price as initial `Stock.average_price`.
- Stock overview value uses current `Stock.average_price` for current stock valuation before
  falling back to older price sources.
- Regular inventory tests still prove regular surplus/shortage behavior.
- Alembic has exactly one head.
- Targeted backend tests pass at minimum:
  - `backend/tests/test_inventory_count.py`
  - `backend/tests/test_articles.py`
  - `backend/tests/test_reports.py`

Validation Notes
- 2026-04-08: Orchestrator created Wave 8 Phase 1 from user feedback intake.

Next Action
- Backend worker implements and records `backend.md`.

---

## Delegation Prompt - Backend Worker

You are the backend worker for STOQIO Wave 8 Phase 1.

Read the files listed above before editing. You are not alone in the codebase: other workers may
edit frontend files in parallel. Do not revert or overwrite changes outside your ownership list.

Implement the backend contract in this orchestrator file. Keep changes scoped. Run targeted tests
and `venv/bin/alembic heads`; if full backend tests are feasible, run them too. Write your handoff
entry to `handoff/wave-08/phase-01-wave-08-opening-inventory-and-valuation/backend.md` using the
standard agent template.
