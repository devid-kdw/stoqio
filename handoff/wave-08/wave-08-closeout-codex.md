# Wave 8 Closeout — Codex

Date
- 2026-04-08

Author
- Codex, main orchestrator session

Context
- User provided Wave 8 feedback on opening inventory behavior, batch terminology,
  initial article pricing, purchase-order supplier article-code autofill, and
  Croatian Settings copy.
- The orchestrator collected the findings in `handoff/Findings/wave-08-user-feedback.md`,
  opened `handoff/wave-08`, delegated three implementation phases, integrated the worker
  changes, reset the local dev inventory state, and validated the full workspace.

Files Changed
- `handoff/Findings/wave-08-user-feedback.md`
  - Added W8-F-001 through W8-F-006 user findings.
- `handoff/decisions/decision-log.md`
  - Added opening-inventory and initial-price decisions.
- `handoff/wave-08/README.md`
  - Opened Wave 8 with phase ownership and finding traceability.
- `handoff/wave-08/phase-01-wave-08-opening-inventory-and-valuation/*`
  - Backend orchestrator and worker handoff.
- `handoff/wave-08/phase-02-wave-08-inventory-and-warehouse-frontend/*`
  - Inventory/Warehouse frontend orchestrator and worker handoff.
- `handoff/wave-08/phase-03-wave-08-orders-and-settings-frontend/*`
  - Orders/Settings frontend orchestrator and worker handoff.
- `backend/app/models/article.py`
  - Added `Article.initial_average_price`.
- `backend/app/models/enums.py`
  - Added `InventoryCountLineResolution.OPENING_STOCK_SET`.
- `backend/migrations/versions/d7e8f9a0b1c2_add_article_initial_average_price_and.py`
  - Added article initial price column and opening inventory resolution enum value.
- `backend/app/services/article_service.py`
  - Article create/update/detail now accepts and serializes `initial_average_price`.
- `backend/app/services/inventory_service.py`
  - Opening inventory now sets `Stock` baseline instead of creating surplus or shortage drafts.
  - Added opening batch-line handling for batch-tracked articles.
- `backend/app/api/inventory_count/routes.py`
  - Added `POST /api/v1/inventory/{count_id}/opening-batch-lines`.
- `backend/app/services/report_service.py`
  - Stock overview valuation now prefers current `Stock.average_price` weighted by quantity.
- `backend/tests/test_articles.py`
  - Added article initial price coverage.
- `backend/tests/test_inventory_count.py`
  - Added opening inventory baseline and opening batch-line coverage.
- `backend/tests/test_reports.py`
  - Added stock-average valuation coverage.
- `frontend/src/api/articles.ts`
  - Added `initial_average_price` API typing.
- `frontend/src/api/inventory.ts`
  - Added `OPENING_STOCK_SET`, `opening_stock_set`, and opening batch-line API typing.
- `frontend/src/pages/warehouse/*`
  - Added `Prosječna cijena` to article create/edit/detail handling.
- `frontend/src/pages/inventory/*`
  - Added opening batch-line UI, opening-count summary handling, and `Šarža` terminology.
- `frontend/src/pages/orders/OrdersPage.tsx`
  - Supplier-scoped article lookup now keeps supplier context fresh and autofills
    `Šifra artikla dobavljača`.
- `frontend/src/pages/settings/SettingsPage.tsx`
  - Localized Settings section headings and adjacent save/action copy.
- `frontend/src/pages/settings/__tests__/SettingsPage.test.tsx`
  - Added Settings Croatian-copy smoke test.
- `stoqio_docs/05_DATA_MODEL.md`
  - Documented `initial_average_price` and opening stock seed behavior.
- `stoqio_docs/13_UI_WAREHOUSE.md`
  - Documented `Prosječna cijena` in Warehouse article setup/detail.
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
  - Documented opening batch-line flow and `OPENING_STOCK_SET`.
- `stoqio_docs/18_UI_SETTINGS.md`
  - Updated Settings copy contract to Croatian headings.

