## Phase Summary

Phase
- Wave 2 - Phase 5 - Explicit Shortage Draft Linkage + Query Helper Consolidation

Objective
- Replace the hidden inventory-shortage draft linkage convention with an explicit nullable foreign key on `draft`.
- Remove duplicated route-level query parsing helpers from the six targeted backend route modules by centralizing them in `backend/app/utils/validators.py`.
- Keep this phase backend-only plus testing. No frontend changes are in scope.

Source Docs
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-026`, `F-034`)
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 17, § 18
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-014`, relevant inventory decisions)
- `backend/app/models/draft.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/utils/validators.py`
- `backend/app/api/articles/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_i18n.py`

Current Repo Reality
- `backend/app/services/inventory_service.py` currently links shortage drafts back to a completed count through the deterministic `Draft.client_event_id` pattern `inv-count-{count_id}-line-{line_id}`.
- `_get_shortage_drafts_summary(count_id)` currently derives shortage summary membership through `Draft.client_event_id.like(...)`, not through an explicit relational link.
- `backend/app/models/draft.py` currently has no `inventory_count_id` column or relationship to `InventoryCount`.
- Existing inventory-count regression tests in `backend/tests/test_inventory_count.py` currently assert the LIKE-pattern linkage directly.
- `backend/app/utils/validators.py` currently contains reusable batch / quantity / note helpers only. It does not yet expose shared query-param parsing helpers.
- `_parse_positive_int(...)` is duplicated in all six targeted route modules:
  - `backend/app/api/articles/routes.py`
  - `backend/app/api/orders/routes.py`
  - `backend/app/api/receiving/routes.py`
  - `backend/app/api/inventory_count/routes.py`
  - `backend/app/api/employees/routes.py`
  - `backend/app/api/settings/routes.py`
- `_parse_bool_query(...)` is also duplicated route-locally where needed, with one current semantic outlier:
  - `backend/app/api/articles/routes.py`
  - `backend/app/api/employees/routes.py`
  - `backend/app/api/settings/routes.py`
- `backend/app/utils/i18n.py` already translates common `VALIDATION_ERROR` fallback patterns such as:
  - `{field} must be a valid integer.`
  - `{field} must be greater than zero.`
  - `{field} must be 'true' or 'false'.`
  so this phase must preserve those message shapes instead of inventing new phrasing.
- Repo baseline before this phase is currently green:
  - backend full suite -> `371 passed`
  - frontend tests -> `17 passed`
  - frontend lint/build -> passed

Contract Locks / Clarifications
- This phase is backend + testing only. Do not delegate frontend work and do not widen frontend scope opportunistically.
- Existing database contents are disposable test data. This phase is explicitly **fresh-database only**:
  - no retroactive data backfill is required
  - existing rows may remain `NULL`
  - a fresh database after `alembic upgrade head` is the only supported post-phase state
- The new draft linkage must be explicit and relational:
  - add nullable `Draft.inventory_count_id`
  - foreign key target: `inventory_count.id`
  - regular `OUTBOUND` drafts keep `inventory_count_id = NULL`
  - shortage drafts created by Inventory Count completion must set `inventory_count_id = count.id`
- Delete semantics are locked as:
  - no cascade delete from `InventoryCount` to `Draft`
  - if an inventory count row is deleted, linked drafts must survive and the FK must become `NULL`
  - implement this with database-level behavior suitable for PostgreSQL, not just ORM-side hope
- Do not remove `Draft.client_event_id` from the schema or from normal draft-idempotency flows.
- Only retire the hidden shortage-linkage convention:
  - `_get_shortage_drafts_summary(...)` must stop using the `LIKE 'inv-count-{id}-line-%'` pattern
  - inventory shortage summary logic must rely on `inventory_count_id`
  - if `client_event_id` remains populated on shortage drafts, treat it as inert historical metadata, not as the active linkage contract
- This phase does not require broad API response expansion.
  - Review whether `inventory_count_id` is genuinely useful in draft / approval serialization.
  - If no existing consumer benefits, do not widen response shapes just because the field exists.
  - If you do expose it somewhere, keep the addition minimal and consistent.
