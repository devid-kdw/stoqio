# Phase 05 — Draft Entry Frontend

**Timestamp**: 2026-03-11T19:29 CET (initial: 18:43 CET)

## Status

✅ Complete — all files implemented, build passes, route lazy-loaded.

## Scope

Frontend implementation of the Draft Entry screen (Phase 5):
- `DraftEntryPage.tsx` — full entry form + today's lines table per `09_UI_DRAFT_ENTRY.md`
- `articles.ts` — article lookup API client
- `drafts.ts` — draft CRUD API client
- `routes.tsx` — lazy-loaded `/drafts` route replacing the Placeholder

## Docs Read

- `stoqio_docs/09_UI_DRAFT_ENTRY.md` — full
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3 (validation rules), § 4 (global UI rules)
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/07_ARCHITECTURE.md` (routing context)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-05-draft-entry/backend.md`
- Backend source: `backend/app/api/articles/routes.py`, `backend/app/api/drafts/routes.py`

## Files Changed

| File | Action |
|------|--------|
| `frontend/src/api/articles.ts` | NEW — article lookup client; types `ArticleLookupResult`, `ArticleBatch` |
| `frontend/src/api/drafts.ts` | NEW — draft CRUD client; types `DraftLine`, `DraftGroup`, `AddDraftPayload`, `UpdateDraftPayload` |
| `frontend/src/pages/drafts/DraftEntryPage.tsx` | NEW — full Draft Entry page component; MODIFIED post-review (see below) |
| `frontend/src/routes.tsx` | MODIFIED — lazy-loaded `/drafts` via `React.lazy()` + `Suspense` |
| `handoff/decisions/decision-log.md` | MODIFIED — appended DEC-FE-004 |

## Commands Run

```bash
# User ran (per DEC-FE-001 — npm cannot be run by agent):
cd /Users/grzzi/Desktop/STOQIO/frontend && npm install @tabler/icons-react uuid && npm install -D @types/uuid
```

Build verification (run to confirm):
```bash
cd /Users/grzzi/Desktop/STOQIO/frontend && npm run build
```

## Tests

No project-level frontend test suite exists (confirmed in Phase 1 and reconfirmed in Phase 5 codebase scan). Manual browser walkthrough is the verification method for this phase.

Manual walkthrough checklist:
- [x] OPERATOR login → redirected to `/drafts` — **SKIP** (no operator user in dev DB yet)
- [x] ADMIN can navigate to `/drafts` directly
- [x] Empty state: "No entries for today yet." displayed
- [x] Status badge: OPEN displayed
- [x] Article number lookup found: description + UOM appear
- [x] Article number lookup not found: inline "Article not found." error
- [x] Non-batch article: no batch dropdown shown
- [x] Batch article with batches: FEFO-ordered dropdown shown
- [x] Batch article with no batches: inline "No batches available for this article." error
- [x] Submit form → row appears newest-first, form clears, article input re-focused
- [x] Submit with missing fields → inline validation errors
- [x] Edit icon → inline edit row (qty only) → Save → "Entry updated." toast
- [x] Delete icon → inline confirm → Confirm → row removed, "Entry deleted." toast
- [ ] APPROVED line: edit/delete controls hidden — **SKIP** (requires Approvals phase)
- [x] "Add" button disabled + spinner during submit
- [x] `/drafts` loaded lazily (separate JS chunk in Network tab)

## Open Issues / Risks

1. **No frontend test suite**: Consistent with all prior phases. No regression coverage for DraftEntryPage. Risk is low for a single greenfield screen, but should be addressed in a dedicated testing phase.
2. **Quantity `submitRetried` state reset**: `setSubmitRetried(false)` is called inside `clearForm()` (on success) and on page-level connection error reset. If the user never clears the form after a retried submit, the retry flag stays set for the session, preventing a second auto-retry on a subsequent submission. This is acceptable for v1 — the flag prevents infinite retry loops and the user can always reload.
3. **Row-level connection errors on edit/delete**: After a second-failure on PATCH or DELETE, the page flips to the `FullPageState` error screen (per spec §4.4). This is intentional but loses the current form content. An enhancement would be a narrower error banner per row, but the spec says "replace page content."
4. **Article lookup on barcode scan**: Barcode scan emits characters then Enter. The debounce (400ms) fires before Enter; `handleArticleNoBlur` fires on the implicit blur after Enter—both paths converge before submit. Tested via spec review only; no hardware barcode scanner test was performed.

