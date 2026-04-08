## Phase Summary

Phase
- Wave 8 - Phase 3 - Frontend Orders and Settings Copy Fixes

Objective
- Remediate W8-F-005 and W8-F-006:
  purchase order article selection should autofill supplier article code, and Settings section
  headings/action copy should be Croatian.

Source Docs
- `handoff/README.md`
- `handoff/wave-08/README.md`
- `handoff/Findings/wave-08-user-feedback.md`
- `frontend/src/api/orders.ts`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx`
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/orders/__tests__/OrderDetailPage.test.tsx`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`
- `stoqio_docs/18_UI_SETTINGS.md`
- `backend/app/services/order_service.py` (read-only contract reference)
- `backend/tests/test_orders.py` (read-only contract reference)

Current Repo Reality
- Backend Orders article lookup already returns `supplier_article_code` and `last_price` when
  called with `supplier_id` and a matching `ArticleSupplier` link exists.
- `OrdersPage.tsx` fills `supplierArticleCode` from `selectedArticle.supplier_article_code` when
  present, so the bug is likely stale frontend lookup/select state.
- `SettingsPage.tsx` hardcodes English section titles and mixed save-button copy:
  `General`, `Roles`, `UOM Catalog`, `Article Categories`, `Quotas`, `Barcode`, `Export`,
  `Suppliers`, `Users`.

Contract Locks / Clarifications
- Do not change backend Orders routes or response shapes unless investigation proves frontend is
  already sending the correct `supplier_id` and backend returns wrong data.
- In order creation, article lookup must include the currently selected supplier id.
- If selected supplier changes, clear or refresh line article selections/options so a supplier
  article code from the wrong supplier cannot remain.
- Keep supplier article code manually editable when no linked code exists.
- Settings visible section labels should be Croatian:
  - `1. Općenito`
  - `2. Role`
  - `3. Mjerne jedinice`
  - `4. Kategorije artikala`
  - `5. Kvote`
  - `6. Barkodovi`
  - `7. Izvoz`
  - `8. Dobavljači`
  - `9. Korisnici`
- Translate adjacent save buttons and short labels that combine Croatian verbs with English nouns
  (for example `Spremi General`, `Spremi Roles`, `Spremi Barcode`, `Spremi Export`).

File Ownership
- `frontend/src/api/orders.ts`
- `frontend/src/pages/orders/OrdersPage.tsx`
- `frontend/src/pages/orders/OrderDetailPage.tsx` (only if same stale supplier context exists there)
- `frontend/src/pages/orders/orderUtils.ts`
- `frontend/src/pages/orders/__tests__/*`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/__tests__/localized-copy-smoke.test.tsx`
- `stoqio_docs/18_UI_SETTINGS.md`
- `handoff/wave-08/phase-03-wave-08-orders-and-settings-frontend/frontend.md`

Delegation Plan
- Frontend worker implements Orders autofill/stale-state fix and Settings localization.

Acceptance Criteria
- Creating a purchase order with selected supplier + article autofills `Šifra artikla dobavljača`
  from the article's supplier link.
- Changing supplier clears or refreshes supplier-specific article code state.
- Settings section headings and adjacent save actions are Croatian.
- Existing localized-copy smoke tests are updated or new targeted coverage is added if feasible.
- Frontend build and lint pass.

Validation Notes
- 2026-04-08: Orchestrator created Wave 8 Phase 3 from user feedback intake.

Next Action
- Frontend worker implements and records `frontend.md`.

---

## Delegation Prompt - Frontend Worker

You are the frontend worker for STOQIO Wave 8 Phase 3.

Read the files listed above before editing. You are not alone in the codebase: another frontend
worker owns Inventory/Warehouse files. Do not edit Inventory or Warehouse article files. Do not
revert or overwrite unrelated changes.

Implement the Orders and Settings fixes described here. Run `npm run build` and `npm run lint` if
feasible. Write your handoff entry to
`handoff/wave-08/phase-03-wave-08-orders-and-settings-frontend/frontend.md` using the standard
agent template.
