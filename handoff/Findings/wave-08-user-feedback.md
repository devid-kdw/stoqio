# Wave 8 User Feedback Findings

Date opened: 2026-04-08

Source:
- User feedback in the main Codex orchestration session.

Status:
- Collecting feedback before opening `handoff/wave-08`.

Notes:
- This document is the intake list for Wave 8 planning.
- Items should be confirmed and converted into scoped Wave 8 phase handoffs before implementation.
- Keep entries append-only while feedback is still being collected.

## W8-F-001: Opening inventory completion records initial stock as surplus

Status:
- open

Area:
- Inventory Count
- Backend inventory completion semantics

Source:
- User feedback, 2026-04-08 15:59 CEST

User report:
- The Inventory module now allows selecting an initial/opening inventory flow.
- In that flow, the user enters the current warehouse quantities after entering articles.
- After completing the opening inventory, the system records those quantities as surplus (`višak`).
- That is wrong: opening inventory should establish the initial/current warehouse stock state.

Expected behavior:
- Quantities entered during an `OPENING` inventory count should become the starting warehouse stock baseline.
- Opening quantities should not be treated as surplus.
- Completing an opening inventory should not make the UI/reports imply that all initial stock is a discovered excess.

Current likely behavior:
- `OPENING` inventory count completion appears to reuse the regular inventory discrepancy path.
- Positive differences are routed to `Surplus`, matching regular count semantics but not opening-stock semantics.

Likely impacted files:
- `backend/app/services/inventory_service.py`
- `backend/app/models/inventory_count.py`
- `backend/tests/test_inventory_count.py`
- Potential frontend/reporting copy if any screen labels opening-stock results as surplus.

Related prior decision:
- `DEC-INV-007` said `OPENING` counts use the same snapshot and completion semantics as `REGULAR` counts.
- This user feedback supersedes that part of `DEC-INV-007`: opening counts must establish initial stock, not regular surplus/shortage discrepancy output.

Open implementation questions for Wave 8 scoping:
- Should opening completion set stock rows absolutely to counted quantities, or only add deltas when pre-existing stock exists?
- Should opening completion create audit `Transaction` rows, and if yes, which `tx_type` and reference semantics should be used?
- Should opening completion completely bypass shortage draft creation for counted quantities below any pre-existing system snapshot?

Recommended direction:
- Add a dedicated completion branch for `InventoryCount.type == OPENING`.
- Persist counted opening quantities into canonical `Stock` rows instead of `Surplus`.
- Prevent regular opening-count completion from generating misleading surplus output.
- Add regression tests proving an opening count with zero prior stock and positive counted quantities creates stock, not surplus.

## W8-F-002: Completed inventory uses "Serija" instead of "Šarža"

Status:
- open

Area:
- Inventory Count
- Frontend Croatian UI terminology

Source:
- User feedback and screenshot, 2026-04-08 16:03 CEST

User report:
- In the completed inventory detail screen, the batch column is labeled `Serija`.
- It should be labeled `Šarža`.

Observed code pointers:
- `frontend/src/pages/inventory/CompletedDetailView.tsx` has `<Table.Th>Serija</Table.Th>`.
- Related inventory UI copy should also be checked because `frontend/src/pages/inventory/ActiveCountView.tsx` has an active-count table header labeled `Batch`.

Expected behavior:
- Croatian Inventory UI should consistently use `Šarža` for batch/lot terminology.
- The completed-count table should show `Šarža`, not `Serija`.
- Regular inventory and opening inventory screens should not mix `Batch`, `Serija`, and `Šarža`.

Recommended direction:
- Replace the completed-count label `Serija` with `Šarža`.
- Run a targeted Inventory Count UI terminology sweep for batch labels and helper text.
- Consider a broader later UI copy sweep because other modules may still contain `Serija`, but the Wave 8 minimum requested fix is the Inventory completed-count screen.