Local Dev Database Reset
- Target database: `postgresql://grzzi@localhost/wms_dev`.
- Before reset:
  - `stock_rows=0`, `stock_qty_sum=0`
  - `surplus_rows=10`, `surplus_qty_sum=10808.000`
  - `opening_counts=1`, `opening_lines=10`, `opening_drafts=0`
- Reset action:
  - Deleted opening inventory id `1`.
  - Deleted `10` inventory transactions linked to the bad opening run.
  - Deleted `10` surplus rows created by the bad opening run.
  - Deleted `10` opening inventory lines.
  - Deleted `1` opening inventory count.
  - `0` stock rows needed quantity reset because no `Stock` rows existed.
- After reset and Wave 8 migration:
  - `stock_rows=0`, `stock_qty_sum=0`
  - `surplus_rows=0`, `surplus_qty_sum=0`
  - `opening_counts=0`, `opening_lines=0`, `opening_drafts=0`

Validation
- `git diff --check`
  - Passed.
- `cd backend && venv/bin/alembic heads`
  - Passed: one head, `d7e8f9a0b1c2`.
- `cd backend && venv/bin/alembic upgrade head`
  - Passed on local PostgreSQL dev DB.
  - Applied `fcb524a92fa4 -> a7b8c9d0e1f2`, `a7b8c9d0e1f2 -> b8c9d0e1f2a3`, and
    `b8c9d0e1f2a3 -> d7e8f9a0b1c2`.
- `cd backend && venv/bin/alembic current`
  - Passed: `d7e8f9a0b1c2 (head)`.
- `cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_inventory_count.py tests/test_reports.py -q --tb=short`
  - Passed: 140 passed.
- `cd backend && venv/bin/python -m pytest -q --tb=short`
  - Passed: 583 passed.
- `cd frontend && npm run lint`
  - Passed.
- `cd frontend && npm run build`
  - Passed.
- `cd frontend && npm test -- src/pages/settings/__tests__/SettingsPage.test.tsx`
  - Passed: 1 test file, 1 test.
- `cd frontend && npm test`
  - Passed: 12 test files, 42 tests.

Residual Notes
- Frontend Vitest emits a non-blocking warning: `--localstorage-file was provided without a valid path`.
  Tests still pass.
- Inventory module RBAC remains ADMIN-only per the existing route contract. Wave 8 used the user's
  operator/procurement distinction to place pricing in article setup, not to change access control.

Post-Closeout Follow-Up
- User reported that `Šifra artikla dobavljača` still did not appear on the new order form.
- Verified local dev data for article `800048` and supplier Mankiewicz (`supplier_id=1`):
  backend `lookup_articles('800048', supplier_id=1)` returns `supplier_article_code='34657.9723.7.020'`.
- Updated `frontend/src/pages/orders/OrdersPage.tsx` so selecting an article triggers an exact
  supplier-scoped refresh for that article and fills `Šifra artikla dobavljača` even if the dropdown
  option came from a stale or supplierless lookup.
- Ran:
  - `cd frontend && npm run lint` — passed.
  - `cd frontend && npm run build` — passed.
- Copied the fresh `frontend/dist` output into `backend/static`.
- Verified `frontend/dist/index.html` and `backend/static/index.html` hashes match, and backend static
  now references `assets/index-DZXCHWDj.js` / `assets/OrdersPage-B4eoIyih.js`.
- User later clarified the behavior is expected: the supplier article code appears only after a
  supplier is selected, because the value is supplier-specific.

Post-Closeout Follow-Up 2
- User requested an opening-inventory UX improvement for batch entry:
  - remove the separate `Učitaj artikl` button
  - show matching articles while typing
  - allow adding multiple batches for the same selected article without reloading it
  - fix grouped batch-article rows staying white in dark mode
- Updated `frontend/src/pages/inventory/ActiveCountView.tsx`:
  - replaced manual article-number load with a searchable `Select` that queries Warehouse articles
    while the user types
  - loading an article now happens immediately on dropdown selection
  - successful `Dodaj šaržu` keeps the selected article and clears only batch-specific fields
  - grouped batch-header rows and batch child result rows now use dark-mode-safe backgrounds instead
    of hardcoded light status colors
