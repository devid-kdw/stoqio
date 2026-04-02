## [2026-04-02] Frontend Agent — Phase 9 Wave 02: Docs Alignment and Handoff Reorg

### Status
Done

### Scope
Aligned barcode / settings / domain / UI documentation with the accepted current baseline.
Made one live-copy cleanup in `SettingsPage.tsx` (Pi-ja → host-generic wording).
No feature code was added or changed.

### Docs Read
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
- `stoqio_docs/04_FEATURE_SPEC.md`
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/18_UI_SETTINGS.md`
- `backend/app/services/settings_service.py` (confirmed barcode settings payload: barcode_format, barcode_printer, label_printer_ip, label_printer_port, label_printer_model)
- `backend/app/api/articles/routes.py` (confirmed GET PDF + POST direct-print routes; both ADMIN-only)
- `frontend/src/api/settings.ts`
- `frontend/src/api/articles.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `handoff/implementation/phase-15-barcodes-export/orchestrator.md`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/orchestrator.md`
- `handoff/wave-02/phase-09-wave-02-docs-alignment-and-handoff-reorg/backend.md`
- `handoff/README.md`

### Files Changed

**Runtime code**
- `frontend/src/pages/settings/SettingsPage.tsx` — line 1845: barcode printer `description` prop changed from `"Naziv printera u OS-u Pi-ja za PDF ispis barkoda."` to `"Naziv printera u OS-u hosta za PDF ispis barkoda."`. Only this one substring changed; no logic, structure, or other copy touched.

**Documentation**
- `stoqio_docs/18_UI_SETTINGS.md`
  - Section 8 (Barcode) completely rewritten into four subsections: 8.1 barcode format, 8.2 PDF download printing (barcode_printer), 8.3 direct host printing (label_printer_ip / label_printer_port / label_printer_model), 8.4 future raw-label mode (not implemented).
  - Pi-only wording removed; replaced with host-generic wording throughout.
  - API table: added four barcode/print endpoints (GET PDF + POST direct-print for articles and batches).
  - Edge-cases table: updated barcode_printer entry; added two direct-print error cases.

- `stoqio_docs/13_UI_WAREHOUSE.md`
  - Section 5.5 Article Actions: split "Ispis barkoda" into two distinct ADMIN-only actions — PDF download (Preuzmi PDF barkoda → GET) and direct print (Ispis barkoda → POST).
  - Section 7 (Barcode Printing): rewritten into three subsections — 7.1 PDF download, 7.2 Direct host printing, 7.3 Future raw-label mode (not implemented). ADMIN-only scope stated explicitly. MANAGER scope confirmed (no print actions).
  - Section 9 API table: renamed old "Print barcode" GET rows; added two POST direct-print rows.

- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
  - Section 2.4 (Barkodovi): replaced vague "PDF ili direktno na printer" with four-layer breakdown: generation, PDF download (with endpoints), direct host printing (with endpoints + ADMIN-only note), future raw-label mode (not implemented).
  - Section 15 (Settings persistence): expanded SystemConfig description from prose to explicit key list — all seven current keys listed (`default_language`, `barcode_format`, `barcode_printer`, `label_printer_ip`, `label_printer_port`, `label_printer_model`, `export_format`).

- `stoqio_docs/04_FEATURE_SPEC.md`
  - Section 5 (Warehouse) Barkodovi block: replaced single "Print barkoda (PDF ili direktno na printer)" line with three lines — PDF download (with endpoints), direct print (with endpoints + label_printer_ip requirement), future raw-label mode (not implemented).
  - Section 10 (Settings) list: added `label_printer_ip`, `label_printer_port`, `label_printer_model`, and `barcode_printer` as distinct settings entries.

### Commands Run

```bash
# Pi / barcode reference verification
grep -rn "Raspberry Pi|Pi-ja|Pi-u" stoqio_docs/02_DOMAIN_KNOWLEDGE.md stoqio_docs/04_FEATURE_SPEC.md stoqio_docs/13_UI_WAREHOUSE.md stoqio_docs/18_UI_SETTINGS.md frontend/src/pages/settings/SettingsPage.tsx
# → 0 hits

# Barcode endpoint presence verification in docs
grep -n "/barcode|barcode/print|label_printer_|barcode_printer" stoqio_docs/13_UI_WAREHOUSE.md stoqio_docs/18_UI_SETTINGS.md
# → all expected hits present; both GET PDF and POST direct-print routes documented

cd frontend && npm run lint -- --max-warnings=0
# → exit 0, no warnings

cd frontend && npm run build
# → ✓ built in 2.72s, zero errors
```

### Tests
No runtime product tests added. Docs-only changes not covered by automated test suite.
Lint and build verified clean — no regressions from the one-line SettingsPage.tsx change.

### Open Issues / Risks
- `stoqio_docs/06_SESSION_NOTES.md` still contains Pi references as historical session context. These are session notes rather than active guidance and were not in scope for this phase. (Same note as backend agent made.)
- Historical handoff docs in `handoff/implementation/` and `handoff/decisions/decision-log.md` retain Pi wording as immutable historical truth.
- The `barcode_printer` field is stored in the settings payload but does not programmatically drive the current direct ZPL print path. This distinction is now documented explicitly in `18_UI_SETTINGS.md` §8.2 and `02_DOMAIN_KNOWLEDGE.md` §2.4.

### Next Recommended Step
None — this phase is complete. All four owned docs are aligned. Pi-ja live copy removed. Lint and build green.