## W8-F-003: Opening inventory needs a way to enter existing batches for batch-tracked articles

Status:
- open

Area:
- Inventory Count
- Warehouse article onboarding
- Backend batch + stock initialization semantics
- Frontend opening-inventory workflow

Source:
- User feedback, 2026-04-08 16:03 CEST

User report:
- The Warehouse article create/edit form has the option `Artikl sa šaržom`.
- There is no option there to enter the batches that already exist in the warehouse.
- Since the initial stock state is set through opening inventory, opening inventory likely needs a way to enter the batches for the relevant article.
- Opening inventory is therefore meaningfully different from regular inventory because setup facts such as existing batch codes are established there.

Current likely behavior:
- Batch-tracked articles can be marked with `has_batch = true` in Warehouse.
- New batches are currently created through Receiving, not through Warehouse article creation.
- Regular inventory snapshots existing article/batch rows; if no batch rows exist yet, earlier inventory logic may represent batch-tracked articles without real initial batch rows.

Expected behavior:
- Opening inventory should support declaring the currently existing batches for a batch-tracked article, including at least:
  - batch code
  - expiry date
  - counted/current quantity
- Completing the opening inventory should create or reuse the corresponding `Batch` rows and initialize canonical `Stock` rows for those batches.
- Regular inventory should remain mostly a counting/reconciliation flow over known stock and known batches, not a general batch-creation workflow by default.

Orchestrator recommendation:
- Keep Warehouse article creation focused on article master data (`Artikl sa šaržom` only declares that the article is batch-tracked).
- Add batch entry to the `OPENING` inventory flow, because opening inventory is the natural setup step where the operator records the warehouse's real initial stock state.
- Model opening inventory for batch-tracked articles as "add one or more batch lines under this article" with quantity per batch, then use those lines to establish initial stock.
- Do not use `Surplus` for these opening quantities; this should be coordinated with W8-F-001.

Open implementation questions for Wave 8 scoping:
- Should opening inventory allow adding multiple batch rows directly under one article in the active count table?
- Should `batch_code` validation and `expiry_date` requirements match Receiving exactly?
- If a batch code already exists for that article, should opening inventory reuse it when expiry matches and return a conflict if expiry differs, matching Receiving behavior?
- Should regular inventory allow adding a newly discovered batch later, or should new batch creation after go-live remain limited to Receiving?

## W8-F-004: Initial purchase/average price is missing when creating articles and opening stock

Status:
- open

Area:
- Warehouse article create
- Opening inventory / initial stock setup
- Backend stock valuation
- Reports stock value

Source:
- User feedback, 2026-04-08 16:07 CEST

User report:
- When creating a new article and setting up the warehouse, there should be a field such as `Zadnja nabavna cijena` or `Prosječna cijena`.
- This is important during initial setup because the system needs a starting price/value for existing stock.
- The user recalls that average price should later be calculated automatically from receiving and ordering flows where the article price is entered on the current order/receipt.

Current code/docs reality:
- `Stock.average_price` is the canonical weighted-average purchase price field for actual on-hand stock buckets.
- Receiving updates `Stock.average_price` in `backend/app/services/receiving_service.py` using weighted average:
  `(current_quantity * current_avg + received_quantity * unit_price) / (current_quantity + received_quantity)`.
- Linked receiving uses `OrderLine.unit_price` when receipt line `unit_price` is not explicitly supplied.
- Ad-hoc receiving without `unit_price` preserves an existing stock row's `average_price`; if a new stock row is created with no price, `average_price` initializes to `0.0000`.
- `ArticleSupplier.last_price` exists as supplier-level last known price, but Warehouse article create currently only submits supplier id/code/preferred status and does not set `last_price`.
- Warehouse article create/update currently has no price field.
- Reports stock-overview valuation currently prioritizes most recent non-null `Receiving.unit_price`, then preferred supplier `ArticleSupplier.last_price`, then `null`.

