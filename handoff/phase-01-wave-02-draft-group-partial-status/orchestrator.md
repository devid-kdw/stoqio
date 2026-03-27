## Phase Summary

Phase
- Wave 2 - Phase 1 - DraftGroup PARTIAL Persistence

Objective
- Resolve the approval-state inconsistency where a `DraftGroup` can be effectively `PARTIAL` in API/display logic while the persisted `DraftGroup.status` in the database remains `PENDING`.
- Promote `PARTIAL` from a computed-only display escape hatch into a real persisted approval-group status.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-030`)
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10-12
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-APP-001`, prior approvals decisions)
- `handoff/phase-06-approvals/orchestrator.md`
- `handoff/phase-06-approvals-followup/orchestrator.md`
- `backend/app/models/enums.py`
- `backend/app/models/draft_group.py`
- `backend/app/services/approval_service.py`
- `backend/tests/test_approvals.py`
- `frontend/src/api/approvals.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

Current Repo Reality
- The UI spec already expects History to include `APPROVED`, `REJECTED`, and `PARTIAL` groups.
- The persisted `DraftGroup.status` enum/model currently supports only `PENDING`, `APPROVED`, and `REJECTED`.
- `approval_service._compute_group_display_status(...)` already derives `PARTIAL` when a group has no remaining `DRAFT` lines and contains a mix of approved and rejected lines.
- `approval_service.get_history_draft_groups()` currently masks the persistence gap by computing a display-only `PARTIAL` status for API output.
- `approval_service._update_group_status_if_done(...)` explicitly leaves the database row unchanged when the computed result is `PARTIAL`, so the row can remain stored as `PENDING` forever even though the group is fully resolved.
- Pending/history list segmentation currently works because it is based on whether any `Draft.status = DRAFT` rows remain, not because `DraftGroup.status` is correct.
- The frontend already partially knows about `PARTIAL` in approval type unions and badge rendering, but this phase still requires a full audit so no status-mapping or tab behavior depends on the older three-status assumption.
- Current backend tests lock only the computed API surface for mixed groups; they do not assert persisted `DraftGroup.status == PARTIAL`.

Contract Locks / Clarifications
- This phase adopts the explicit design from `DEC-APP-001`: `DraftGroup.status` is authoritative for resolved group state and must now persist `PARTIAL`.
- `PARTIAL` is valid only for a fully resolved group:
  - no remaining `Draft.status = DRAFT` rows
  - at least one approved line
  - at least one rejected line
- A group that still has any pending draft lines remains `PENDING` even if some lines were already approved or rejected.
- Pending/history segmentation must stay tied to the existence of unresolved draft lines:
  - Pending = groups with at least one `DRAFT` line
  - History = groups with no `DRAFT` lines
- Do not replace the current list segmentation with a naive `DraftGroup.status = 'PENDING'` / `!= 'PENDING'` split unless you prove it is behaviorally identical for all supported approval flows.
- The shared group-status update path must stop leaving mixed resolved groups as stored `PENDING`.
- The migration path must do two things:
  - make `PARTIAL` valid in the schema/model for both SQLite test upgrades and PostgreSQL deployment upgrades
  - backfill already-existing groups that are effectively mixed-and-resolved but still persisted as `PENDING`
- Keep approval route shapes, RBAC, response field names, and approval/rejection business semantics unchanged outside the status-fix scope.
- Keep the existing Phase 6 daily-outbound uniqueness invariant intact:
  - only one `PENDING` `DAILY_OUTBOUND` group per `operational_date`
  - resolved `PARTIAL` groups must not interfere with creation of a new `PENDING` group for the same day
- This phase is about approval-group persisted state, not a redesign of row-level status logic, rejection-note handling, or ApprovalAction semantics.

Delegation Plan
- Backend:
- extend the persisted enum/model + migration path, backfill inconsistent rows, and make the shared approvals service persist `PARTIAL` correctly without breaking pending/history segmentation
- Frontend:
- audit approval status typing and rendering so `PARTIAL` is treated as a first-class group status everywhere needed, with no Pending-tab regressions
- Testing:
- extend backend regression coverage so the persisted DB row and API surface both agree on `PARTIAL`, while existing fully approved/rejected behavior remains stable

Acceptance Criteria
- `DraftGroupStatus` and the `draft_group.status` schema accept persisted `PARTIAL`.
- Fresh upgrade-to-head works after the new migration on the supported local SQLite path, and the migration remains suitable for PostgreSQL deployment.
- Existing mixed-and-resolved groups can no longer remain stored as `PENDING` after the upgrade path.
- When a group becomes fully resolved with a mix of approved and rejected lines, persisted `DraftGroup.status` becomes `PARTIAL`.
- Pending approvals endpoints still return only genuinely pending work.
- History approvals endpoints include `PARTIAL` groups with the correct status.
- Frontend approval history renders `PARTIAL` with a distinct badge/label and does not re-show such groups in Pending.
- Existing fully `APPROVED` and fully `REJECTED` group behavior remains unchanged.
- The phase leaves a complete orchestration, backend, frontend, and testing handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the persisted enum/migration/status contract is locked before Frontend and Testing finalize their work.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 2 Phase 1 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-030`)
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10-12
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-APP-001` and prior approvals decisions)
- `handoff/phase-06-approvals/orchestrator.md`
- `handoff/phase-06-approvals-followup/orchestrator.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`
- `backend/app/models/enums.py`
- `backend/app/models/draft_group.py`
- `backend/app/services/approval_service.py`
- `backend/app/api/approvals/routes.py`
- `backend/tests/test_approvals.py`
- `backend/tests/test_phase2_models.py`

Goal
- Make `PARTIAL` a real persisted `DraftGroup.status` instead of a computed-only display state, while keeping the accepted approvals workflow behavior intact.

Non-Negotiable Contract Rules
- `DraftGroup.status` must now support persisted `PARTIAL`.
- Persist `PARTIAL` only when a group has no remaining `Draft.status = DRAFT` rows and has a mix of approved and rejected lines.
- If any `DRAFT` rows remain, the group stays `PENDING` even if some rows were already approved or rejected.
- Pending/history segmentation must remain based on actual unresolved draft rows:
- Pending = groups with at least one `DRAFT` line
- History = groups with no `DRAFT` lines
- Do not replace that with a naive `DraftGroup.status` filter unless you prove it is equivalent and preserve current behavior.
- Remove the current `_update_group_status_if_done(...)` code path that deliberately leaves mixed resolved groups stored as `PENDING`.
- The migration must:
- make `PARTIAL` valid in the schema/model
- preserve compatibility for existing rows
- backfill already inconsistent mixed-and-resolved groups that are currently stored as `PENDING`
- Because the repo supports fresh SQLite upgrade verification and targets PostgreSQL deployments, handle the enum/check-constraint migration path carefully for both environments.
- Keep approval route shapes, RBAC, error semantics, and row-level approval/rejection business rules unchanged outside this status-fix scope.
- Preserve the existing unique `PENDING` daily-outbound invariant; adding resolved `PARTIAL` must not block future same-day pending groups.

Tasks
1. Extend the persisted `DraftGroupStatus` enum/model to include `PARTIAL`.
2. Add the required Alembic migration for the `draft_group.status` schema change.
3. In that upgrade path, correct any existing groups that are already fully resolved mixed groups but still stored as `PENDING`.
4. Update the shared approvals status-sync path so:
- fully approved groups persist as `APPROVED`
- fully rejected groups persist as `REJECTED`
- fully resolved mixed groups persist as `PARTIAL`
- groups with any remaining pending draft lines stay `PENDING`
5. Audit approvals queries/serializers so no code still assumes only `PENDING / APPROVED / REJECTED`.
6. Keep `get_pending_draft_groups()`, `get_history_draft_groups()`, and detail serializers behaviorally aligned with the locked Pending-vs-History rules.
7. Do not broaden this into unrelated approvals refactors.

Verification
- Extend backend tests as needed.
- Run at minimum:
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q`
- `backend/venv/bin/pytest backend/tests/test_phase2_models.py -q`
- If your migration or enum change has wider blast radius, also run:
- `backend/venv/bin/pytest backend/tests -q`

