## Phase Summary

Phase
- Wave 1 - Phase 4 - Opening Inventory Count

Objective
- Add an `OPENING` inventory count type for initial warehouse stock entry on first operational setup.
- Preserve the existing Inventory Count workflow and locked discrepancy-processing rules for regular counts.
- Enforce that only one `OPENING` count can ever exist in the system, while keeping the separate "only one active count at a time" rule intact.

Source Docs
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-001` through `DEC-INV-006`, `DEC-BE-014`)
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Current Repo Reality
- Inventory Count is already implemented end to end for the single existing count type.
- `InventoryCount` currently has no `type` column or enum.
- `POST /api/v1/inventory` currently starts a count with no request body.
- `GET /api/v1/inventory` currently returns paginated completed-count history only.
- `GET /api/v1/inventory/active` currently returns either `{ "active": null }` or the active count object directly.
- The frontend history screen currently starts a count immediately from the "Pokreni novu inventuru" button with no type-selection modal.

Contract Locks / Clarifications
- `InventoryCount.type` is now a required enum with values `REGULAR` and `OPENING`; default is `REGULAR`.
- Only one `OPENING` count row may exist in the entire database, regardless of whether that row is `IN_PROGRESS` or `COMPLETED`.
- The existing rule "only one inventory count may be `IN_PROGRESS` at a time" remains unchanged and applies across both types.
- `OPENING` and `REGULAR` counts share identical line snapshot, autosave, completion, surplus, and shortage-draft behavior. Do not introduce special discrepancy handling for `OPENING`.
- To support the new frontend start-flow without requiring a full paginated history scan, `GET /api/v1/inventory?page=...` must additionally expose `opening_count_exists: boolean`, computed across all `InventoryCount` rows.
- Any response that describes a count should expose `type`, including `POST /api/v1/inventory`, `GET /api/v1/inventory/active`, `GET /api/v1/inventory`, and `GET /api/v1/inventory/{id}`.
- Existing decisions from Phase 12 remain locked: stock snapshot includes surplus (`DEC-INV-004`), shortage draft grouping uses operational timezone (`DEC-INV-005`), and line payloads keep `decimal_display` (`DEC-INV-006`).

Delegation Plan
- Backend:
- Add the new enum-backed `type` model field with a migration that is safe for both PostgreSQL and fresh SQLite Alembic upgrades; extend inventory routes/service serialization and start validation.
- Frontend:
- Add the start-type selection flow, wire the new inventory API contract, and surface `OPENING` badges in history plus count headers.
- Testing:
- Extend inventory-count backend coverage for opening-count creation, singleton enforcement, response shapes, and unchanged completion semantics; reverify fresh migration coverage.

Acceptance Criteria
- Starting an `OPENING` count returns `201` and persists `type = OPENING`.
- Starting a second `OPENING` count returns `400` with message `"Opening stock count already exists."`.
- Starting `REGULAR` counts remains allowed whether or not an `OPENING` count already exists, provided no other count is currently `IN_PROGRESS`.
- Inventory history rows and count detail payloads expose `type`, and history responses expose `opening_count_exists`.
- Inventory history shows a distinct "Opening Stock" badge for completed opening counts.
- Inventory count headers show a prominent "Opening Stock" badge whenever the viewed count is of type `OPENING`.
- Completing an `OPENING` count produces the same outcomes as a regular count: surpluses go to `Surplus`, shortages create `INVENTORY_SHORTAGE` drafts for Approvals.
- The phase leaves a complete handoff trail across orchestration, backend, frontend, and testing.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the enum/migration/API contract is explicit, then let Frontend and Testing proceed against that locked backend contract.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 1 Phase 4 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` § 17, § 18
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-001` through `DEC-INV-006`, `DEC-BE-014`, `DEC-INV-007`)
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- `backend/app/models/enums.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_phase2_models.py`

Goal
- Extend the Inventory Count backend so counts can be either `REGULAR` or `OPENING`, while preserving the existing count lifecycle and discrepancy-processing semantics.

Non-Negotiable Contract Rules
- Keep the current rule that only one count may be `IN_PROGRESS` at a time.
- Add the new rule that only one `OPENING` count may ever exist in the database, regardless of status.
- `OPENING` completion logic must be identical to `REGULAR` completion logic. Do not special-case surplus handling, shortage-draft creation, or summary counters.
- Keep `GET /api/v1/inventory/active` returning HTTP `200` with `{ "active": null }` when there is no active count.
- Keep `GET /api/v1/inventory` as the paginated history endpoint for completed counts only.
- Add `opening_count_exists: boolean` to the `GET /api/v1/inventory` response so the frontend can decide whether the opening-count option should still be offered.
- Include `type` in every count-shaped inventory response: start response, active response, history items, and count detail.
- Migration must be safe for:
  - PostgreSQL fresh installs: explicitly create/drop the enum type before/after the table alteration.
  - SQLite fresh Alembic upgrades: do not use an ALTER pattern that breaks `backend/tests/test_phase2_models.py`; use Alembic batch mode or an equivalent SQLite-safe migration strategy.
- Do not regress the locked Phase 12 rules around surplus-inclusive snapshots, timezone-aware shortage draft grouping, or `decimal_display` in line payloads.

Tasks
1. Add a new backend enum for inventory count type with values `REGULAR` and `OPENING`.
2. Extend `InventoryCount` with a non-null `type` column defaulting to `REGULAR`.
3. Add the Alembic migration for that column:
   - PostgreSQL: explicitly create the enum type before the `ALTER TABLE` step.
   - SQLite: keep fresh upgrade-to-head working.
4. Extend `POST /api/v1/inventory`:
   - accept optional JSON body `{ "type": "REGULAR" | "OPENING" }`
   - default to `REGULAR` when omitted
   - reject invalid values with the standard validation error shape
   - if `type = OPENING` and any opening count already exists, return `400` with exact message `"Opening stock count already exists."`
5. Extend inventory serialization so `type` is included in:
   - start response
   - active count response
   - history list items
   - count detail response
6. Extend `GET /api/v1/inventory` to include `opening_count_exists: boolean` alongside the existing paginated history payload.
7. Preserve the current completion path. `OPENING` counts must still create `Surplus` rows and `INVENTORY_SHORTAGE` drafts exactly like `REGULAR` counts.
8. Keep route RBAC unchanged: Inventory Count remains ADMIN-only.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q`
- If you touch any other regressions while implementing, run those files too and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-04-wave-01-opening-inventory-count/backend.md`.
- Use the section shape required by `handoff/README.md`.
- If you discover any additional cross-agent contract detail while implementing, log it in `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- Inventory counts persist and expose `type`.
- Opening-count singleton enforcement works with the exact required message.
- `opening_count_exists` is available to the frontend without requiring a full history scan.
- Existing Inventory Count completion semantics are preserved.
- Migration safety and verification are recorded in handoff.