Expected behavior:
- During article + warehouse setup, ADMIN should have a way to enter an initial purchase/average price for the article's opening stock.
- After opening setup, stock valuation should not default to `0.0000` or `null` when the user knows the real starting price.
- Later receiving/order flows should continue to update/derive average price automatically from `unit_price` using the existing weighted-average logic.

Important modeling note:
- `average_price` belongs to `Stock`, not directly to `Article`.
- For batch-tracked articles, initial average price may need to be stored per batch stock row, because each `Stock` bucket is `(location_id, article_id, batch_id)`.
- If no stock row exists yet, adding a price only to the article form does not by itself create a canonical stock valuation unless Wave 8 also defines where that value is persisted until opening inventory creates stock.

Recommended direction:
- Coordinate this with W8-F-001 and W8-F-003.
- Treat `Prosječna cijena` as the likely user-facing label because the runtime field is `Stock.average_price` and it continues as a weighted average after future receiving.
- Add initial average price input to the opening-stock setup path, at least for each opening stock row/batch line, so the value can be written directly to the resulting `Stock.average_price`.
- Consider optionally showing a default price on Warehouse article creation only as a setup convenience, but do not rely on article master data alone as the canonical valuation store unless a new backend field is deliberately added.

Open implementation questions for Wave 8 scoping:
- Should the visible label be `Prosječna cijena`, `Zadnja nabavna cijena`, or both with helper text?
- Should non-batch opening inventory use one price per article line and batch-tracked opening inventory use one price per batch line?
- Should reports use `Stock.average_price` for current inventory value before falling back to latest `Receiving.unit_price` / preferred supplier `last_price`, or should the existing report fallback order stay unchanged?
- Should Warehouse supplier links allow entering `ArticleSupplier.last_price` during article creation, independently of initial stock valuation?

User clarification, 2026-04-08 16:11 CEST:
- Opening inventory will logically be performed by a warehouse operator.
- Initial article creation / article master setup will logically be performed by ADMIN / procurement.
- The warehouse operator does not need to know prices and should not be responsible for entering them during opening inventory.
- Therefore the initial price field should be part of article creation/setup, not the opening inventory counting workflow.

Updated recommended direction:
- Add the starting price field to Warehouse article creation/setup, not to the opening inventory line-entry UI.
- Opening inventory should capture physical facts only: article, batch code / expiry where applicable, and quantity.
- Backend implementation needs a bridge from the article-level setup price to `Stock.average_price` when opening inventory later creates the actual stock rows.
- The price field may need to be stored as a new article-level setup/default valuation field, because `Stock.average_price` cannot be written until stock rows exist.
- When opening inventory creates stock for the article, use the article's setup price as the initial `Stock.average_price` unless a more specific future rule is explicitly defined.

## W8-F-005: Purchase order article selection does not autofill supplier article code

Status:
- open

Area:
- Orders
- Warehouse supplier links
- Frontend order creation form

Source:
- User feedback and screenshot, 2026-04-08 16:14 CEST

User report:
- During new purchase order creation, the user selects/enters the article they want to order.
- The `Šifra artikla dobavljača` field remains empty.
- The supplier article code had already been entered during article setup.
- The field should be automatically populated when the article is selected on the purchase order.

Current code/docs reality:
- Backend Orders lookup already supports this contract:
  - `GET /api/v1/orders/lookups/articles?q=...&supplier_id=...`
  - `backend/app/services/order_service.py` returns `supplier_article_code` and `last_price` when an `ArticleSupplier` link exists for `(article_id, supplier_id)`.
  - `backend/tests/test_orders.py` already asserts `supplier_article_code == "SUP-LINK-001"` and `last_price == 12.34` for lookup with `supplier_id`.
- Frontend create-order selection code (`frontend/src/pages/orders/OrdersPage.tsx`) fills `supplierArticleCode` from `selectedArticle.supplier_article_code` when present.
- Therefore the likely bug is in the frontend lookup/select flow, not the core backend contract.

