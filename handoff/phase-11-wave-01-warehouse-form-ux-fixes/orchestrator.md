## Phase Summary

Phase
- Wave 1 - Phase 11 - Warehouse Form UX Fixes

Objective
- Fix two small UX issues on the Warehouse article create/edit form.
- Improve repeated article-entry flow for ADMIN users creating multiple articles.
- Tighten the click target of the Warehouse form switches so empty row space does not toggle them unexpectedly.

Source Docs
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-WH-005`, `DEC-WH-006`, `DEC-WH-007`, `DEC-WH-008`)
- `handoff/phase-09-warehouse/orchestrator.md`
- `handoff/phase-03-wave-01-article-aliases/orchestrator.md`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Current Repo Reality
- New article creation currently happens from the Warehouse list page modal in `frontend/src/pages/warehouse/WarehousePage.tsx`.
- After a successful create, the current flow shows the success toast, closes the modal, and navigates to `/warehouse/articles/{id}`.
- Existing article edits happen in `frontend/src/pages/warehouse/ArticleDetailPage.tsx`, and successful save currently keeps the user on the article detail screen. That behavior is already correct for this wave.
- The two boolean article controls (`has_batch`, `is_active`) are rendered in the shared `frontend/src/pages/warehouse/WarehouseArticleForm.tsx` via Mantine `Switch` components inside a `SimpleGrid`.
- There is no obvious custom row-level `onClick` handler around those switches today, so the reported bug is likely caused by the rendered hit area/layout rather than explicit container click logic.
- No backend/API change is needed for either requested UX fix.

Contract Locks / Clarifications
- Frontend-only phase. Do not change backend routes, payloads, or tests in this wave.
- Fix 1 applies only to the New Article flow:
  - after successful `POST /api/v1/articles`, redirect to `/warehouse`
  - do not redirect to `/warehouse/articles/{id}`
- Edit Article flow must remain unchanged:
  - after successful update of an existing article, the user stays on the article detail view
- Switch hit-area behavior is fixed as follows:
  - only the `Switch` control itself and its label text may toggle the value
  - empty space to the right inside the same layout row must not toggle the value
  - do not rely on a wider wrapping `Group`, `Stack`, `SimpleGrid` cell, or custom container click handler to change the switch state
- Keep the visible labels as they are today:
  - `"Artikl sa šaržom"`
  - `"Aktivan artikl"`
- Keep the rest of the Warehouse form behavior unchanged:
  - validation
  - supplier rows
  - create/edit payload shape
  - existing success/error toasts
  - ADMIN/MANAGER RBAC behavior

Delegation Plan
- Backend:
- None. No backend changes are needed in this phase.
- Frontend:
- Fix the post-create redirect and constrain the Warehouse form switch hit areas without disturbing the accepted Warehouse baseline.
- Testing:
- None. Verification for this frontend-only phase is lint, build, and explicit manual UX checks recorded by the frontend agent.

Acceptance Criteria
- Create new article -> save -> user lands on `/warehouse`, not `/warehouse/articles/{id}`.
- Edit existing article -> save -> user remains on the article detail screen, unchanged from current behavior.
- Clicking empty horizontal space to the right of `"Artikl sa šaržom"` does not toggle the switch.
- Clicking empty horizontal space to the right of `"Aktivan artikl"` does not toggle the switch.
- Clicking directly on either switch control toggles it normally.
- Existing Warehouse create/edit validation and submission behavior remain intact.
- The phase leaves a complete orchestration and frontend handoff trail for this frontend-only change.

Validation Notes
- None yet.

Next Action
- Delegate to the Frontend Agent only.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 11 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/13_UI_WAREHOUSE.md` § 4, § 5, § 6
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-WH-005`, `DEC-WH-006`, `DEC-WH-007`, `DEC-WH-008`)
- `handoff/phase-09-warehouse/orchestrator.md`
- `handoff/phase-11-wave-01-warehouse-form-ux-fixes/orchestrator.md`
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Goal
- Fix two small Warehouse form UX issues without changing backend behavior:
  - new-article post-save redirect
  - switch clickable area

Non-Negotiable Contract Rules
- Do not change backend/API contracts in this phase.
- New Article flow only:
  - after successful `articlesApi.create(...)`, redirect to `/warehouse`
  - do not redirect to `/warehouse/articles/{id}`
- Edit Article flow stays unchanged:
  - successful update of an existing article must keep the user on article detail
- Switch hit areas:
  - only the switch itself and its label text should toggle the control
  - empty space to the right in the same row/cell must not toggle
  - no surrounding container should have an `onClick` that toggles these fields
- Keep the current visible labels:
  - `Artikl sa šaržom`
  - `Aktivan artikl`
- Do not broaden this into a general Warehouse form redesign.

Tasks
1. Update `frontend/src/pages/warehouse/WarehousePage.tsx`:
   - change the successful create flow so it redirects to `/warehouse`
   - keep the existing success toast and modal-close/reset behavior
2. Leave `frontend/src/pages/warehouse/ArticleDetailPage.tsx` edit-save behavior unchanged unless a tiny refactor is needed to preserve the current detail-page outcome explicitly.
3. Update `frontend/src/pages/warehouse/WarehouseArticleForm.tsx` so the clickable/interactive area for the two switches is limited appropriately:
   - verify that clicking empty space to the right does not toggle
   - keep direct switch interaction normal
4. Keep the rest of the form behavior intact:
   - field validation
   - supplier management
   - payload building
   - loading/disabled states
5. Prefer the smallest, local frontend change that fixes the UX issue cleanly.

Verification
- Run at minimum:
  - `cd frontend && npm run lint -- --max-warnings=0`
  - `cd frontend && npm run build`
- Manually verify and record:
  - Create a new article -> save -> lands on `/warehouse`
  - Edit an existing article -> save -> remains on article detail
  - Clicking to the right of `Artikl sa šaržom` does not toggle the switch
  - Clicking directly on the `Artikl sa šaržom` switch toggles it
  - Clicking to the right of `Aktivan artikl` does not toggle the switch
  - Clicking directly on the `Aktivan artikl` switch toggles it

Handoff Requirements
- Append your work log to `handoff/phase-11-wave-01-warehouse-form-ux-fixes/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, lint/build results, manual verification notes, open issues, and assumptions.
- If you discover a contract mismatch or hidden dependency that would require backend changes, log it immediately in handoff instead of silently broadening scope.

