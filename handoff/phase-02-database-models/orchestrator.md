## Phase Summary

Phase
- Phase 2 - Database Models

Objective
- Implement all SQLAlchemy models for the WMS data model.
- Generate the initial Alembic migration.
- Apply the migration and verify the schema is created correctly.
- No feature routes or business logic in this phase.

Source Docs
- `stoqio_docs/05_DATA_MODEL.md` (full)
- `stoqio_docs/07_ARCHITECTURE.md` § 1
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 1.3
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 1.4
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Current Repo Reality
- `backend/app/models/` currently contains only package scaffolding.
- Alembic executable exists in the virtualenv, but the repo currently does not contain a usable Alembic project scaffold (`alembic.ini`, `migrations/env.py`, version directory).
- Backend agent must treat missing Alembic scaffolding as a Phase 2 prerequisite and create the minimal required setup before generating the initial migration.
- This is not optional, because Phase 2 verification depends on `alembic revision --autogenerate` and `alembic upgrade head`.

Delegation Plan
- Backend: implement all model files, import them through `backend/app/models/__init__.py`, create Alembic scaffolding if missing, autogenerate initial migration, apply it, and verify the schema.
- Frontend: no work in this phase.
- Testing: no separate testing agent in this phase; backend agent must provide clear command-level verification in handoff.

Acceptance Criteria
- All 26 model entities are implemented in `backend/app/models/`.
- Field names, types, nullable rules, enums, and constraints match `05_DATA_MODEL.md`.
- `backend/app/models/__init__.py` imports all models so Alembic sees the metadata.
- Initial Alembic migration is generated and applied successfully.
- All 26 tables exist after migration.
- `stock.quantity >= 0` check constraint exists.
- Backend handoff entry fully documents files changed, commands run, and verification results.

Validation Notes
- Backend agent delivered all model files, Alembic scaffold, and the initial migration.
- Manual local PostgreSQL verification was performed after agent delivery:
  - `.env` configured with `DATABASE_URL=postgresql://grzzi@localhost/wms_dev`
  - local `wms_dev` database created
  - `python3 -m flask db upgrade` initially failed with `KeyError: 'formatters'`
  - after guarding `fileConfig(...)` in `backend/migrations/env.py`, upgrade succeeded
  - 27 PostgreSQL tables were verified (`26` entities + `alembic_version`)
- `.gitignore` was updated to ignore `backend/instance/`.
- Decision `DEC-BE-002` logged the Alembic `fileConfig` workaround.
- Orchestrator follow-up implemented the remaining fixes: `Article.article_no` normalization is now enforced in the model layer, and automated Phase 2 schema/migration assertions were added to the backend test suite (`3/3` passing).

Next Action
- Phase 2 is functionally complete and manually verified on PostgreSQL.
- Proceed to Phase 3.

## Delegation Prompt - Backend Agent

You are the backend agent for Phase 2 of the WMS project.

Read before coding:
- `stoqio_docs/05_DATA_MODEL.md` — full document
- `stoqio_docs/07_ARCHITECTURE.md` § 1 (models folder structure)
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 1.3 (audit trail)
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 1.4 (transaction sign convention)
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3 (batch rules, validation, FEFO note)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Goal
- Implement the full SQLAlchemy data model and the initial Alembic migration.
- No API routes, no service logic, no seed script, and no feature workflows in this phase.

Required Output
1. Implement one model file per entity in `backend/app/models/`, matching the Phase 2 scope exactly.
2. Ensure Alembic can autogenerate from the SQLAlchemy metadata.
3. Generate the initial migration and apply it successfully.
4. Record the full work trail in `handoff/phase-02-database-models/backend.md`.

Entities to Implement
- `Supplier`
- `Article`
- `ArticleSupplier`
- `ArticleAlias`
- `Category`
- `UomCatalog`
- `Batch`
- `Stock`
- `Surplus`
- `Draft`
- `DraftGroup`
- `ApprovalAction`
- `Order`
- `OrderLine`
- `Receiving`
- `Transaction`
- `InventoryCount`
- `InventoryCountLine`
- `Employee`
- `PersonalIssuance`
- `AnnualQuota`
- `User`
- `Location`
- `MissingArticleReport`
- `SystemConfig`
- `RoleDisplayName`

Implementation Rules
- Follow `05_DATA_MODEL.md` exactly for field names, nullability, numeric precision, foreign keys, uniqueness, and enum values.
- Keep enum values in English exactly as documented.
- Preserve the documented semantics of nullable `batch_id` everywhere it appears.
- `Article.article_no` must be stored uppercase.
- Use one file per entity as defined by the architecture doc.
- Add explicit model imports to `backend/app/models/__init__.py` so Alembic detects all metadata.
- If helpful, add shared enum definitions or model mixins, but keep the one-file-per-entity structure intact and easy to follow.

Constraints That Must Exist
- `stock.quantity >= 0` as a database CHECK constraint.
- `Draft.client_event_id` UNIQUE.
- `Article.article_no` UNIQUE.
- `User.username` UNIQUE.
- `Employee.employee_id` UNIQUE.
- `RoleDisplayName.role` UNIQUE.
- `SystemConfig.key` UNIQUE.
- Respect all other unique constraints explicitly documented in `05_DATA_MODEL.md`, even if not repeated above.

Relationships and Schema Notes
- Implement the relationships implied by the data model where useful for ORM navigation.
- Do not invent undocumented columns.
- Use `Numeric(14, 3)` and `Numeric(14, 4)` where specified.
- Timestamps should reflect UTC semantics as documented, but do not add business logic beyond schema defaults.
- `batch_id` is nullable on all documented entities where the note says it is nullable.
- `Stock` must include the documented uniqueness for `(location_id, article_id, batch_id)`.
- `Batch` must support the documented article relationship and expiry data, but FEFO logic itself is not implemented in this phase.

Alembic Requirement
- The current repo does not yet contain a complete Alembic project scaffold.
- If `alembic.ini`, `migrations/env.py`, or related files are missing, create the minimal Alembic setup required for this phase before generating the migration.
- Ensure Alembic points at the Flask app metadata correctly.
- Generate the migration with:
  - `alembic revision --autogenerate -m "initial"`
- Apply it with:
  - `alembic upgrade head`

Verification Requirements
- Confirm `alembic upgrade head` completes without errors.
- Confirm all 26 tables exist.
- Confirm the `stock.quantity >= 0` CHECK constraint exists.
- Include the exact commands and their results in handoff.
- If PostgreSQL is unavailable locally, do not fake verification. Log the blocker clearly and stop at the earliest honest point.

Out of Scope
- API endpoints
- route handlers
- service-layer business logic
- seeds
- auth
- frontend changes

Handoff Requirements
- Append your work log to `handoff/phase-02-database-models/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record every file changed.
- Record every command run.
- Record migration generation and upgrade results explicitly.
- If you have to make an assumption not fully defined in docs, log it.
- If you discover a spec gap, add it to `handoff/decisions/decision-log.md` and reference it in your handoff entry.

Done Criteria
- Models are implemented.
- Alembic migration is generated.
- Migration applies successfully.
- Schema verification is recorded.
- Handoff entry is complete.