Likely failure modes to verify in Wave 8:
- The article lookup may be running without the currently selected `supplier_id`.
- Article options may have been loaded before supplier selection and then reused after supplier selection, so `supplier_article_code` remains `null`.
- Changing the selected supplier may not invalidate/reset/refetch already selected article options and line drafts.
- Supplier links created in the Warehouse article form may be persisted without `ArticleSupplier.last_price`, but `supplier_article_code` should still persist and be returned.

Expected behavior:
- In new order creation, after a supplier is selected and an article with a matching supplier link is selected, `Šifra artikla dobavljača` should autofill from `ArticleSupplier.supplier_article_code`.
- If the selected supplier changes, existing line article selections/options should be refreshed or cleared so supplier-specific data cannot stay stale.
- If no supplier-specific article code exists, the field may remain blank and still be manually editable.

Recommended direction:
- Add/adjust frontend regression coverage around `OrdersPage` create flow:
  - select supplier
  - lookup/select an article whose lookup response includes `supplier_article_code`
  - assert the `Šifra artikla dobavljača` field is populated
  - change supplier and assert supplier-specific article code state is cleared or refetched
- Preserve the existing backend lookup contract unless investigation proves the API is not receiving the correct `supplier_id`.

## W8-F-006: Settings section titles are still in English

Status:
- open

Area:
- Settings
- Frontend Croatian localization
- Product docs localization alignment

Source:
- User feedback and screenshot, 2026-04-08 16:18 CEST

User report:
- In the Settings (`Postavke`) module, section titles are still in English:
  `General`, `Roles`, `Quotas`, and similar.
- These headings should be Croatian.

Observed code pointers:
- `frontend/src/pages/settings/SettingsPage.tsx` hardcodes section titles:
  - `1. General`
  - `2. Roles`
  - `3. UOM Catalog`
  - `4. Article Categories`
  - `5. Quotas`
  - `6. Barcode`
  - `7. Export`
  - `8. Suppliers`
  - `9. Users`
- The same file also has mixed save-button copy such as `Spremi General`, `Spremi Roles`, `Spremi Barcode`, and `Spremi Export`.
- `stoqio_docs/18_UI_SETTINGS.md` also documents the section names in English, so docs likely need alignment after the UI copy is fixed.

Expected behavior:
- Settings section titles should be Croatian by default, consistent with the HR-first UI rule.
- Suggested labels:
  - `1. Općenito`
  - `2. Role`
  - `3. Mjerne jedinice`
  - `4. Kategorije artikala`
  - `5. Kvote`
  - `6. Barkodovi`
  - `7. Izvoz`
  - `8. Dobavljači`
  - `9. Korisnici`
- Related buttons and short descriptions in those sections should not mix English section names into Croatian copy.

Recommended direction:
- Update Settings hardcoded section titles and directly adjacent action copy in `SettingsPage.tsx`.
- Add or update frontend smoke/regression coverage if existing localized-copy tests can cheaply catch these titles.
- Update `stoqio_docs/18_UI_SETTINGS.md` to reflect the Croatian user-facing section names while preserving API/internal English identifiers.

## W8-F-007: Opening inventory batch entry should use searchable dropdown, not manual load button

Status:
- open

Area:
- Inventory Count
- Frontend opening inventory UX

Source:
- User feedback, 2026-04-08 19:20 CEST

User report:
- In opening inventory batch entry, the user currently types an article number and then clicks
  `Učitaj artikl`.
- The user expects article suggestions while typing and then selection from a dropdown.
- The extra `Učitaj artikl` button feels unnecessary and slows the flow.

Expected behavior:
- The article field should be searchable by article number and description.
- Matching articles should appear in a dropdown/autocomplete list while the user types.
- Selecting one suggestion should immediately load the article context for batch entry.
- The batch-entry flow should not require a separate `Učitaj artikl` confirmation button.