- Shared query parsing helper scope is limited to the six named route modules. Do not turn this into a backend-wide parsing-refactor sweep.
- Validation message semantics must stay compatible with the existing i18n fallback catalog:
  - use consistent field formatting
  - avoid introducing quoted-field variants in some modules and unquoted variants in others
  - keep the canonical English fallback shapes aligned with existing translation patterns
- Current repo reality includes one outlier: `backend/app/api/employees/routes.py` currently defaults invalid boolean query strings instead of raising a validation error.
  - The phase goal is **standardization** on the shared helper contract requested by the user.
  - If this intentionally changes that one outlier edge case, record it explicitly in handoff and cover it with tests instead of silently treating it as “unchanged”.
- Migration discipline must follow `DEC-BE-014`:
  - do not validate the schema change on SQLite only
  - verify that a fresh PostgreSQL `alembic upgrade head` succeeds on a clean database
  - even though this phase adds no enum type, treat PostgreSQL DDL behavior as first-class verification, not an afterthought

Delegation Plan
- Backend:
- add the explicit `Draft.inventory_count_id` column + relationship, ship the fresh-db-safe migration, replace the shortage-summary LIKE lookup with FK logic, and centralize the duplicated route query helpers in `validators.py`
- Frontend:
- none in this phase
- Testing:
- update inventory-count regression coverage for the FK-based linkage, add focused validator-helper coverage, and rerun the full backend suite after the route-helper consolidation

Acceptance Criteria
- `draft.inventory_count_id` exists as a nullable integer FK to `inventory_count.id`.
- The FK behavior is non-cascading and leaves drafts intact with `inventory_count_id = NULL` if a linked count row is deleted.
- Fresh `alembic upgrade head` completes successfully on a clean PostgreSQL database.
- Fresh SQLite upgrade-to-head still completes successfully for the repo's local test path.
- Inventory Count completion creates shortage drafts with `inventory_count_id` populated correctly.
- `_get_shortage_drafts_summary(count_id)` no longer uses a `client_event_id LIKE ...` pattern and instead filters directly on `inventory_count_id`.
- Drafts with `inventory_count_id = NULL` do not appear in any count's shortage summary.
- Regular daily outbound drafts continue to have `inventory_count_id = NULL`.
- `backend/app/utils/validators.py` exposes shared `parse_positive_int(...)` and `parse_bool_query(...)` helpers.
- No targeted route module retains a local copy of `_parse_positive_int(...)` or `_parse_bool_query(...)`.
- Validation outcomes remain localization-compatible and consistent across the touched routes.
- All existing backend tests pass, and the new regression tests for the FK linkage and shared validators pass.

Validation Notes
- None yet.

Next Action
- Delegate to the Backend Agent first so the schema + service + route contract is explicit, then let the Testing Agent lock the new baseline and rerun the full backend suite.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 2 Phase 5 of the STOQIO WMS project.

You are not alone in the codebase. Do not revert unrelated work. Your ownership is limited to the backend schema/model/service/route changes required by this phase, any narrowly targeted backend tests truly needed to support your implementation, and `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/backend.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-026`, `F-034`)
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 17, § 18
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-014` and relevant inventory-count decisions)
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/orchestrator.md`
- `backend/app/models/draft.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/utils/validators.py`
- `backend/app/api/articles/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_phase2_models.py`

Goal
- Replace the hidden inventory-shortage linkage convention with an explicit nullable `Draft.inventory_count_id` FK, and centralize the duplicated route query parsing helpers in `backend/app/utils/validators.py` without broadening backend scope.

Current Repo Reality
- Shortage drafts are currently linked back to a completed count only through the `client_event_id` naming pattern `inv-count-{count_id}-line-{line_id}`.
- `_get_shortage_drafts_summary(...)` currently uses `Draft.client_event_id.like(...)` to find related shortage drafts.
- `Draft` currently has no `inventory_count_id`.
- The six targeted route modules still carry local `_parse_positive_int(...)` and/or `_parse_bool_query(...)` copies.
- `backend/app/utils/i18n.py` already recognizes the canonical fallback validation message patterns, so helper wording must stay aligned with those patterns.

