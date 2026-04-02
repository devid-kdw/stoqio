## Phase Summary

Phase
- Wave 1 - Phase 5 - Rejection Reason Visibility

Objective
- Fix the draft-rejection flow so rejection reason becomes optional instead of mandatory.
- Surface saved rejection reasons where users actually need them: Approvals history and Draft Entry.
- Add an operator-facing "My entries today" view without regressing the existing shared daily-draft workflow from Phase 5 and Phase 16.

Source Docs
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-PROD-001`, `DEC-BE-013`)
- `handoff/implementation/phase-05-draft-entry/orchestrator.md`
- `handoff/implementation/phase-06-approvals/orchestrator.md`
- `handoff/implementation/phase-06-approvals-followup/orchestrator.md`
- `handoff/implementation/phase-16-v1-stabilization/orchestrator.md`
- `backend/app/api/approvals/routes.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/tests/test_approvals.py`
- `frontend/src/api/approvals.ts`
- `frontend/src/api/drafts.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`

Current Repo Reality
- Both rejection routes currently reject blank reasons at the route layer with `400 VALIDATION_ERROR`.
- Rejection notes are already persisted on `ApprovalAction.note`, but the approvals API does not expose them in the history/detail payload used by the UI.
- Draft Entry line payloads already expose `status`, but not `rejection_reason`.
- `GET /api/v1/drafts?date=today` currently returns only the current `PENDING` `DAILY_OUTBOUND` group for the operational day.
- Phase 16 intentionally allows multiple same-day `DAILY_OUTBOUND` groups as long as only one is still `PENDING`, so a rejected or approved same-day group can exist alongside a later pending one.

Contract Locks / Clarifications
- The user prompt overrides the older Approvals doc: rejection reason remains a visible free-text field, but it is now optional for both single-line rejection and whole-group rejection.
- Blank or whitespace-only rejection reasons must not block rejection. Persist them as `NULL` / empty-normalized state, not as validation failures.
- Reuse the existing `ApprovalAction.note` persistence path. Do not add a new schema column unless a real blocker is found and documented first.
- The Approvals history UI currently loads summary cards from `GET /api/v1/approvals?status=history` and expanded detail from `GET /api/v1/approvals/{group_id}`. At minimum, the expanded history/detail payload must expose `rejection_reason` for rejected rows and entries; if the list payload is broadened too, keep the existing list contract compatible.
- Do not regress the Phase 5 / Phase 16 Draft Entry model:
- `draft_group` in the drafts response must keep representing the current editable `PENDING` `DAILY_OUTBOUND` group for the operational day, or `null` if none exists.
- To support "My entries today" after an admin has already approved or rejected a same-day draft, the drafts API must additionally expose same-day `DAILY_OUTBOUND` lines across resolved and pending groups without mixing in `INVENTORY_SHORTAGE` groups.
- Preserve current RBAC and edit/delete rules: Approvals stays ADMIN-only; Draft Entry stays ADMIN/OPERATOR; only `DRAFT` lines remain editable/deletable.
- Follow global Croatian UI copy for client-rendered labels, helper text, empty states, and badges. Raw backend business-error messages may remain English when surfaced directly.

Delegation Plan
- Backend:
- remove mandatory rejection validation, normalize optional reasons, expose rejection reason in approvals detail/history serialization, and extend the drafts payload so Draft Entry can show same-day operator statuses without losing the current editable-group contract.
- Frontend:
- remove required rejection validation in the modal, render rejection reasons in Approvals history, and add a "My entries today" section driven by the expanded drafts payload while preserving the current shared-draft note/edit flow.
- Testing:
- extend approvals regressions for optional rejection reasons and response shapes, plus verify the expanded drafts payload and any touched draft-entry contract.

Acceptance Criteria
- Rejecting a line or a whole draft without entering a reason returns `200` and completes the rejection.
- Rejecting with a reason persists that reason and exposes it back through the approvals history/detail API.
- Draft Entry shows the logged-in user's same-day daily-outbound lines with status badges and optional rejection reason, even if the original same-day draft group is already resolved.
- Existing shared daily draft note handling and editable pending-draft behaviour remain intact.
- The phase leaves a complete orchestration / backend / frontend / testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first so the response-shape change for Draft Entry is explicit before Frontend and Testing proceed.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 5 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-PROD-001`, `DEC-BE-013`)
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/orchestrator.md`
- `backend/app/api/approvals/routes.py`
- `backend/app/services/approval_service.py`
- `backend/app/models/approval_action.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/models/draft.py`
- `backend/app/models/draft_group.py`
- `backend/tests/test_approvals.py`
- `backend/tests/test_drafts.py`

Goal
- Make draft rejection reason optional and expose rejection metadata to Approvals history and Draft Entry without regressing the existing Draft Entry / same-day DraftGroup semantics.

Non-Negotiable Contract Rules
- Both rejection paths must accept an omitted, blank, or whitespace-only reason:
- `POST /api/v1/approvals/{group_id}/lines/{line_id}/reject`
- `POST /api/v1/approvals/{group_id}/reject`
- Keep max-length validation for non-empty reasons.
- Persist optional rejection notes via `ApprovalAction.note`; blank input should normalize to `None`, not to a `400` validation failure.
- Preserve the existing Approvals pending/history split and current RBAC.
- Preserve the existing Draft Entry meaning of `draft_group`: it is still the current editable `PENDING` `DAILY_OUTBOUND` group for the operational day, not an arbitrary resolved group.
- Because Phase 16 allows closed same-day groups plus a later pending group, the Draft Entry response must expose enough same-day `DAILY_OUTBOUND` line data for the frontend to show operator status/rejection history even after a same-day group is already `APPROVED` or `REJECTED`.
- Do not include `INVENTORY_SHORTAGE` groups in the Draft Entry operator-status data.

Tasks
1. Remove the server-side non-empty validation for rejection reason from both rejection routes.
2. Update the approval-service rejection path so it accepts `reason: str | None` and stores `ApprovalAction.note = None` when no reason is provided.
3. Extend approvals serialization:
- `GET /api/v1/approvals/{group_id}` must include `rejection_reason` on rejected aggregated rows and on individual entries.
- Use `null` when no reason exists or when the field is not applicable.
- Keep the existing response shape compatible otherwise.
4. If the history list endpoint itself is the easiest place to surface row-level rejection reasons too, that is allowed, but do not break the current summary-card contract consumed by the frontend.
5. Extend the drafts payload used by Draft Entry:
- Keep `items` and `draft_group` backward-compatible for the current editable pending daily draft.
- Add a separate same-day line collection for all `DAILY_OUTBOUND` draft lines from the operational day, across pending and resolved same-day groups, ordered newest first.
- Each same-day line object must include at least:
  - `id`
  - `draft_group_id`
  - `article_id`
  - `article_no`
  - `description`
  - `batch_id`
  - `batch_code`
  - `quantity`
  - `uom`
  - `employee_id_ref`
  - `status`
  - `rejection_reason`
  - `created_by`
  - `created_at`
- Keep inventory-shortage groups excluded from this Draft Entry response.
6. Include `rejection_reason` on the current editable-draft line serialization too, using `null` when not rejected or when no note exists.
7. Do not regress idempotency, current draft-group lookup semantics, or the existing edit/delete route behaviour for `DRAFT` lines only.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q`
- If you touch any additional regressions, run and record them too.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you need to lock or revise the exact Draft Entry response shape beyond what is stated here, record that in `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- Blank rejection reasons no longer fail validation.
- Rejection reasons are exposed in approvals detail/history data.
- Draft Entry receives same-day status/rejection data without losing the current editable-group contract.
- Verification is recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 5 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/api/approvals.ts`
- `frontend/src/api/drafts.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
- `frontend/src/store/authStore.ts`

Goal
- Make rejection reason optional in the Approvals UI, show rejection reasons in Approvals history, and add an operator-facing "My entries today" section in Draft Entry without breaking the existing shared daily-draft behaviour.

Non-Negotiable Contract Rules
- The rejection modal textarea remains visible but must no longer be required. Submitting a blank reason must be allowed.
- Keep existing retry-once-then-fatal-error behaviour in both Approvals and Draft Entry.
- Preserve the current shared daily-draft note/editor flow from Phase 5. Do not remove the existing shared draft mechanics just because "My entries today" is being added.
- Use the backend-provided same-day line data for "My entries today"; do not infer rejection reasons client-side.
- "My entries today" should show only lines created by the logged-in user, filtered from the backend response.
- If a rejected line has no reason, render no empty placeholder field.
- Client-rendered UI copy should remain Croatian by default.

Tasks
1. Update `frontend/src/api/approvals.ts` typings so approvals detail/history data can carry `rejection_reason` on rejected rows and entries, plus optional blank-reason rejection responses.
2. Update the Approvals rejection modal in `DraftGroupCard.tsx`:
- remove the required attribute
- remove the client-side "reason required" block
- keep the textarea label visible
- allow confirm with empty text
3. Update the Approvals history/detail rendering:
- for rejected rows, show the rejection reason below the article description or in another clear read-only placement within the expanded detail
- if a row/entry has no rejection reason, show nothing extra
- do not disturb pending-view actions or the existing expandable-row workflow
4. Update `frontend/src/api/drafts.ts` typings for the expanded drafts payload, including per-line `rejection_reason` and the new same-day line collection added by the backend.
5. Update `DraftEntryPage.tsx`:
- keep the current entry form
- keep the current shared daily draft note flow
- add a new section below the form named in Croatian equivalent of "My entries today"
- derive that section by filtering the backend-provided same-day daily-outbound lines to the logged-in user
- show article, quantity, and status badge for each line
- use Croatian badge labels consistent with the existing UI language, but preserve the semantic colors:
  - pending = yellow
  - approved = green
  - rejected = red
- for rejected lines with a reason, show the reason below the line
6. Keep edit/delete affordances aligned with existing rules for the shared current-draft table; do not accidentally make approved/rejected rows editable.

Verification
- Run at minimum:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If the backend response shape differs from the orchestrator brief, log the exact difference before finalizing.

Done Criteria
- Rejection can be confirmed without entering text.
- Rejection reasons are visible in Approvals history/detail where applicable.
- Draft Entry shows the logged-in user's same-day lines with status badges and optional rejection reason.
- Existing shared daily-draft behaviour remains intact.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 5 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `backend/tests/test_approvals.py`
- `backend/tests/test_drafts.py`
- `backend/app/api/approvals/routes.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/drafts/routes.py`

Goal
- Lock regression coverage for optional rejection reasons and the new rejection-metadata response shapes used by Approvals history and Draft Entry.

Tasks
1. Extend `backend/tests/test_approvals.py` to cover at minimum:
- reject whole draft without reason -> `200`
- reject aggregated line with reason -> `200`, reason saved
- approvals detail/history payload exposes `rejection_reason`
- `rejection_reason` is `null` when no reason was given and the exact string when it was
2. Add or extend coverage for the Draft Entry payload contract:
- the drafts response used by Draft Entry includes `status`
- rejected lines include `rejection_reason`
- same-day resolved daily-outbound lines remain visible through the new payload branch needed by the frontend
- inventory-shortage groups are not leaked into the Draft Entry operator-status data
3. Reuse the existing approvals/drafts fixture patterns where practical; do not rewrite unrelated module setup.
4. Keep assertions aligned with the standard API error shape wherever errors are still expected.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q`
- Also run any additional targeted regressions you touch or depend on, and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/testing.md`.
- Use the section shape required by `handoff/README.md`.
- If you find a spec or contract mismatch, log it immediately in your handoff with the precise failing behaviour.

Done Criteria
- Optional rejection reason behaviour is covered.
- Approvals rejection metadata serialization is covered.
- Draft Entry same-day status/reason payload coverage is in place.
- Verification is recorded in handoff.

## [2026-03-24 15:50] Orchestrator Validation - Wave 1 Phase 5 Rejection Reason Visibility

Status
- backend accepted
- testing accepted
- frontend follow-up required before full closeout

Scope
- Reviewed the backend, frontend, and testing deliveries for Wave 1 Phase 5.
- Re-ran the delegated backend verification plus frontend lint/build.
- Checked the changed Draft Entry and Approvals code paths against the locked phase contract and the existing Phase 5 / Phase 16 baseline.

Docs Read
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/orchestrator.md`
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/backend.md`
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/frontend.md`
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/testing.md`
- `handoff/decisions/decision-log.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/10_UI_APPROVALS.md`

Files Reviewed
- `backend/app/api/approvals/routes.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/drafts/routes.py`
- `backend/tests/test_approvals.py`
- `backend/tests/test_drafts.py`
- `frontend/src/api/approvals.ts`
- `frontend/src/api/drafts.ts`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`
- `frontend/src/pages/drafts/DraftEntryPage.tsx`