## Delegation Prompt - Frontend Agent

You are the frontend agent for Wave 1 Phase 4 of the STOQIO WMS project.

Read before coding:
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4, § 5
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-INV-001` through `DEC-INV-007`)
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- backend handoff for this phase after the backend agent finishes
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Goal
- Add the opening-vs-regular start flow to the Inventory Count screen and surface `OPENING` counts clearly in the existing history and detail UI without disturbing the established page state machine.

Non-Negotiable Contract Rules
- Preserve the current page model:
  - active count view when a count is in progress
  - history view when no count is active
  - read-only detail view when a history row is opened
- Use the backend-provided `opening_count_exists` flag. Do not infer opening availability by scanning paginated history pages client-side.
- Keep the existing retry-once-then-fatal-error behavior with `runWithRetry(...)` for count start and data-fetch flows.
- If no opening count exists yet, clicking "Pokreni novu inventuru" must open a choice modal with:
  - "Opening Stock Count"
  - "Regular Count"
- If an opening count already exists, clicking the start button must go directly to creating a `REGULAR` count with no type-selection modal.
- If the backend rejects an `OPENING` start attempt because another opening count was created meanwhile, surface the backend message inline in the start flow instead of escalating to a fatal page error.
- Show a distinct "Opening Stock" badge for opening counts:
  - in history rows, next to the status badge
  - in count headers whenever the viewed count is `OPENING`
- Keep the rest of the Inventory Count behavior unchanged.

Tasks
1. Expand `frontend/src/api/inventory.ts`:
   - add inventory count type typings
   - include `type` in `ActiveCount`, `HistoryItem`, and `CountDetail`
   - include `opening_count_exists` in the history response shape
   - extend `start(...)` to accept an optional `type`
2. Update the history view in `frontend/src/pages/inventory/InventoryCountPage.tsx`:
   - if `opening_count_exists === false`, clicking the start button opens the type-selection modal
   - if `opening_count_exists === true`, clicking the start button directly creates a `REGULAR` count
   - after a successful start, preserve the existing flow of moving into the active count view
3. Add the distinct opening-count badge to history rows.
4. Add the opening-count badge prominently in the count header:
   - active count header if the active count is `OPENING`
   - completed detail header if the viewed count is `OPENING`
5. Preserve current network/server failure handling:
   - retry once via `runWithRetry`
   - use the page-level fatal state only after retryable failures exhaust
   - do not invent a new failure mode for this screen

Verification
- Run at minimum:
  - `cd frontend && npm run lint`
  - `cd frontend && npm run build`

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-04-wave-01-opening-inventory-count/frontend.md`.
- Use the section shape required by `handoff/README.md`.
- If the backend contract differs from the orchestrator brief, log the difference before finalizing.