Non-Negotiable Contract Rules
- Treat this phase as **fresh-db only**:
- no data backfill is required
- existing rows may remain `NULL`
- a fresh database after `alembic upgrade head` is the only supported post-phase state
- Add a nullable integer column on `draft`:
- name: `inventory_count_id`
- FK target: `inventory_count.id`
- regular outbound drafts must keep this field `NULL`
- inventory shortage drafts created by `complete_count(...)` must populate it
- Delete semantics are locked:
- no cascade delete from `InventoryCount` to `Draft`
- if a linked `InventoryCount` row is deleted, drafts must remain and `inventory_count_id` must become `NULL`
- Do not remove `Draft.client_event_id` from the schema or from normal draft-idempotency flows.
- Do remove the hidden shortage-linkage dependency:
- `_get_shortage_drafts_summary(...)` must stop using `LIKE 'inv-count-{count_id}-line-%'`
- no new summary logic may depend on `client_event_id` naming
- Review serialization for `inventory_count_id`, but do not widen API responses unless a current consumer or regression test truly benefits.
- Add shared helpers to `backend/app/utils/validators.py`:
- `parse_positive_int(value, *, field_name, default)`
- `parse_bool_query(value, *, field_name, default)`
- Keep the canonical fallback wording localization-compatible:
- `{field} must be a valid integer.`
- `{field} must be greater than zero.`
- `{field} must be 'true' or 'false'.`
- Remove local helper copies from exactly these route files and replace them with shared imports:
- `backend/app/api/articles/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/settings/routes.py`
- Do not broaden this into a service-layer parsing refactor or a repo-wide validation framework rewrite.
- Migration discipline must follow `DEC-BE-014`:
- do not rely on SQLite-only validation
- verify a fresh PostgreSQL `alembic upgrade head` on a clean database
- if any dialect-specific DDL handling is needed for the FK addition, implement it explicitly and document it

Tasks
1. Add `Draft.inventory_count_id` as a nullable FK column and relationship in the SQLAlchemy model layer.
2. Create the Alembic migration for the new column and FK.
3. Ensure the FK behavior matches the locked contract:
- no cascade delete
- deleting a count leaves linked drafts intact and nulls the FK
4. Update `inventory_service.complete_count(...)` so every shortage draft created there gets `inventory_count_id = count.id`.
5. Update `_get_shortage_drafts_summary(count_id)` to filter directly on `inventory_count_id` and remove the LIKE-pattern logic entirely.
6. Retire the shortage-linkage dependency on `client_event_id` naming while keeping the column itself intact for idempotency / existing draft flows.
7. Review existing draft / approval serialization for `inventory_count_id` and only expose it if there is a concrete current consumer or test benefit.
8. Add shared `parse_positive_int(...)` and `parse_bool_query(...)` helpers to `backend/app/utils/validators.py`.
9. Remove the local copies from the six targeted route files and replace them with shared imports.
10. Standardize validation message formatting so localization stays consistent through `backend/app/utils/i18n.py`.
11. Keep route behavior unchanged except where the user-requested helper standardization intentionally resolves the existing employees boolean-query outlier.
12. Append your work log to `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/backend.md` using the required section shape from `handoff/README.md`.

Suggested Implementation Direction
- Prefer a tiny shared structured exception in `backend/app/utils/validators.py` for the new query helpers rather than coupling validators to one route module's service exception class.
- Route modules can catch that shared validation exception and forward it through the existing `_error(...)` response path without refactoring their service layers.
- Keep the migration narrow:
- add the column
- add the FK with the required delete behavior
- do not attempt a backfill
- do not mix in unrelated schema cleanup