Handoff Requirements
- Append your work log to `handoff/phase-01-wave-02-draft-group-partial-status/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, migration/backfill behavior, commands run, tests run, open issues, and assumptions.
- If you discover a new cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- `PARTIAL` is a valid persisted `DraftGroup.status`.
- Mixed fully resolved groups no longer remain stored as `PENDING`.
- Pending/history API behavior remains correct.
- Migration/backfill behavior is verified and recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 2 Phase 1 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/10_UI_APPROVALS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-APP-001`)
- `handoff/phase-06-approvals/orchestrator.md`
- `handoff/phase-06-approvals-followup/orchestrator.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`
- backend handoff for this phase after backend finishes
- `frontend/src/api/approvals.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

Goal
- Treat `PARTIAL` as a first-class approval-group status in the Approvals UI without regressing Pending/History behavior.

Current Repo Reality
- The frontend already has partial support for `PARTIAL` in approval type unions and badge rendering.
- This phase is therefore an audit-and-hardening pass, not necessarily a large UI rewrite.
- Do not assume "already present" means no work is needed; verify all affected status logic and tab behavior against the locked backend contract.

Non-Negotiable Contract Rules
- Keep the Approvals route, tabs, detail flow, and existing approve/reject actions unchanged outside this status-fix scope.
- `PARTIAL` is now a real backend group status, not just a computed display accident.
- Pending tab must continue to show only genuinely pending work.
- History must show resolved mixed groups with a distinct and correct `PARTIAL` badge/label.
- Keep the existing approvals status vocabulary/pattern consistent; do not invent a new backend status value or unrelated visual taxonomy.
- Do not broaden this into a general Approvals redesign or copy refactor.

Tasks
1. Audit `frontend/src/api/approvals.ts` type definitions so `PARTIAL` is treated as a real supported group status everywhere needed.
2. Audit `ApprovalsPage.tsx` and `DraftGroupCard.tsx` for any logic that could accidentally assume only the original three statuses.
3. Verify the Pending tab does not re-show partially resolved groups after refresh/reload.
4. Verify the History tab/card header/detail surfaces show `PARTIAL` with a distinct and correct badge/label.
5. Make only the smallest frontend change set needed to align with the persisted backend status contract.

Verification
- Run at minimum:
- `cd frontend && npm run lint -- --max-warnings=0`
- `cd frontend && npm run build`
- Verify via code-path review that:
- Pending data still comes only from the pending endpoint
- History badges/status display handle `PARTIAL` explicitly
- no status helper/type path silently narrows back to the old three-state assumption

Handoff Requirements
- Append your work log to `handoff/phase-01-wave-02-draft-group-partial-status/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, verification performed, open issues, and assumptions.
- If the backend handoff changes the effective status contract from this prompt, log the mismatch instead of silently inventing a new UI rule.

