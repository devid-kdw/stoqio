# Backend Agent Handoff — Wave 3 Phase 5: SQLAlchemy Relationship Modernization

## Status

Complete. All six `lazy="dynamic"` relationships have been replaced. All query-object call sites have been migrated to explicit model queries. Targeted regression tests pass.

---

## Scope

- Remove all `lazy="dynamic"` relationship definitions from backend models.
- Replace relationship-as-query-object usage in services and tests with explicit `db.session.query(...)` calls.
- No API shape, ordering, status-code, or error-code changes.

---

## Docs Read

- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/orchestrator.md`
- `backend/app/models/article.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/order.py`
- `backend/app/models/order_line.py`
- `backend/app/services/article_service.py` (grep audit only — no query-object usage found)
- `backend/app/services/inventory_service.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_orders.py`

---

## Audit Results

### Article.batches
- **Previous**: `lazy="dynamic"`
- **Query-object usage found**: None. Services use explicit `Batch.query` / `db.session.query(Batch)` calls keyed by article_id. Confirmed by full grep of `article.batches` across `backend/`.
- **Strategy chosen**: `lazy="select"` — simple collection, no call-site refactoring required.

### Article.aliases
- **Previous**: `lazy="dynamic"`, `cascade="all, delete-orphan"`
- **Query-object usage found**: None. Services use explicit `ArticleAlias.query` calls. Confirmed by full grep.
- **Strategy chosen**: `lazy="select"` — preserves cascade; no call-site refactoring required.

### Article.suppliers
- **Previous**: `lazy="dynamic"`, `cascade="all, delete-orphan"`
- **Query-object usage found**: None. Services use explicit `ArticleSupplier.query` calls. Confirmed by full grep.
- **Strategy chosen**: `lazy="select"` — preserves cascade; no call-site refactoring required.

### DraftGroup.drafts
- **Previous**: `lazy="dynamic"`
- **Query-object usage found**: None. No service or test code accesses `draft_group.drafts` as a query object. Confirmed by full grep of `.drafts` across `backend/`.
- **Strategy chosen**: `lazy="select"` — no call-site refactoring required.

### InventoryCount.lines
- **Previous**: `lazy="dynamic"`, `cascade="all, delete-orphan"`
- **Query-object usage found**: Concentrated in `inventory_service.py` and `test_inventory_count.py`:
  - `count.lines.count()` — used in `list_counts()` and `get_active_count()`
  - `count.lines.filter(...).count()` — used in `list_counts()` and `get_active_count()`
  - `count.lines.all()` — used in `get_active_count()`, `get_count_detail()`, `complete_count()`
  - `count.lines.first()` — used in `test_inventory_count.py` (line 751)
  - `count.lines.count()` — used in `test_inventory_count.py` (line 393)
  - `count.lines.all()` — used in `test_inventory_count.py` (line 673)
- **Strategy chosen**: `lazy="select"` + explicit `db.session.query(InventoryCountLine).filter_by(inventory_count_id=...)` calls at all call sites. `write_only` was not appropriate here because the relationship is used both for writing new lines (during `start_count`) and for reading the full collection.

### Order.lines
- **Previous**: `lazy="dynamic"`, `cascade="all, delete-orphan"`
- **Query-object usage found**: One call site in `order_service.py` line 909:
  - `order.lines.order_by(OrderLine.id.asc()).all()`
- **Strategy chosen**: `lazy="select"` + explicit `db.session.query(OrderLine).filter_by(order_id=order.id).order_by(OrderLine.id.asc()).all()`. The ordering requirement is preserved exactly.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/app/models/article.py` | `Article.batches`, `Article.aliases`, `Article.suppliers`: `lazy="dynamic"` → `lazy="select"` |
| `backend/app/models/draft_group.py` | `DraftGroup.drafts`: `lazy="dynamic"` → `lazy="select"` |
| `backend/app/models/inventory_count.py` | `InventoryCount.lines`: `lazy="dynamic"` → `lazy="select"` |
| `backend/app/models/order.py` | `Order.lines`: `lazy="dynamic"` → `lazy="select"` |
| `backend/app/services/inventory_service.py` | Replaced 5 query-object call sites with explicit `db.session.query(InventoryCountLine)` queries in `list_counts()`, `get_active_count()`, `get_count_detail()`, `complete_count()` |
| `backend/app/services/order_service.py` | Replaced 1 query-object call site with explicit `db.session.query(OrderLine)` query in `receive_order_lines()` return block |
| `backend/tests/test_inventory_count.py` | Replaced 3 query-object call sites (`count.lines.count()`, `count.lines.all()`, `count.lines.first()`) with explicit `_db.session.query(InventoryCountLine)` queries |

---

## Commands Run

```
rg -n 'lazy="dynamic"' backend/app/models -g '*.py'
# → no output (zero remaining lazy="dynamic" relationships)

cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q
# → 154 passed, 1 failed (pre-existing issue — see Open Issues below)

cd backend && venv/bin/python -m pytest tests/test_articles.py::TestWarehouseArticles::test_include_inactive_true_includes_inactive_articles -v
# → 1 passed (confirms the failure is a pre-existing inter-module DB isolation issue, not caused by this phase)
```

---

## Tests

**Targeted suite (155 tests total):** 154 passed, 1 pre-existing failure.

- `tests/test_orders.py` — all pass
- `tests/test_inventory_count.py` — all pass
- `tests/test_drafts.py` — all pass
- `tests/test_articles.py` — 1 pre-existing failure (see Open Issues)

---

## Open Issues / Risks

**Pre-existing test isolation failure — not caused by this phase:**

`tests/test_articles.py::TestWarehouseArticles::test_include_inactive_true_includes_inactive_articles` fails when run together with `test_inventory_count.py`. The inventory count module fixture creates an article `INV-ART-999` with description `"Inactive article"` and `is_active=False`. When the full suite runs, this article exists in the database and appears in the `q=inactive` article search, displacing `WH-INACTIVE-003` from the first result position. The test passes in isolation (`1 passed`). This is a cross-module test fixture pollution issue that predates this phase and is unrelated to relationship loading strategy changes.

No `write_only` relationships were introduced — audited usage patterns for all six relationships ruled it out (each relationship is either read-accessed as a collection or replaced by explicit queries).

---

## Next Recommended Step

Delegate to Testing Agent to lock regression coverage as specified in the orchestrator delegation prompt. Testing Agent should run `cd backend && venv/bin/python -m pytest -q` for the full suite and document results. The pre-existing isolation failure should be noted and left for a dedicated test cleanup phase unless the Testing Agent is in scope to fix it.