Verification
- Run the smallest relevant backend verification you need, but at minimum cover the touched schema + inventory + route-validation surfaces.
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_inventory_count.py tests/test_phase2_models.py -q`
- If you touch validation-message expectations or add shared-helper tests directly, run those targeted files too and record them.
- Fresh migration verification must include:
- a clean PostgreSQL `alembic upgrade head`
- the repo's normal fresh SQLite upgrade path

Done Criteria
- Fresh-db schema includes `draft.inventory_count_id` with the required FK behavior.
- Inventory shortage drafts populate the FK and shortage summary logic uses it directly.
- The six targeted route modules no longer carry local query helper copies.
- Validation wording remains localization-compatible.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 2 Phase 5 of the STOQIO WMS project.

You are not alone in the codebase. Do not revert unrelated work. Your ownership is limited to backend regression coverage and `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/testing.md`.

Read before coding:
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-026`, `F-034`)
- `stoqio_docs/16_UI_INVENTORY_COUNT.md`
- `stoqio_docs/05_DATA_MODEL.md` § 10, § 17, § 18
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/orchestrator.md`
- backend handoff for this phase after the Backend Agent finishes
- `backend/app/services/inventory_service.py`
- `backend/app/utils/validators.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_phase2_models.py`

Goal
- Lock regression coverage for the explicit inventory-shortage FK linkage and for the shared route query parsing helpers after the backend consolidation.

Current Repo Reality
- Existing inventory-count tests currently assert the old `client_event_id LIKE ...` linkage pattern directly.
- There is not yet dedicated automated coverage for shared query-param parsing helpers in `backend/app/utils/validators.py`.
- The backend suite is currently green, so this phase should extend coverage surgically rather than rewrite broad test scaffolding.

Non-Negotiable Test Rules
- Update existing inventory-count tests to reflect the new explicit linkage model:
- shortage drafts created on count completion must have `inventory_count_id` populated
- shortage summary must be validated through the FK-based behavior, not the old LIKE convention
- Add regression coverage proving:
- a draft with `inventory_count_id = NULL` does not appear in any count's shortage summary
- regular daily outbound drafts remain `inventory_count_id = NULL`
- Add focused unit coverage for the new shared validators helpers:
- `parse_positive_int(...)`
- `parse_bool_query(...)`
- Keep validation-message expectations aligned with the existing i18n fallback patterns.
- Do not broaden this into a route-by-route rewrite unless the backend change genuinely forces it.
- If the backend standardization intentionally changes the old employees invalid-bool outlier behavior, cover that chosen behavior explicitly instead of silently preserving drift.

Tasks
1. Update inventory-count tests so shortage drafts are asserted via `inventory_count_id`, not via `client_event_id LIKE ...`.
2. Add a test confirming `inventory_count_id` is populated on shortage drafts after completing a count.
3. Add a test confirming shortage summary counts are computed correctly through the FK-based query.
4. Add a regression test proving drafts with `inventory_count_id = NULL` do not appear in any count's shortage summary.
5. Confirm regular `DAILY_OUTBOUND` drafts keep `inventory_count_id = NULL` and are unaffected by this phase.
6. Add focused unit tests for `parse_positive_int(...)`:
- valid positive integer -> returns parsed int
- zero -> validation error
- negative -> validation error
- non-numeric string -> validation error
- `None` -> returns default
7. Add focused unit tests for `parse_bool_query(...)`:
- `"true"` and `"1"` -> `True`
- `"false"` and `"0"` -> `False`
- `None` -> returns default
- invalid string -> validation error
8. Rerun the full backend test suite and record the result.
9. Append your work log to `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/testing.md` using the required section shape from `handoff/README.md`.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_inventory_count.py -q`
- `cd backend && venv/bin/python -m pytest tests/test_i18n.py -q`
- `cd backend && venv/bin/python -m pytest -q`
- If you add a new dedicated validator test file, run it explicitly and record it.

Done Criteria
- Automated tests prove the explicit inventory shortage linkage works.
- Automated tests prove the shared validator helpers behave as intended.
- The full backend suite remains green.
- Verification is recorded in handoff.

## [2026-03-27 20:59 CET] Orchestrator Validation - Wave 2 Phase 5 Explicit Shortage Draft Linkage + Query Helper Consolidation

Status
- accepted

Scope
- Reviewed the delivered backend and testing handoffs for Wave 2 Phase 5.
- Re-read the touched schema, service, route, validator, migration, and test files against the locked phase contract.
- Re-ran the targeted Phase 5 backend verification, the full backend suite, a fresh SQLite `alembic upgrade head`, and an independent fresh PostgreSQL `alembic upgrade head` on a temporary local database.
- Performed a direct PostgreSQL schema inspection to confirm the new `draft.inventory_count_id` FK exists and uses `ON DELETE SET NULL`.