Done Criteria
- Frontend treats `PARTIAL` as a real approval-group status everywhere needed.
- Pending tab does not re-show resolved mixed groups.
- History shows `PARTIAL` correctly.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 2 Phase 1 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-APP-001`)
- `handoff/phase-06-approvals/orchestrator.md`
- `handoff/phase-06-approvals-followup/orchestrator.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `backend/tests/test_approvals.py`
- `backend/app/services/approval_service.py`
- `backend/app/models/enums.py`
- `backend/app/models/draft_group.py`
- `backend/app/api/approvals/routes.py`

Goal
- Lock regression coverage for the persisted `PARTIAL` approval-group status contract.

Non-Negotiable Test Rules
- Assert the persisted database row state, not only the API display state.
- Keep existing fully approved and fully rejected expectations intact.
- Do not rewrite unrelated approvals scaffolding.

Tasks
1. Extend `backend/tests/test_approvals.py`.
2. Cover at minimum:
- mixed scenario: approve some lines, reject some lines, fully resolve the group, then assert persisted `DraftGroup.status == PARTIAL`
- `PARTIAL` group does not appear in the pending list
- `PARTIAL` group appears in history with correct status
- existing fully approved behavior remains unchanged
- existing fully rejected behavior remains unchanged
3. Where possible, assert both:
- direct DB state on the `DraftGroup` row
- API response state from the approvals endpoints
4. Reuse the current approvals fixtures/helpers instead of rebuilding the entire setup.