Commands Run
```bash
git diff --stat -- handoff/wave-01/phase-05-wave-01-rejection-reason-visibility backend/app/api/approvals/routes.py backend/app/services/approval_service.py backend/app/api/drafts/routes.py backend/tests/test_approvals.py backend/tests/test_drafts.py frontend/src/api/approvals.ts frontend/src/api/drafts.ts frontend/src/pages/approvals/components/DraftGroupCard.tsx frontend/src/pages/drafts/DraftEntryPage.tsx handoff/decisions/decision-log.md
backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- Accepted backend changes:
  - rejection reason is now optional on both reject endpoints
  - approvals detail payload now exposes `rejection_reason`
  - Draft Entry backend gets the needed `same_day_lines` branch without breaking the existing `items` / `draft_group` contract
- Accepted testing changes:
  - targeted approvals and drafts regression coverage was extended and the delegated backend verification passes cleanly
- Finding:
  - `Moji unosi danas` is rendered from `sameDayLines`, but that state is only hydrated during the initial `loadLines()` fetch and is not kept in sync after local mutations.
  - In [DraftEntryPage.tsx](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/drafts/DraftEntryPage.tsx#L351), successful add-on-existing-draft updates only `lines`, not `sameDayLines`.
  - In [DraftEntryPage.tsx](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/drafts/DraftEntryPage.tsx#L467), successful edit updates only `lines`, not `sameDayLines`.
  - In [DraftEntryPage.tsx](/Users/grzzi/Desktop/STOQIO/frontend/src/pages/drafts/DraftEntryPage.tsx#L525), successful delete removes only from `lines`, not `sameDayLines`.
  - Result: within the same session, the new operator-facing section can show stale data after add/edit/delete until a full page reload. That breaks the intended "My entries today" behaviour even though lint/build and backend tests stay green.

Verification
- `backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q` -> `61 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- No additional backend contract issues were found in this review pass.
- Phase cannot be closed yet because the frontend state-sync issue affects the newly added user-visible workflow.

