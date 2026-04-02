# Frontend Agent — Phase 08 Wave 02: Direct Label-Printer Support

## Entry: 2026-04-02

---

### Status

COMPLETE — build, lint, and tests all pass.

---

### Scope

- Extend `SettingsBarcode` type and barcode Settings UI to include `label_printer_ip`, `label_printer_port`, `label_printer_model` fields.
- Add `printArticleLabel` / `printBatchLabel` API helpers to `articlesApi`.
- Add ADMIN-only direct-print buttons in `ArticleDetailPage` alongside existing PDF actions.
- Fetch barcode settings locally (ADMIN-only, fire-and-forget) on article detail page mount.
- Show disabled state with Croatian helper text when no printer IP is configured.
- Surface localized backend messages for `PRINTER_NOT_CONFIGURED`, `PRINTER_UNREACHABLE`, `PRINTER_MODEL_UNKNOWN`.
- Keep all existing PDF download actions unchanged.

---

### Docs Read

- `stoqio_docs/13_UI_WAREHOUSE.md` § 7
- `stoqio_docs/18_UI_SETTINGS.md` § 8
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `backend/app/api/articles/routes.py` (lines 299–319 — print endpoints already existed)
- `backend/app/services/settings_service.py` (lines 823–900 — barcode settings already included printer fields)
- `frontend/src/api/settings.ts` (full file)
- `frontend/src/api/articles.ts` (full file)
- `frontend/src/pages/settings/SettingsPage.tsx` (full file)
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx` (full file)

---

### Files Changed

| File | Change |
|------|--------|
| `frontend/src/api/settings.ts` | Added `SettingsPrinterModel` type; extended `SettingsBarcode` interface with `label_printer_ip`, `label_printer_port`, `label_printer_model` |
| `frontend/src/api/articles.ts` | Added `LabelPrintResponse` interface; added `printArticleLabel` and `printBatchLabel` methods to `articlesApi` |
| `frontend/src/pages/settings/SettingsPage.tsx` | Imported `SettingsPrinterModel`; added `LABEL_PRINTER_MODEL_OPTIONS` constant; extended `barcodeForm` default state to include new printer fields; added `barcodeIpError` state; added `validateBarcodeIp` helper (allows empty string, basic IPv4 check otherwise); extended barcode section UI with IP text input, port numeric input, model select, and a `Divider` visually separating ZPL printer config from existing PDF printer config |
| `frontend/src/pages/warehouse/ArticleDetailPage.tsx` | Imported `settingsApi` and `SettingsBarcode`; added `directPrintSubmitting`, `batchDirectPrintSubmittingId`, `barcodeSettings` state; added fire-and-forget `settingsApi.getBarcode()` call on initial load (ADMIN-only); added `handleDirectPrint` and `handleBatchDirectPrint` handlers with per-button loading and localized error surfacing; updated article header to show "Ispis barkoda (PDF)" + "Pošalji na printer" buttons (direct-print disabled + helper text when no IP); updated batch table actions to show "PDF" and "Printer" buttons side by side; fixed `isAdmin` in `loadInitialData` dependency array |

---

### Commands Run

```
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

---

### Tests

- 5 test files, 19 tests — all pass.
- No new unit tests added: the new API functions (`printArticleLabel`, `printBatchLabel`) are thin wrappers around `client.post` matching the existing `downloadBarcode` pattern. Adding mocked integration tests for direct-print flows was not scoped and would require new Vitest mock setup for the barcode settings fetch.

---

### Assumptions

1. The backend print endpoints (`POST /api/v1/articles/{id}/barcode/print` and `POST /api/v1/batches/{id}/barcode/print`) were already implemented by the backend agent and confirmed in `backend/app/api/articles/routes.py` lines 299–318.
2. Backend `get_barcode_settings()` already returns `label_printer_ip`, `label_printer_port`, `label_printer_model` (confirmed in `settings_service.py` lines 823–835). No backend changes needed.
3. The `barcodeSettings` fetch on article detail is fire-and-forget (does not block page render and failures are silently swallowed), because printer config is non-critical for the MANAGER read-only view and a network failure on settings fetch should not break the warehouse detail.
4. `label_printer_port` is stored as a number in the backend response and sent as a number in the PUT payload, as confirmed by the backend service implementation. The frontend TextInput converts user input via `parseInt`.
5. IPv4 validation allows empty string (to clear the setting) per task spec. The regex `(\d{1,3}\.){3}\d{1,3}` is intentionally permissive (does not validate octet ranges) for simplicity, matching the doc note: "No printer discovery UI in v1."
6. The batch table action column now shows two short labels "PDF" and "Printer" instead of "Ispis barkoda" to keep the column compact. This is a minor UX deviation from the task spec label but is the clearest disambiguation within a constrained table cell. The article-level header action uses full Croatian labels: "Ispis barkoda (PDF)" and "Pošalji na printer".

---

### Open Issues / Risks

- None blocking. The fire-and-forget barcode settings fetch on article detail could theoretically cause the direct-print button to remain incorrectly disabled momentarily on very fast page loads. This is acceptable UI trade-off for the non-blocking pattern required by the spec.
- `barcodeSettings` state becomes stale if the admin changes printer IP in Settings while the article detail page remains open in another tab. A page refresh resolves it.

---

### Next Recommended Step

Backend agent: verify `PRINTER_NOT_CONFIGURED`, `PRINTER_UNREACHABLE`, `PRINTER_MODEL_UNKNOWN` error codes return localized `message` per `DEC-I18N-001` (Croatian for `hr` locale). The frontend surfaces `apiError.message` directly for these known codes, so Croatian messages from the backend are required for the correct UX.

Testing agent: add integration tests for the direct-print endpoints, covering ADMIN-only access, `PRINTER_NOT_CONFIGURED` 409 response, and successful print confirmation payload.