Recommended direction:
- Replace the manual article-number input and button with a searchable select/autocomplete.
- Keep the article-detail fetch on selection so batch validation still uses canonical article data.
- Preserve the current constraint that only batch-tracked articles can be used in this flow.

## W8-F-008: Opening inventory should allow consecutive batch additions for the same article and respect dark mode row colors

Status:
- open

Area:
- Inventory Count
- Frontend batch-entry workflow
- Frontend dark mode styling

Source:
- User feedback and screenshot, 2026-04-08 19:22 CEST

User report:
- After adding one batch for an article, the user gets an error when trying to add another batch
  for the same article unless they re-enter and reload the article.
- The user should be able to add a second batch for the same selected article without reloading it.
- In dark mode, grouped batch article rows remain white on the active inventory screen.

Expected behavior:
- After a successful batch add, the selected article should remain loaded so the user can enter the
  next batch immediately.
- Only the per-batch fields should reset after submit: batch code, expiry date, and quantity.
- Group header rows for batch-tracked articles should adapt to the active color scheme and not stay
  white in dark mode.

Recommended direction:
- Keep selected opening-article state after successful `Dodaj šaržu`.
- Reset only the batch subfields, not the article selection.
- Replace the hardcoded light background for grouped batch rows with a color-scheme-aware token.

## W8-F-009: All STOQIO tables should use alternating row backgrounds for better readability

Status:
- open

Area:
- Frontend design system
- Shared table styling

Source:
- User feedback and screenshot, 2026-04-08 19:33 CEST

User report:
- On the Inventory screen in dark mode, alternating darker gray rows make the table easier to scan.
- The user wants that same row separation pattern in every table across STOQIO.

Expected behavior:
- All app tables should use a consistent zebra-row pattern by default.
- The pattern should work in both light and dark mode.
- Screens that already use explicit status colors may still override the zebra background where needed.

Recommended direction:
- Move table striping into a shared Mantine theme default instead of relying on per-page props.
- Keep the pattern subtle and readable so it works as a system-wide default.
- Let explicit row-status backgrounds continue to win when a module intentionally marks a row as
  success, warning, surplus, shortage, or similar.

## W8-F-010: Zebra pattern should remain visible on Warehouse and active Inventory screens even when row state exists

Status:
- open

Area:
- Warehouse list
- Active inventory count
- Frontend table/status presentation

Source:
- User feedback and screenshots, 2026-04-08 19:38 CEST

User report:
- On the Warehouse screen, zebra rows are not visible while all articles are in the red reorder zone.
- On the active Inventory screen, counted rows also stop following the zebra pattern.

Expected behavior:
- Zebra striping should remain the base table pattern on these screens.
- Reorder status and inventory discrepancy state should not completely replace row separation.
- Status should still be visible through indicators, text color, or other lighter-weight cues.

Recommended direction:
- Remove full-row status tints on Warehouse list rows so the shared zebra pattern can show through.
- In active Inventory, use zebra as the base and keep discrepancy emphasis in content-level styling
  such as the `Razlika` cell rather than full-row backgrounds.

## W8-F-011: Batch parent rows in active Inventory should show aggregate totals, including total difference

Status:
- open

Area:
- Inventory Count
- Frontend batch-group summary rows

Source:
- User feedback and screenshot, 2026-04-08 19:38 CEST

User report:
- In active Inventory, parent rows for batch-tracked articles leave `Razlika` empty.
- The user expects the parent row to show the total quantity aggregated from all child batches.

Expected behavior:
- Batch parent rows should summarize their child rows, not leave key numeric columns blank.
- At minimum, the parent row should show aggregate `Razlika`.
- Showing aggregate `Prebrojano` on the parent row is also desirable because it matches the summary
  role of the parent row.

Recommended direction:
- Sum child batch quantities into parent-row totals.
- Show aggregate `Prebrojano` and aggregate `Razlika` when all visible child lines are counted.
- Keep the existing `Stanje sustava` summary text with batch count and total system quantity.