Verification
- Run at minimum:
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q`
- If test additions expose broader regressions, run any additional targeted subset you touch and record it.

Handoff Requirements
- Append your work log to `handoff/phase-01-wave-02-draft-group-partial-status/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record files changed, commands run, tests run, open issues, and assumptions.
- If you find that backend or frontend behavior still conflicts with the locked contract, log the exact mismatch instead of relaxing the test to match drift.

Done Criteria
- Backend tests now prove that `PARTIAL` is persisted as well as displayed.
- Pending/history separation for `PARTIAL` groups is covered.
- Fully approved and fully rejected behavior remains covered and unchanged.
- Verification is recorded in handoff.

## [2026-03-27 16:03 CET] Orchestrator Validation - Wave 2 Phase 1 DraftGroup PARTIAL Persistence

Status
- changes_requested

Scope
- Reviewed the delivered backend, frontend, and testing handoffs for Wave 2 Phase 1.
- Re-ran the targeted approvals and migration suites, then re-ran the full backend suite plus frontend lint/build gates.
- Performed an additional fresh-SQLite migration inspection because this phase changes the persisted `draft_group.status` schema contract.

Docs Read
- `handoff/phase-01-wave-02-draft-group-partial-status/backend.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/frontend.md`
- `handoff/phase-01-wave-02-draft-group-partial-status/testing.md`
- `handoff/decisions/decision-log.md` (`DEC-APP-001`)
- `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py`
- `backend/tests/test_phase2_models.py`

Files Reviewed
- `backend/app/models/enums.py`
- `backend/app/services/approval_service.py`
- `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py`
- `backend/migrations/versions/7c2d2c6d0f4a_persist_token_revocation_and_lock_daily_.py`
- `backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py`
- `backend/tests/test_approvals.py`
- `frontend/src/api/approvals.ts`
- `frontend/src/pages/approvals/ApprovalsPage.tsx`
- `frontend/src/pages/approvals/components/DraftGroupCard.tsx`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_approvals.py -q
backend/venv/bin/pytest backend/tests/test_phase2_models.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build

# additional fresh-SQLite migration inspection
tmp_db=$(mktemp /tmp/stoqio_phase1_XXXXXX.db)
cd backend
FLASK_ENV=development DATABASE_URL=sqlite:///$tmp_db JWT_SECRET_KEY=test-jwt-secret-key-suite-2026-0001 venv/bin/alembic upgrade head
sqlite3 "$tmp_db" ".schema draft_group"
sqlite3 "$tmp_db" "PRAGMA foreign_keys=OFF; INSERT INTO draft_group (group_number, status, operational_date, created_by, created_at, group_type) VALUES ('IZL-TEST', 'PARTIAL', '2026-03-27', 1, '2026-03-27 00:00:00', 'DAILY_OUTBOUND');"
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q` -> `29 passed`
- `backend/venv/bin/pytest backend/tests/test_phase2_models.py -q` -> `2 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `350 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- Additional manual migration inspection found a blocking fresh-SQLite schema defect:
  - `sqlite3 "$tmp_db" ".schema draft_group"` still showed
  - `CONSTRAINT draft_group_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'))`
  - inserting a fresh `draft_group.status = 'PARTIAL'` row on that migrated SQLite DB failed with
  - `CHECK constraint failed: draft_group_status`

Accepted Work
- Backend runtime/service logic now persists `DraftGroupStatus.PARTIAL` on the normal ORM/test path.
- Pending/history API segmentation remains behaviorally correct in the approvals service and regression tests.
- Frontend audit conclusion is acceptable: current approvals UI already treats `PARTIAL` as a first-class display status and did not need code changes.
- The added approvals regression coverage materially improves protection around persisted `PARTIAL` behavior on the non-migration test path.