- Added W8-F-007 and W8-F-008 to `handoff/Findings/wave-08-user-feedback.md` for traceability.
- Ran:
  - `cd frontend && npm run lint` — passed.
  - `cd frontend && npm run build` — passed.
  - `git diff --check` — passed.
- Copied the fresh `frontend/dist` output into `backend/static`.
- Verified `frontend/dist/index.html` and `backend/static/index.html` hashes match, and backend static
  now references `assets/index-DfGh2u0C.js` / `assets/InventoryCountPage-BNLnQ9G9.js`.

Post-Closeout Follow-Up 3
- User liked the alternating darker row pattern visible on the Inventory table in dark mode and
  requested the same readability pattern across all STOQIO tables.
- Added shared frontend theme file `frontend/src/theme.ts`.
- Updated Mantine provider usage in `frontend/src/main.tsx` and `frontend/src/utils/test-utils.tsx`
  to use the shared theme.
- Set global `Table` default props to `striped="odd"` so zebra rows apply across the app without
  repeating per-screen props.
- Added W8-F-009 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 4
- User then reported two remaining gaps:
  - Warehouse list rows still hid zebra striping because the whole row background was tinted by
    reorder status.
  - Active Inventory batch-parent rows left `Razlika` empty instead of showing the aggregate child
    quantity.
- Updated `frontend/src/pages/warehouse/WarehousePage.tsx`:
  - removed full-row reorder-status tint so zebra striping remains visible even when all rows are in
    the same reorder zone
  - kept reorder-state visibility via the existing status indicator and label
- Updated `frontend/src/pages/inventory/ActiveCountView.tsx`:
  - removed full-row discrepancy backgrounds from counted rows and batch child rows so zebra striping
    remains the base pattern
  - removed the fixed batch-parent row background for the same reason
  - batch parent rows now show aggregate `Prebrojano` and aggregate `Razlika` when all child lines
    are counted
- Added W8-F-010 and W8-F-011 to `handoff/Findings/wave-08-user-feedback.md` for traceability.
- Ran:
  - `cd frontend && npm run lint` — passed.
  - `cd frontend && npm run build` — passed.

Post-Closeout Follow-Up 5
- User reported that completed Inventory detail still showed bright full-row status backgrounds in
  dark mode.
- Updated `frontend/src/pages/inventory/CompletedDetailView.tsx`:
  - removed the completed-detail full-row background override for line status
  - kept status visibility through `ResolutionBadge` and colored `Razlika`
- Added W8-F-012 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 6
- User reported two additional Wave 8 follow-ups:
  - completed Inventory detail still lists batch-tracked articles as repeated flat rows instead of
    a single expandable parent row with batches beneath it
  - Reports stock overview still shows `0,00 €` values even after initial/prosječna cijena was
    entered for articles
- Updated `frontend/src/pages/inventory/CompletedDetailView.tsx`:
  - reused the active-inventory batch grouping pattern for completed counts
  - added expandable parent rows for batch-tracked articles
  - parent rows now summarize total system quantity, total counted quantity, and total difference
    across grouped batches
  - child rows keep per-batch `Šarža`, `Rok valjanosti`, and status detail
- Updated `backend/app/services/report_service.py`:
  - added `Article.initial_average_price` fallback for stock overview valuation when the current
    stock weighted average is missing or resolves to zero
  - kept current stock weighted average as the primary source whenever it is valid
- Updated `backend/tests/test_reports.py`:
  - added a regression test covering stock rows with zero `average_price` and non-zero
    `initial_average_price`
- Added W8-F-013 and W8-F-014 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 7
- User requested explicit barcode generation actions in Warehouse article detail:
  - a `Generiraj` action beside the non-batch article `Barkod` field
  - a `Generiraj` action in `Šarže (FEFO) -> Akcije` for batch-tracked articles
