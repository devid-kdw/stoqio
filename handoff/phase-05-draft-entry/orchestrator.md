## Phase Summary

Phase
- Phase 5 - Draft Entry

Objective
- Deliver the Draft Entry module end to end and close post-review deviations from the Phase 5 spec.
- Ensure backend API, frontend UI, and automated verification align with `09_UI_DRAFT_ENTRY.md` and the global UI rules.

Source Docs
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 11
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 5
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3, § 4
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`

Delegation Plan
- Backend: implement draft CRUD, article lookup, FEFO batch support, and validators.
- Frontend: implement Draft Entry screen, lazy-loaded route, and required network/error handling behavior.
- Testing: add backend Draft Entry coverage and verify frontend lint/build.
- Orchestrator follow-up: review the phase against docs, fix any residual gaps directly, and record final validation.

Acceptance Criteria
- `OPERATOR` and `ADMIN` can use `/drafts`.
- Draft create/edit/delete and article lookup match the documented contract.
- Batch dropdown behavior follows FEFO and blocks submission when no batches exist.
- Global UI rules are respected, including one automatic retry and a full-page connection error state on repeated network/server failures.
- Phase 5 handoff trail is complete, including the orchestrator record.

Validation Notes
- Initial backend/frontend/testing deliveries were reviewed against the Phase 5 docs.
- Review found four concrete gaps:
  - transient `DraftGroup` creation conflicts could still surface as `409`
  - article lookup network/server failures were shown as `Article not found.`
  - backend trusted client-provided `uom` instead of article master data
  - one Draft Entry test claimed to verify “correct lines returned” without asserting the created line
- Orchestrator follow-up fixed those gaps in:
  - `backend/app/api/drafts/routes.py`
  - `backend/tests/test_drafts.py`
  - `frontend/src/pages/drafts/DraftEntryPage.tsx`
- Phase 5 handoff files were updated with explicit orchestrator follow-up entries so the fix ownership is traceable.
- Re-verified after the follow-up:
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q` → `25 passed`
  - `backend/venv/bin/pytest backend/tests -q` → `72 passed`
  - `cd frontend && npm run lint -- --max-warnings=0` → pass
  - `cd frontend && npm run build` → pass
- Remaining frontend bundle warning:
  - Vite still reports the known >500 kB main chunk warning
  - `DraftEntryPage` is lazy-loaded into its own chunk, so this remains informational only for Phase 5

Next Action
- Phase 5 can be closed.
- Proceed to Phase 6 - Approvals.

## [2026-03-11 20:13] Docs-First Product Follow-up (Codex)

Objective
- Apply the user-approved product change before further Phase 5 work:
- remove line-level note from Draft Entry
- make note shared at the daily draft (`DraftGroup`) level
- keep `Employee ID` as optional input only
- remove `Employee ID` and note from the daily draft table so description gets maximum horizontal space

Docs Updated First
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/04_FEATURE_SPEC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/06_SESSION_NOTES.md`
- `handoff/decisions/decision-log.md` (`DEC-PROD-001`)

Implementation Follow-up
- Backend:
  - `DraftGroup.description` is now the active note field in the Draft Entry workflow
  - `POST /api/v1/drafts` accepts `draft_note` for first-line creation
  - `PATCH /api/v1/drafts/group` updates the shared daily note
  - line-level `note` is no longer part of the active Phase 5 response flow
- Frontend:
  - Draft Entry page now edits/displays a single daily draft note
  - daily table no longer shows note or employee columns
  - description is the flexible-width column
- Testing:
  - backend Draft Entry tests were updated to assert the shared draft note contract
  - full backend suite, frontend lint, and frontend build were re-run

Verification
- `backend/venv/bin/pytest backend/tests/test_drafts.py -q` → `29 passed`
- `backend/venv/bin/pytest backend/tests -q` → `76 passed`
- `cd frontend && npm run lint -- --max-warnings=0` → pass
- `cd frontend && npm run build` → pass

Residual Notes
- Browser-level smoke testing was not repeated from the sandbox.
- The existing Vite chunk-size warning remains informational only; `DraftEntryPage` still builds as its own lazy-loaded chunk.

Next Action
- Treat Phase 5 as closed under the updated documentation baseline.
- Use the new daily-draft note semantics as source of truth for Phase 6 Approvals work.

## [2026-03-11 20:23] UI Copy Follow-up (Codex)

Objective
- Close the remaining visible Phase 5 copy/branding inconsistencies after the Draft Entry follow-up:
- `Kolicina` -> `Količina`
- `Sarza` -> `Šarža`
- `WMS` -> `STOQIO`

Implementation
- Updated the Draft Entry table headers in `frontend/src/pages/drafts/DraftEntryPage.tsx`.
- Updated product branding in:
  - `frontend/src/components/layout/Sidebar.tsx`
  - `frontend/src/pages/auth/LoginPage.tsx`
  - `frontend/index.html`
- Rebuilt the frontend and synced `frontend/dist` into `backend/static` so the Flask-served UI on `:5000` reflects the new bundle.

Verification
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- `backend/static/index.html` now points to the `STOQIO` bundle

Next Action
- Continue using `STOQIO` as the product name in future user-facing frontend work unless a later branding decision supersedes it.