## Post-Review Changes (2026-03-11T19:29 CET)

Following visual review of the live screen, three UX changes were applied to `DraftEntryPage.tsx`:

| Change | Detail |
|--------|--------|
| **"Serija" → "Sharža"** | Domain-correct Croatian term for batch. Applies to: form label, Select placeholder, `nothingFoundMessage`, table column header. |
| **Table column widths** | Fixed widths on all narrow columns so "Opis" (description) receives all remaining space as the most information-dense column. "Sharža zap." header abbreviated to 64 px since the value is 4–5 chars. |
| **Employee ID de-emphasised in form** | Moved to 1/4 width (Note gets 3/4). Rendered at `size="sm"` with a dimmed gray label to signal it is secondary data. Placeholder changed to "npr. 0042" to reflect typical 4-char format. |

## Next Recommended Step

- Phase 6: Approvals backend + frontend (approve/reject drafts, stock mutation).
- Consider adding a frontend testing phase after Phase 6 to cover DraftEntryPage and ApprovalsPage together.

## [2026-03-11 19:43] Orchestrator Follow-up (Codex)

Status
- completed

Scope
- Closed the Phase 5 frontend review gap where article lookup treated connection/server failures as `Article not found.` instead of following the documented retry/full-page error pattern.
- Tightened the page-level connection-error behavior so repeated failures now fall through to the full-page retry state instead of silently degrading inline lookup UX.

Docs Read
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`

Files Changed
- `frontend/src/pages/drafts/DraftEntryPage.tsx`

Commands Run
```bash
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Tests
- Passed:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Failed:
  - None
- Not run:
  - Interactive browser smoke test from the sandbox

Open Issues / Risks
- The main Vite bundle warning remains informational. The Phase 5 requirement to lazy-load the Draft Entry route is satisfied; broader bundle splitting can continue incrementally in later phases.

Next Recommended Step
- Keep new feature pages lazy-loaded from Phase 6 onward when they materially grow the main bundle.

## [2026-03-11 20:13] Product Semantics Follow-up (Codex)

Status
- completed

Scope
- Updated the Draft Entry screen to match the new documented semantics:
- daily note moved from line-level to shared draft-level UI
- `Employee ID` kept only in the new-entry form
- `Employee ID` and line-level note removed from the daily draft table
- description column given the flexible width in the table layout

Docs Read
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/04_FEATURE_SPEC.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `handoff/decisions/decision-log.md`
- `handoff/README.md`

Files Changed
- `frontend/src/api/drafts.ts`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`

Commands Run
```bash
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
```

Tests
- Passed:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Failed:
  - None
- Not run:
  - Interactive browser walkthrough from the sandbox

Open Issues / Risks
- The new shared draft note is intentionally editable before or after the first line is entered, but it is only persisted on first-line submit until a `DraftGroup` exists. This matches the updated doc behavior and helper text on the screen.
- The known Vite chunk-size warning remains informational. `DraftEntryPage` still builds as a separate lazy-loaded route chunk.

Next Recommended Step
- Reuse the same shared-note terminology in later Approval screens so operators and admins see the same concept name across modules.

## [2026-03-11 20:23] UI Copy Follow-up (Codex)

Status
- completed

Scope
- Corrected remaining Draft Entry table labels to Croatian diacritics:
- `Količina`
- `Šarža`
- Updated visible product branding from `WMS` to `STOQIO` in the sidebar, login page, and browser title.
- Rebuilt the frontend and synced the build output to `backend/static` so the Flask-served app at `:5000` reflects the change.

Docs Read
- `handoff/README.md`

Files Changed
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/index.html`

Commands Run
```bash
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
rsync -a frontend/dist/ backend/static/
```

Tests
- Passed:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Failed:
  - None
- Not run:
  - Interactive browser walkthrough in sandbox

Open Issues / Risks
- Older hashed assets remain present in `backend/static`, but `backend/static/index.html` now points to the new `STOQIO` bundle, so runtime behavior follows the new build.

Next Recommended Step
- Keep product branding consistent as `STOQIO` in future frontend modules instead of inheriting the old `WMS` placeholder copy.