Done Criteria
- Start button behavior matches the opening/regular selection rules.
- History and header badge behavior is implemented for opening counts.
- Existing Inventory Count page-state and retry semantics remain intact.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 1 Phase 4 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- backend and frontend handoffs for this phase after those agents finish
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_phase2_models.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/api/inventory_count/routes.py`

Goal
- Extend backend regression coverage for the new opening-count contract and verify that the migration path stays healthy.

Tasks
1. Extend `backend/tests/test_inventory_count.py` to cover at minimum:
   - start `OPENING` count -> `201`, response type = `OPENING`
   - start second `OPENING` count -> `400`
   - start `REGULAR` count when an opening count already exists -> `201`
   - start `REGULAR` count when no opening count exists -> `201`
   - history list includes `type`
   - history response includes `opening_count_exists`
   - count detail includes `type`
   - active count response includes `type`
   - complete `OPENING` count -> same discrepancy outcomes as regular count (`Surplus` add + shortage drafts)
2. Keep assertions aligned with the existing standard API error shape and the exact duplicate-opening message `"Opening stock count already exists."`.
3. Reuse the current inventory-count fixture patterns where practical; do not rewrite unrelated module setup.
4. Reverify fresh migration coverage by running `backend/tests/test_phase2_models.py`.

Verification
- Run at minimum:
  - `backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q`
- Also run any additional targeted regressions you touch or depend on, and record them.

Handoff Requirements
- Append your work log to `handoff/wave-01/phase-04-wave-01-opening-inventory-count/testing.md`.
- Use the section shape required by `handoff/README.md`.
- If you find a spec or contract mismatch, log it immediately in your handoff with the precise failing behavior.

Done Criteria
- Inventory-count regressions cover opening start, singleton enforcement, response shapes, and unchanged completion behavior.
- Migration verification is rerun and recorded.
- Verification is recorded in handoff.

## [2026-03-23 20:23] Orchestrator Validation - Wave 1 Phase 4 Opening Inventory Count

Status
- frontend accepted; backend and testing follow-up required before full closeout

Scope
- Reviewed the backend, frontend, and testing deliveries for the opening-inventory-count follow-up.
- Re-ran the delegated Phase 4 verification and an additional full backend suite pass to separate phase-local correctness from repo-wide health.

Docs Read
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/backend.md`
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/frontend.md`
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/testing.md`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/models/enums.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/migrations/versions/b2c3d4e5f6a7_add_inventory_count_type.py`
- `backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_aliases.py`
- `backend/tests/test_articles.py`
- `frontend/src/api/inventory.ts`
- `frontend/src/pages/inventory/InventoryCountPage.tsx`

Commands Run
```bash
git diff -- backend/app/api/inventory_count/routes.py backend/app/models/enums.py backend/app/models/inventory_count.py backend/app/services/inventory_service.py backend/migrations/versions/b2c3d4e5f6a7_add_inventory_count_type.py backend/migrations/versions/a1b2c3d4e5f6_add_article_alias_unique_constraint.py backend/tests/test_inventory_count.py frontend/src/api/inventory.ts frontend/src/pages/inventory/InventoryCountPage.tsx handoff/wave-01/phase-04-wave-01-opening-inventory-count/backend.md handoff/wave-01/phase-04-wave-01-opening-inventory-count/frontend.md handoff/wave-01/phase-04-wave-01-opening-inventory-count/testing.md
backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q
backend/venv/bin/pytest backend/tests -q
cd frontend && npm run lint
cd frontend && npm run build
```

Validation Notes
- Accepted backend work:
- `InventoryCount.type` was added and serialized through start, active, history, and detail responses.
- `GET /api/v1/inventory` now exposes `opening_count_exists`, which is the right contract for the frontend start-flow.
- The new migration `b2c3d4e5f6a7` worked in the delegated SQLite migration regression path, and the prerequisite SQLite fix in `a1b2c3d4e5f6` removed the earlier Phase 2 migration failure.
- Accepted frontend work:
- history view now branches correctly on `opening_count_exists`
- opening/regular start selection is present
- opening badges are rendered in history and count headers
- existing retry/error handling remains intact
- Review finding 1:
- `backend/app/services/inventory_service.py` checks for any `IN_PROGRESS` count before it checks the new opening-singleton rule. If an opening count already exists and is still `IN_PROGRESS`, `POST /api/v1/inventory` with `{ "type": "OPENING" }` returns `COUNT_IN_PROGRESS` instead of the required `"Opening stock count already exists."` contract. This violates the delegated "regardless of status" rule and is not covered by the new tests.
- Review finding 2:
- The repository is still not fully green after this phase. `backend/tests/test_aliases.py` reuses the module-scoped `warehouse_data` fixture from `backend/tests/test_articles.py`, and alias mutations in the alias suite leak into the Warehouse detail assertion in `backend/tests/test_articles.py`. The additional full-suite verification failed at `backend/tests/test_articles.py` on the unexpected alias `"Duplicate Test"`. This is not caused by Phase 4 inventory work, but it means the phase cannot be documented as a clean repo-wide green closeout yet.

Verification
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q` -> `29 passed, 1 warning`
- `backend/venv/bin/pytest backend/tests -q` -> `1 failed, 275 passed`
- `cd frontend && npm run lint` -> passed
- `cd frontend && npm run build` -> passed