Done Criteria
- New article save redirects to `/warehouse`.
- Existing article edit save behavior remains unchanged.
- The two switches no longer toggle from empty right-side row space.
- Verification is recorded in handoff.

## [2026-03-24 22:13] Orchestrator Validation - Wave 1 Phase 11 Warehouse Form UX Fixes

Status
- accepted

Scope
- Reviewed the delivered frontend-only changes for the Warehouse create/edit UX fixes.
- Compared the implementation against the locked frontend-only contract for post-create redirect and switch hit-area behavior.
- Re-ran frontend verification on the delivered code.

Docs Read
- `handoff/phase-11-wave-01-warehouse-form-ux-fixes/orchestrator.md`
- `handoff/phase-11-wave-01-warehouse-form-ux-fixes/frontend.md`
- `handoff/phase-09-warehouse/orchestrator.md`

Files Reviewed
- `frontend/src/pages/warehouse/WarehousePage.tsx`
- `frontend/src/pages/warehouse/WarehouseArticleForm.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Commands Run
- `git diff -- frontend/src/pages/warehouse/WarehousePage.tsx frontend/src/pages/warehouse/WarehouseArticleForm.tsx frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`

Validation Result
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed

Accepted Work
- New article create flow now returns the user to `/warehouse` instead of navigating to article detail.
- Existing article edit-save behavior remains unchanged because `ArticleDetailPage.tsx` save flow was not broadened or regressed.
- The two Warehouse form switches are now wrapped so their effective interactive area is constrained to the control/label region instead of the full grid-cell width.
- The changes stay tightly scoped to the requested frontend UX fixes and do not alter Warehouse API usage, validation rules, or payload shape.

Findings
- None. No blocking bugs or contract mismatches were found in the delivered Phase 11 wave changes.

Residual Notes
- Browser interaction was not independently replayed by the orchestrator in this review pass. Acceptance is based on code-path review plus the frontend handoff's recorded manual verification and green lint/build results.

Next Action
- Wave 1 Phase 11 can be treated as formally closed.