- Updated backend barcode flow:
  - added dedicated JSON generate endpoints for articles and batches
  - separated barcode generation/persistence from PDF download and direct printer output
  - hardened barcode lookups to refresh entities from the database before generation so stale
    session state cannot pretend a barcode exists when it does not
- Updated frontend Warehouse detail:
  - article edit form now shows a `Generiraj` button beside the `Barkod` input
  - successful generation writes the returned barcode back into article state and the edit form
  - FEFO batch action rows now include `Generiraj`, `PDF`, and `Printer`
- Updated `backend/tests/test_articles.py` with coverage for the new generate endpoints.
- Added W8-F-015 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 8
- User requested two UI copy/presentation tweaks:
  - FEFO batch action button should read `Generiraj barkod`, not only `Generiraj`
  - Reports stock overview `Status` column should show only the colored indicator dot, without the
    clipped badge text beside it
- Updated `frontend/src/pages/warehouse/ArticleDetailPage.tsx`:
  - renamed the FEFO batch action label to `Generiraj barkod`
- Updated `frontend/src/pages/reports/ReportsPage.tsx`:
  - simplified the stock-overview `Status` cell renderer to a dot-only reorder indicator with
    tooltip/aria label
- Added W8-F-016 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 9
- User pointed out that batch-tracked articles should not show top-level article barcode output
  actions in the header, because barcode output belongs to the batch rows under `Šarže (FEFO)`.
- Updated `frontend/src/pages/warehouse/ArticleDetailPage.tsx`:
  - hid top-right article-level `Ispis barkoda (PDF)` and `Pošalji na printer` actions when
    `article.has_batch` is true
  - kept the header edit/deactivate actions unchanged
  - hid the related printer-configuration helper text in the header for batch-tracked articles
- Added W8-F-017 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 10
- User reported a small but annoying article-edit UX issue: after scrolling down to click `Spremi`,
  the page stayed at the bottom after save, forcing a manual scroll back to the header.
- Updated `frontend/src/pages/warehouse/ArticleDetailPage.tsx`:
  - after a successful article save, the page now scrolls back to the top automatically
- Added W8-F-018 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 11
- User pointed out that create/edit forms for batch-tracked articles should not expose an
  article-level `Barkod` field, because barcode ownership belongs to the batch.
- Updated frontend Warehouse forms:
  - `frontend/src/pages/warehouse/WarehouseArticleForm.tsx` now hides the barcode field whenever
    `form.hasBatch` is true
  - `frontend/src/pages/warehouse/WarehousePage.tsx` and
    `frontend/src/pages/warehouse/ArticleDetailPage.tsx` now clear in-form barcode state when the
    user switches an article into batch-tracked mode
  - `frontend/src/pages/warehouse/warehouseUtils.ts` now sends `barcode: null` for batch articles
    in create/update payloads
  - article detail read-only metadata also hides the article-level `Barkod` field for batch
    articles for consistency
- Added W8-F-019 to `handoff/Findings/wave-08-user-feedback.md` for traceability.

Post-Closeout Follow-Up 12
- User pointed out that batch barcode generation still lacked visible state:
  - after generating a batch barcode, the FEFO table did not show the actual barcode value
  - `Generiraj barkod` stayed clickable, making it unclear whether generation had already happened
    or whether repeated clicks would overwrite the barcode
- Updated backend article detail serialization:
  - batch rows now include `barcode` in the article detail payload
- Updated `frontend/src/pages/warehouse/ArticleDetailPage.tsx`:
  - added a FEFO `Barkod` column
  - after successful generation, the returned barcode is written into local FEFO row state
  - FEFO generate action now switches into a disabled `Barkod generiran` state when the batch
    already has a barcode
- Updated `backend/tests/test_articles.py`:
  - article detail tests now assert batch barcode presence in the payload
  - batch generate tests now verify the generated barcode is visible through the article detail API
- Added W8-F-020 to `handoff/Findings/wave-08-user-feedback.md` for traceability.