Residual Risks
- The opening-singleton API contract is still wrong for the specific case where the existing opening count is itself the active count.
- The backend suite still has the unrelated Wave 1 Phase 3 alias-fixture contamination failure, so repo-level closeout evidence is not yet fully clean.
- SQLite migration verification still emits the known Alembic warning about implicit constraint creation during ALTER; the targeted migration test still passed.

Next Action
- Backend follow-up:
- reorder the opening-singleton check so an existing opening count always yields the required `"Opening stock count already exists."` response for `type = OPENING`, even when that opening count is also the active count
- Testing follow-up:
- add explicit coverage for the "second OPENING while first OPENING is still IN_PROGRESS" case
- Separate repo-health cleanup:
- fix the alias-suite fixture leakage before claiming a repo-wide green backend suite for this wave

## [2026-03-23 20:28] Orchestrator Follow-Up - Validation Fixes Applied

Status
- completed

Scope
- Implemented both review findings directly as orchestrator:
- fixed the Phase 4 opening-singleton contract edge case in backend logic
- fixed the unrelated alias-test fixture leakage that was keeping the full backend suite red

Files Changed
- `backend/app/services/inventory_service.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_aliases.py`
- `handoff/wave-01/phase-04-wave-01-opening-inventory-count/orchestrator.md`
- `handoff/wave-01/phase-03-wave-01-article-aliases/orchestrator.md`

What Changed
- Reordered the `OPENING` singleton check ahead of the generic `IN_PROGRESS` count check in `inventory_service.start_count(...)`, so `POST /api/v1/inventory` with `{ "type": "OPENING" }` now returns the required `"Opening stock count already exists."` response whenever any opening count already exists, even if that opening count is itself the active count.
- Added explicit regression coverage for the "second OPENING while first OPENING is still IN_PROGRESS" case in `backend/tests/test_inventory_count.py`.
- Isolated `backend/tests/test_aliases.py` from the shared Warehouse module fixture by snapshotting baseline alias rows and cleaning any aliases created by each alias test.
- Removed the last inter-test dependency in the alias suite by making the casing-duplicate test create its own setup alias instead of depending on the previous test's side effect.

Verification
- `backend/venv/bin/pytest backend/tests/test_inventory_count.py backend/tests/test_phase2_models.py -q` -> `30 passed, 1 warning`
- `backend/venv/bin/pytest backend/tests/test_aliases.py backend/tests/test_articles.py -q` -> `40 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `277 passed, 1 warning`

Result
- Both previously documented review findings are resolved.
- Wave 1 Phase 4 can now be treated as functionally accepted.
- Repo-wide backend verification is green again apart from the known SQLite Alembic warning.

Residual Risks
- Fresh SQLite migration verification still emits the known Alembic warning about implicit constraint creation during ALTER. The upgrade path still passes.

Next Action
- Refresh the backend-served frontend build and reset the local development database to a clean manual-testing baseline before the user starts post-Phase-4 testing.