Next Action
- Send a frontend follow-up:
  - keep `sameDayLines` synchronized after successful add/edit/delete, or
  - re-fetch the drafts payload after those mutations so both the shared table and `Moji unosi danas` stay correct.
- After that follow-up, rerun `cd frontend && npm run lint` and `cd frontend && npm run build`, then re-review for closeout.

## [2026-03-24 15:53] Orchestrator Follow-up Implementation - Frontend State Sync

Status
- accepted
- phase closed

Scope
- Implemented the previously identified frontend follow-up directly in the orchestrator pass so the new `Moji unosi danas` section stays synchronized after successful local mutations.
- Re-ran the full Wave 1 Phase 5 verification set after the fix.

Files Changed
- `frontend/src/pages/drafts/DraftEntryPage.tsx`
  - added local helpers to prepend, update, and remove `sameDayLines`
  - wired those helpers into successful add, edit, and delete flows so `sameDayLines` stays aligned with `lines` without requiring a page reload

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- The stale-state finding from the earlier review is resolved:
  - successful add on an existing pending draft now prepends the new line to both `lines` and `sameDayLines`
  - successful edit now updates both `lines` and `sameDayLines`
  - successful delete now removes from both `lines` and `sameDayLines`
- No new contract drift was introduced by this follow-up.
- Ownership note:
  - this frontend follow-up was implemented directly by the orchestrator, not by a delegated frontend-agent pass, so later readers should treat this section as the source of truth for the closeout fix.

Verification
- `backend/venv/bin/pytest backend/tests/test_approvals.py backend/tests/test_drafts.py -q` -> `61 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- No open phase-local issues remain from this review and follow-up.

Next Action
- Treat Wave 1 Phase 5 as closed.
- Future work can build on this rejection-reason baseline and the synchronized `sameDayLines` Draft Entry behaviour.