## W8-F-012: Completed Inventory should not use light full-row status backgrounds in dark mode

Status:
- open

Area:
- Inventory Count
- Completed inventory detail
- Frontend dark mode table styling

Source:
- User feedback and screenshot, 2026-04-08 19:48 CEST

User report:
- After finishing inventory and opening the completed detail screen, rows still use a light
  background in dark mode.

Expected behavior:
- Completed inventory should follow the same zebra-first table pattern as the rest of STOQIO.
- Status visibility should come from the status badge and value styling, not from a bright full-row
  background that breaks dark mode readability.

Recommended direction:
- Remove the completed-detail full-row status background override.
- Keep `ResolutionBadge` and colored `Razlika` text as the primary status signals.

## W8-F-013: Completed Inventory should group batch-tracked articles into one expandable parent row

Status:
- open

Area:
- Inventory Count
- Completed inventory detail
- Frontend batch presentation

Source:
- User feedback and screenshot, 2026-04-08 20:11 CEST

User report:
- On the completed inventory screen, the same batch-tracked article is listed multiple times, once
  per batch.
- The user expects the same grouped dropdown/expand behavior that already exists in the active
  inventory screen.

Expected behavior:
- Batch-tracked articles should appear as one parent row in completed inventory.
- Expanding the parent row should reveal the individual batches beneath it.
- Parent rows should summarize the grouped batches instead of repeating the article identity.

Recommended direction:
- Reuse the active-inventory batch grouping pattern in completed detail.
- Show aggregate counted quantity and aggregate difference on the parent row.
- Keep per-batch `Šarža`, `Rok valjanosti`, and status visible in expandable child rows.

## W8-F-014: Stock overview reports should value opening stock using configured initial average prices

Status:
- open

Area:
- Reports
- Stock overview valuation
- Backend pricing fallback

Source:
- User feedback and screenshot, 2026-04-08 20:12 CEST

User report:
- Articles have configured average prices, but the Reports screen still shows `0,00 €` for unit
  value, total value, and warehouse total value.

Expected behavior:
- Articles seeded through opening setup should contribute to report valuation.
- If current stock valuation is missing or zero, configured initial/prosječna cijena should be used
  as the value basis until newer stock pricing supersedes it.

Recommended direction:
- Treat `Article.initial_average_price` as a valuation fallback for stock overview when the current
  stock weighted average is unavailable or zero.
- Keep current weighted stock average as the highest-priority source when it is valid.

## W8-F-015: Warehouse article detail needs explicit barcode generation actions

Status:
- open

Area:
- Warehouse article detail
- Barcode UX
- Frontend + backend barcode actions

Source:
- User feedback and screenshots, 2026-04-08 20:27 CEST

User report:
- For non-batch articles there is a barcode field, but no nearby action to generate and fill a
  barcode value.
- For batch-tracked articles, FEFO rows expose `PDF` and `Printer`, but there is no explicit
  `Generiraj barkod` action in batch row actions.

Expected behavior:
- Non-batch article detail should offer an explicit `Generiraj` action beside the `Barkod` field.
- Batch rows under `Šarže (FEFO)` should expose a direct barcode generation action alongside label
  output actions.
- Generating a barcode should persist the value in the backend instead of only producing a PDF.

Recommended direction:
- Add dedicated generate endpoints for article and batch barcodes so UI generation is separate from
  PDF download and printer output.
- In article edit mode, place a `Generiraj` button next to the barcode input and write the returned
  value back into the form.
- In FEFO batch actions, add a `Generiraj` button before `PDF` and `Printer`.

## W8-F-016: Reports status column should show only the reorder indicator dot, and batch action label should be explicit

Status:
- open

Area:
- Reports stock overview
- Warehouse article detail FEFO actions
- Frontend microcopy / table UX

