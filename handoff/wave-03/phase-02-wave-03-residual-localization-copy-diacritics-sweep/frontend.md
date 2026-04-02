# Frontend Handoff — Wave 3 Phase 2: Residual Localization / Copy / Diacritics Sweep

---

## Entry 1 — 2026-04-02

### Status

Complete. All mandatory and sweep-identified user-visible English, mixed, and no-diacritic strings in the targeted flows have been corrected. Functional behavior is unchanged.

### Scope

Copy cleanup only across four targeted files:
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

No shared components (SetupGuard, FullPageState, http.ts) required changes — they were already Croatian-first.

### Docs Read

- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/orchestrator.md`
- `handoff/wave-03/phase-01-wave-03-runtime-language-switching-and-locale-foundation/frontend.md`
- `handoff/wave-03/phase-02-wave-03-residual-localization-copy-diacritics-sweep/orchestrator.md`
- All four targeted source files (read in full before editing)

### Files Changed

- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/pages/auth/SetupPage.tsx`
- `frontend/src/pages/receiving/ReceivingPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

### Strings Fixed — DraftEntryPage.tsx

| Before | After |
|---|---|
| `No batches available for this article.` (inline lookup + validate) | `Nema dostupnih šarži za ovaj artikl.` |
| `Article not found.` (inline lookup + validate) | `Artikl nije pronađen.` |
| `Article number is required.` | `Broj artikla je obavezan.` |
| `Article not resolved. Please wait for lookup.` | `Artikl još nije razriješen. Pričekaj dovršetak pretrage.` |
| `Quantity is required.` | `Količina je obavezna.` |
| `Quantity must be greater than 0.` (validate + saveEdit toast) | `Količina mora biti veća od 0.` |
| `Batch is required.` | `Šarža je obavezna.` |
| `Failed to add entry. Please try again.` | `Dodavanje unosa nije uspjelo. Pokušajte ponovo.` |
| `Failed to update draft note.` | `Ažuriranje napomene nije uspjelo.` |
| `Failed to update entry.` | `Ažuriranje unosa nije uspjelo.` |
| `Failed to delete entry.` | `Brisanje unosa nije uspjelo.` |

### Strings Fixed — SetupPage.tsx

| Before | After |
|---|---|
| `Location name is required.` | `Naziv lokacije je obavezan.` |
| `Location name must be 100 characters or fewer.` | `Naziv lokacije smije imati najviše 100 znakova.` |
| `Timezone is required.` | `Vremenska zona je obavezna.` |
| `Initial setup completed successfully.` | `Inicijalno postavljanje uspješno dovršeno.` |
| `Setup failed. Please try again.` | `Postavljanje nije uspjelo. Pokušajte ponovo.` |
| `npr. Skladiste Tvornica d.o.o.` (placeholder) | `npr. Skladište Tvornica d.o.o.` |

### Strings Fixed — ReceivingPage.tsx

| Before | After |
|---|---|
| `This order is already closed.` | `Ova narudžbenica je već zatvorena.` |
| `Article not found.` (resolveArticle + validateAdhoc) | `Artikl nije pronađen.` |
| `Kolicina je obavezna.` (linked + adhoc validation) | `Količina je obavezna.` |
| `Kolicina mora biti veca od 0.` (linked + adhoc validation) | `Količina mora biti veća od 0.` |
| `Artikl jos nije razrijesen. Pricekaj dovrsetak pretrage.` | `Artikl još nije razriješen. Pričekaj dovršetak pretrage.` |
| `Broj dostavnice smije imati najvise 100 znakova.` (linked + adhoc) | `Broj dostavnice smije imati najviše 100 znakova.` |
| `Napomena smije imati najvise 1000 znakova.` (linked + adhoc) | `Napomena smije imati najviše 1000 znakova.` |
| `A note is required for ad-hoc receipts.` (frontend validation) | `Napomena je obavezna za ad-hoc zaprimanja.` |
| `Batch code je obavezan.` (linked + adhoc validation) | `Kod šarže je obavezan.` |
| `Batch code ima neispravan format.` (linked + adhoc validation) | `Kod šarže ima neispravan format.` |
| `Receipt recorded.` (linked + adhoc success toast) | `Zaprimanje evidentirano.` |
| `<Table.Th>Batch code</Table.Th>` | `<Table.Th>Kod šarže</Table.Th>` |
| `<Table.Th>Expiry date</Table.Th>` | `<Table.Th>Datum isteka</Table.Th>` |
| `Confirm Receipt` (linked submit button) | `Potvrdi zaprimanje` |
| `Confirm Receipt` (adhoc submit button) | `Potvrdi zaprimanje` |
| `Batch tracking: Da/Ne` | `Praćenje šarže: Da/Ne` |
| `label="Batch code"` (adhoc form) | `label="Kod šarže"` |
| `label="Expiry date"` (adhoc form) | `label="Datum isteka"` |

### Strings Fixed — DraftGroupCard.tsx

| Before | After |
|---|---|
| `Ucitavanje detalja drafta nije uspjelo.` (x2, fetchDetail fallback) | `Učitavanje detalja drafta nije uspjelo.` |
| `Kolicina mora biti veca od nule.` | `Količina mora biti veća od nule.` |
| `Azuriranje kolicine nije uspjelo.` (x2, handleSaveEdit fallback) | `Ažuriranje količine nije uspjelo.` |
| `Nema dostupnog sadrzaja.` | `Nema dostupnog sadržaja.` |

### Intentionally Not Changed

- Backend-message passthrough comparison strings in ReceivingPage.tsx:
  - `message === 'At least one line must be received.'` (line ~681) — this is control-flow logic that compares against a backend-returned message, not a frontend-authored string. If the backend localizes this, the comparison will need updating on the backend side. Logged here for the backend agent.
  - `message === 'A note is required for ad-hoc receipts.'` (line ~775) — same pattern; backend passthrough routing check, not changed.
- API enum values displayed in status badges (PENDING, APPROVED, REJECTED, PARTIAL) in DraftGroupCard — these are machine-readable API identifiers displayed as badges; the spec contract prohibits translating them.
- `e.status` in nested operator entry rows in DraftGroupCard — same reasoning.

### Commands Run

```
grep -n "Receipt recorded|Initial setup completed|Quantity must be greater than 0|Ucitavanje|Kolicina|Azuriranje|Confirm Receipt|Batch code|Expiry date" [targeted files]
# → No matches found