Docs Read
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/backend.md`
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/testing.md`
- `handoff/phase-05-wave-02-shortage-linkage-query-helper-cleanup/orchestrator.md`
- `handoff/decisions/decision-log.md` (`DEC-BE-014`)
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-026`, `F-034`)

Files Reviewed
- `backend/app/models/draft.py`
- `backend/app/models/inventory_count.py`
- `backend/app/services/inventory_service.py`
- `backend/app/utils/validators.py`
- `backend/app/api/articles/routes.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/api/inventory_count/routes.py`
- `backend/app/api/employees/routes.py`
- `backend/app/api/settings/routes.py`
- `backend/migrations/versions/c3d4e5f6a7b8_add_partial_to_draft_group_status.py`
- `backend/migrations/versions/d4e5f6a7b8c9_add_draft_inventory_count_link.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_phase2_models.py`
- `backend/tests/test_validators.py`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_inventory_count.py tests/test_validators.py tests/test_i18n.py tests/test_phase2_models.py -q
cd backend && venv/bin/python -m pytest -q

tmp_db=$(mktemp /tmp/stoqio_phase5_review_XXXXXX.db)
cd backend
FLASK_ENV=development DATABASE_URL=sqlite:///$tmp_db JWT_SECRET_KEY=test-jwt-secret-key-suite-2026-0001 venv/bin/alembic upgrade head

# fresh PostgreSQL review path on a temporary local DB
cd backend && venv/bin/python -c "import uuid, psycopg2; name='stoqio_phase5_review_' + uuid.uuid4().hex[:8]; conn=psycopg2.connect('postgresql://grzzi@localhost/postgres'); conn.autocommit=True; cur=conn.cursor(); cur.execute(f'CREATE DATABASE {name}'); cur.close(); conn.close(); print(name)"
FLASK_ENV=development DATABASE_URL=postgresql://grzzi@localhost/stoqio_phase5_review_fc217159 JWT_SECRET_KEY=test-jwt-secret-key-suite-2026-0001 venv/bin/alembic upgrade head

cd backend && venv/bin/python - <<'PY'
import psycopg2
conn = psycopg2.connect('postgresql://grzzi@localhost/stoqio_phase5_review_fc217159')
cur = conn.cursor()
cur.execute("""
SELECT tc.constraint_name, rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.referential_constraints rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.table_name = 'draft' AND tc.constraint_type = 'FOREIGN KEY'
""")
print(cur.fetchall())
cur.execute("""
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'draft' AND column_name = 'inventory_count_id'
""")
print(cur.fetchall())
cur.close()
conn.close()
PY
```

Validation Result
- `cd backend && venv/bin/python -m pytest tests/test_inventory_count.py tests/test_validators.py tests/test_i18n.py tests/test_phase2_models.py -q` -> `73 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `386 passed`
- fresh SQLite `alembic upgrade head` on a temporary DB -> passed
- fresh PostgreSQL `alembic upgrade head` on temporary DB `stoqio_phase5_review_fc217159` -> passed
- PostgreSQL schema inspection confirmed:
  - FK `fk_draft_inventory_count_id_inventory_count` exists on `draft.inventory_count_id`
  - delete rule is `SET NULL`

Accepted Work
- `Draft.inventory_count_id` is now an explicit nullable FK with the required non-cascading delete behavior.
- Inventory shortage summary logic no longer depends on `client_event_id LIKE ...`; it now filters directly through the explicit FK.
- The six targeted route modules no longer carry local `_parse_positive_int(...)` / `_parse_bool_query(...)` copies.
- Validation message wording remains aligned with the existing i18n fallback catalog patterns.
- The PostgreSQL fresh-upgrade path is now healthy again because the prior `c3d4e5f6a7b8` enum migration was corrected to use an autocommit block before subsequent updates.

Findings
- No blocking implementation findings were discovered in this review pass.

Residual Notes
- `backend/app/api/employees/routes.py` now returns a `400 VALIDATION_ERROR` for invalid `include_inactive` boolean query strings instead of silently defaulting. This is accepted as an intentional result of the user-requested helper standardization, not treated as accidental drift.
- `Draft.client_event_id` remains populated on inventory shortage drafts as inert metadata; the active relational linkage is now `inventory_count_id`.
- `stoqio_docs/05_DATA_MODEL.md` does not yet document the new `Draft.inventory_count_id` field, so there is now minor docs drift outside the handoff trail.

Closeout Decision
- Wave 2 Phase 5 is formally accepted.

Next Action
- Treat the current repo state and this handoff trail as the accepted baseline for the next Wave 2 phase.