Source:
- User feedback and screenshot, 2026-04-08 20:39 CEST

User report:
- In Reports `Status`, the colored dot is fine, but a clipped green character appears beside it as if
  extra text is being cut off.
- In FEFO batch actions, the button label `Generiraj` is too vague and should explicitly say
  `Generiraj barkod`.

Expected behavior:
- The Reports status cell should show only the colored reorder indicator dot.
- FEFO batch action labels should clearly state what is being generated.

Recommended direction:
- Replace the stock-overview status badge with a dot-only indicator in the table cell.
- Rename the FEFO batch action button from `Generiraj` to `Generiraj barkod`.

## W8-F-017: Batch-tracked article detail should not show top-level article barcode output actions

Status:
- open

Area:
- Warehouse article detail
- Barcode UX
- Frontend action visibility

Source:
- User feedback and screenshot, 2026-04-08 20:44 CEST

User report:
- For articles with batches, the top-right action bar still shows article-level barcode output
  actions such as `Ispis barkoda (PDF)`.
- This is misleading because barcode output for batch-tracked articles should happen per batch.

Expected behavior:
- Non-batch articles should keep the top-right article barcode actions.
- Batch-tracked articles should not show article-level barcode PDF/printer actions in the header.
- Barcode output for batch-tracked articles should remain in `Šarže (FEFO) -> Akcije`.

Recommended direction:
- Hide top-level article barcode output actions when `article.has_batch === true`.
- Keep edit/deactivate actions visible in the header.
- Remove the related printer-configuration helper text from the header for batch articles as well.

## W8-F-018: After saving article edits, the detail page should return to the top

Status:
- open

Area:
- Warehouse article detail
- Frontend edit UX

Source:
- User feedback and screenshot, 2026-04-08 20:47 CEST

User report:
- When editing an article, the user scrolls down to reach `Spremi`.
- After saving, the page stays scrolled down, so the user must manually scroll back up to use
  header actions such as `Natrag na skladište`.

Expected behavior:
- After a successful article save, the detail page should return to the top automatically.

Recommended direction:
- Scroll the page back to the top after successful save and exit from edit mode.

## W8-F-019: Batch-tracked article create/edit forms should not expose article-level barcode field

Status:
- open

Area:
- Warehouse create article
- Warehouse article edit
- Frontend form UX / payload mapping

Source:
- User feedback and screenshot, 2026-04-08 20:49 CEST

User report:
- When creating or editing an article with `Artikl sa šaržom`, the form still shows the article-level
  `Barkod` field.
- This is inconsistent because the barcode belongs to the batch, not to the article.

Expected behavior:
- Create and edit forms should hide the article-level `Barkod` field whenever `Artikl sa šaržom` is
  enabled.
- Batch articles should not submit an article-level barcode value in the payload.

Recommended direction:
- Hide the form barcode field for batch articles in both create and edit flows.
- Clear any in-form article barcode when the user switches an article to batch-tracked mode.
- Send `barcode: null` for batch articles in the article mutation payload.

## W8-F-020: FEFO batch rows should show generated barcode state and prevent redundant generation clicks

Status:
- open

Area:
- Warehouse article detail
- FEFO batch barcode UX
- Frontend + backend detail payload

Source:
- User feedback, 2026-04-08 20:50 CEST

User report:
- After generating a batch barcode, the UI does not show the generated barcode anywhere.
- The `Generiraj barkod` button remains clickable, so it is unclear whether generation already
  happened or whether repeated clicks overwrite the old value.

Expected behavior:
- The generated barcode should be visible on the FEFO row for that batch.
- Once a batch already has a barcode, the generation action should become clearly non-repeatable in
  the UI.
- Repeated clicks should not silently create a different barcode value.

Recommended direction:
- Include `barcode` in the batch detail payload returned by article detail.
- Add a visible FEFO `Barkod` column.
- Disable the FEFO generate button when a batch barcode already exists and show a clear generated
  state label.