cd frontend && CI=true npm run test
# → 8 test files passed, 32 tests passed

cd frontend && npm run lint -- --max-warnings=0
# → Clean, no warnings

cd frontend && npm run build
# → Built in 3.11s, no errors
```

### Tests

- `CI=true npm run test`: 8 passed / 32 passed — no regressions.
- Lint: 0 warnings, 0 errors.
- Build: clean.

No new test files added in this phase. The copy changes are in string literals and do not require new unit test logic — the existing test suite covers component rendering and validation behavior structurally.

### Open Issues / Risks

- **Backend passthrough comparison — `At least one line must be received.`**: The frontend routes this specific backend message to `setLinkedFormError`. If the backend i18n layer changes this message text, the routing condition will silently stop matching. The backend agent should confirm whether this string is already covered in the backend i18n catalog (`backend/app/utils/i18n.py`) or needs a targeted patch.
- **Backend passthrough comparison — `A note is required for ad-hoc receipts.`**: Same concern. Frontend routes this to the note field error. Backend agent should confirm coverage.
- **DraftGroupCard status badges**: PENDING / APPROVED / REJECTED / PARTIAL are displayed as raw API enum values in badges (both summary-level and row-level). DraftEntryPage.tsx already translates these for its own status display. This is a display inconsistency but out of scope for this phase since it requires behavioral logic not just copy replacement.

### Next Recommended Step

- Backend agent: audit whether `At least one line must be received.` and `A note is required for ad-hoc receipts.` are covered in the backend i18n catalog for the receiving flow.
- Testing agent: add regression assertions for the concrete string replacements in the four targeted components.