Blocking Findings
- The new SQLite migration path does not actually rebuild the `draft_group.status` CHECK constraint to include `PARTIAL`, so fresh SQLite installs upgraded via Alembic still reject persisted `PARTIAL` rows. The issue is in `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py` where the SQLite `alter_column(...)` path uses `sa.Enum(*_NEW_VALUES, name=_ENUM_NAME)` without recreating the SQLite CHECK constraint for the four-value set.
- The migration verification coverage did not lock the real phase requirement. `backend/tests/test_phase2_models.py` proves upgrade-to-head runs, but it does not assert that the migrated `draft_group.status` constraint actually allows `PARTIAL`, which is why the broken fresh-SQLite path slipped through.

Closeout Decision
- Wave 2 Phase 1 is not ready for closeout.
- Backend migration work must be remediated before this phase can be accepted.

Next Action
- Return the phase for backend remediation of the fresh-SQLite migration path so `draft_group.status` truly accepts `PARTIAL` after `alembic upgrade head`.
- Extend migration verification to assert the migrated schema or runtime behavior really allows persisted `PARTIAL` on a fresh SQLite database.

## [2026-03-27 16:14 CET] Orchestrator Remediation + Final Validation - Wave 2 Phase 1 DraftGroup PARTIAL Persistence

Status
- accepted

Scope
- Implemented the blocking remediation directly as orchestrator after the prior validation finding.
- Fixed the fresh-SQLite migration path for persisted `PARTIAL`.
- Extended migration regression coverage so the same defect cannot slip through again.
- Re-ran targeted approvals and migration tests, then re-ran the full backend suite and frontend lint/build gates.

Why The Orchestrator Edited Code
- The prior validation found a real blocking defect in the newly added migration path, not a scope ambiguity.
- The user explicitly requested that the orchestrator implement the required fix directly and document that this remediation was done by the orchestrator so future agents can see the provenance clearly.

Files Changed By Orchestrator
- `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py`
- `backend/tests/test_phase2_models.py`
- `handoff/phase-01-wave-02-draft-group-partial-status/orchestrator.md`

What Changed
- Fixed the SQLite branch of `c3d4e5f6a7b8_add_partial_to_draft_group_status.py`:
- the batch enum alter now rebuilds the `draft_group.status` CHECK constraint with `create_constraint=True` on both the old and new enum definitions
- result: fresh SQLite `alembic upgrade head` now produces `draft_group_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIAL'))`
- Strengthened `backend/tests/test_phase2_models.py`:
- migration verification now asserts the migrated `draft_group` CHECK constraint includes `PARTIAL`
- the same test now performs a real insert of a `draft_group` row with `status = 'PARTIAL'` on a fresh migrated SQLite database, which would have failed before this remediation

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_phase2_models.py -q
backend/venv/bin/pytest backend/tests/test_approvals.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build

# additional manual migration inspection after remediation
tmp_db=$(mktemp /tmp/stoqio_phase1_fix_XXXXXX.db)
cd backend
FLASK_ENV=development DATABASE_URL=sqlite:///$tmp_db JWT_SECRET_KEY=test-jwt-secret-key-suite-2026-0001 venv/bin/alembic upgrade head
sqlite3 "$tmp_db" ".schema draft_group"
```

Validation Result
- `backend/venv/bin/pytest backend/tests/test_phase2_models.py -q` -> `2 passed`
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q` -> `29 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `350 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- manual fresh-SQLite migration inspection now shows:
- `CONSTRAINT draft_group_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'PARTIAL'))`

Closeout Decision
- The prior blocking migration defect is resolved.
- Wave 2 Phase 1 is formally closed.

Residual Notes
- The opportunistic SQLite warning fixes in earlier migrations remain in place and the full backend suite is still green after this remediation.
- Frontend remained audit-only in this phase; no frontend code changes were necessary.

Next Action
- Treat the current repo state and this handoff trail as the accepted baseline for the next Wave 2 phase.
