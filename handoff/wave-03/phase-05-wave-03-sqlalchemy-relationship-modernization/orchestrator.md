## Phase Summary

Phase
- Wave 3 - Phase 5 - SQLAlchemy Relationship Modernization

Objective
- Replace the remaining legacy `lazy="dynamic"` relationships with SQLAlchemy 2-compatible relationship behavior and explicit query patterns where needed.
- Keep runtime behavior unchanged. This is a maintainability modernization phase, not a feature phase.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-005`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-04-wave-03-draft-serialization-performance-cleanup/orchestrator.md`
- `backend/app/models/article.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/order.py`
- `backend/app/models/order_line.py`
- `backend/app/services/article_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_orders.py`

Current Repo Reality
- The repo still has six `lazy="dynamic"` relationships:
- `Article.batches`
- `Article.aliases`
- `Article.suppliers`
- `DraftGroup.drafts`
- `InventoryCount.lines`
- `Order.lines`
- Current repo search shows real query-object call-site dependence concentrated in:
- `backend/app/services/order_service.py`
- `order.lines.order_by(OrderLine.id.asc()).all()`
- `backend/app/services/inventory_service.py`
- `count.lines.count()`
- `count.lines.filter(...).count()`
- `count.lines.all()`
- `count.lines.first()`
- current backend tests also directly rely on `InventoryCount.lines` query-object behavior in `backend/tests/test_inventory_count.py`
- Current repo search did not show direct query-object usage of:
- `Article.batches`
- `Article.aliases`
- `Article.suppliers`
- `DraftGroup.drafts`
- instead, current article-related service paths already mostly use explicit `Batch.query`, `ArticleAlias.query`, and `ArticleSupplier.query` calls keyed by `article.id`
- backend agent must still verify and document whether any non-obvious direct usage exists before changing those relationships
- This phase is limited to removing legacy `dynamic` behavior and updating touched backend call sites. It is not a broader SQLAlchemy declarative rewrite.

Contract Locks / Clarifications
- Runtime behavior must remain unchanged.
- No API response-shape, ordering, pagination, RBAC, status-code, or error-code changes are in scope.
- Do not broaden this into:
- full typed `Mapped[...]` SQLAlchemy 2 model migration
- global conversion from query API to `select()` API
- unrelated relationship cleanup outside the six legacy `dynamic` relationships
- Do not replace current query-object semantics with silent eager loading.
- Where current code relies on query-like access, move that behavior to explicit model queries.
- Preserve relationship semantics:
- collection mutation where still needed
- `cascade="all, delete-orphan"` behavior
- existing backref/back_populates behavior unless a minimal compatible adjustment is required
- `write_only` is allowed only if the audited usage pattern clearly justifies it. Do not use it speculatively.
- After this phase, repo search should show no remaining `lazy="dynamic"` under `backend/app/models/`.
- No frontend changes are expected in this phase.

Delegation Plan
- Backend:
- audit all six legacy dynamic relationships
- replace each with the most appropriate modern relationship strategy
- refactor all backend call sites that assume the relationship itself is a query object
- add/update targeted backend tests when needed to lock the touched semantics
- Testing:
- validate the touched backend behavior through focused regression coverage
- confirm no regression in the named access patterns
- run the full backend suite after the backend migration lands

Acceptance Criteria
- No model relationships still use `lazy="dynamic"`.
- All touched backend call sites behave correctly after the migration.
- No caller-visible behavior changes are introduced.
- Regression coverage exists for:
- order line access
- draft group draft access
- article batch / alias / supplier access
- inventory count line access
- Full backend suite remains green.
- The phase leaves complete backend, testing, and orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first, then Testing after backend delivery is available. Testing depends on the final relationship strategy and the exact touched call sites.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 3 Phase 5 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-005`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-03/phase-04-wave-03-draft-serialization-performance-cleanup/orchestrator.md`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/orchestrator.md`
- `backend/app/models/article.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/order.py`
- `backend/app/models/order_line.py`
- `backend/app/services/article_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_orders.py`

Goal
- Replace all remaining legacy `lazy="dynamic"` relationships with SQLAlchemy 2-compatible relationship behavior and explicit query patterns where needed, without changing runtime behavior.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend model files, directly affected backend service/api call sites, any directly needed backend tests, and `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/backend.md`.

Current Repo Reality You Must Respect
- The six legacy dynamic relationships are:
- `Article.batches`
- `Article.aliases`
- `Article.suppliers`
- `DraftGroup.drafts`
- `InventoryCount.lines`
- `Order.lines`
- Current repo search suggests actual query-object dependency is concentrated in:
- `backend/app/services/order_service.py` on `order.lines.order_by(...).all()`
- `backend/app/services/inventory_service.py` on `count.lines.count()/filter()/all()/first()`
- `backend/tests/test_inventory_count.py` on direct `count.lines.*` query-object calls
- Current repo search did not show direct query-object usage of `Article.*` or `DraftGroup.drafts`; confirm this explicitly and document the result in handoff before finalizing.

Non-Negotiable Contract Rules
- Keep behavior unchanged from the caller perspective.
- Do not change API shapes, ordering, response fields, status codes, or error codes.
- Do not introduce implicit eager loading that would create hidden performance regressions.
- Where a relationship is currently being used as a query object, replace that usage with explicit model queries rather than trying to preserve query-like behavior on the relationship itself.
- Preserve collection semantics and existing cascades unless a minimal compatible adjustment is required.
- Do not broaden this into a full SQLAlchemy 2 typed-model migration or a general query-style rewrite.
- Use `write_only` only if your audited usage proves it is the right fit for that specific relationship.

Tasks
1. Audit all six current `lazy="dynamic"` relationships and document how each one is actually used in the repo today.
2. Replace each relationship with the most appropriate SQLAlchemy 2-compatible strategy:
- ordinary relationship loading where real collection access is needed
- explicit model queries where query-like behavior is needed
- `write_only` only if it is genuinely justified by the audited usage pattern
3. Update all touched backend call sites that currently assume the relationship itself is a query object.
4. Pay special attention to:
- `Order.lines`
- `InventoryCount.lines`
- any direct test usage relying on query-object methods from those relationships
5. For `Article.batches`, `Article.aliases`, `Article.suppliers`, and `DraftGroup.drafts`, do not invent unnecessary refactors if current runtime usage already prefers explicit queries. Modernize the relationship definitions cleanly and keep behavior stable.
6. Add or update targeted backend tests if needed to lock the touched semantics.
7. Do not leave any `lazy="dynamic"` occurrences under `backend/app/models/`.

Verification
- Run at minimum:
- `rg -n 'lazy="dynamic"' backend/app/models -g '*.py'`
- `cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q`
- If you touch additional shared backend surfaces, run any extra targeted slices needed and record them.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- every touched relationship and the chosen replacement strategy
- which call sites required refactoring
- files changed
- commands run
- tests run
- open issues or residual risk
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- No remaining `lazy="dynamic"` relationships exist in backend models.
- Query-object call sites have been migrated safely.
- Behavior remains unchanged.
- Verification is recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 3 Phase 5 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-005`)
- `handoff/README.md`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/orchestrator.md`
- backend handoff for this phase after backend finishes
- `backend/app/models/article.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/order.py`
- `backend/app/services/article_service.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_drafts.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_orders.py`

Goal
- Lock regression coverage around the touched relationship migration and confirm the backend remains stable after removing legacy `dynamic` relationships.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files and `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/testing.md`.

Non-Negotiable Contract Rules
- This phase is backend maintainability work only. Do not broaden into product behavior changes.
- Focus on proving that relationship modernization did not change caller-visible behavior.
- Prefer extending the existing backend suites over inventing a brand-new test harness.
- Cover the actual touched call sites and the required regression surfaces named in the phase brief.

Minimum Required Coverage
1. Confirm no regression in:
- order line access
- draft group draft access
- article batch / alias / supplier access
- inventory count line access
2. Add or update backend tests around all touched model/service call sites.
3. Run the full backend suite after the relationship migration.

Testing Guidance
- Use existing suites first:
- `backend/tests/test_orders.py`
- `backend/tests/test_inventory_count.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_drafts.py`
- If the backend implementation replaced relationship-query calls with explicit queries, make sure tests still lock:
- ordering
- counts
- filtered subsets
- expected payload content
- access to related rows where collection semantics still matter
- Do not add brittle implementation-detail assertions unless they are needed to lock the accepted behavior.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q`
- `cd backend && venv/bin/python -m pytest -q`
- Confirm repo search shows no remaining model `lazy="dynamic"` relationships, either by your own check or by reviewing the backend delivery.

Handoff Requirements
- Append your work log to `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which relationship-access patterns were explicitly covered
- residual risk, if any

Done Criteria
- Regression coverage exists for all required touched access patterns.
- Full backend suite is green.
- Verification is recorded in handoff.

## [2026-04-03 15:18 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend and testing work for Wave 3 Phase 5.
- Compared the agent handoffs against the actual repo diff.
- Re-ran relationship-migration verification on the touched backend scope plus the full backend suite.

Docs Read
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/backend.md`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/testing.md`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/orchestrator.md`
- `backend/app/models/article.py`
- `backend/app/models/draft_group.py`
- `backend/app/models/inventory_count.py`
- `backend/app/models/order.py`
- `backend/app/services/inventory_service.py`
- `backend/app/services/order_service.py`
- `backend/tests/test_inventory_count.py`

Commands Run
```bash
git status --short
git diff -- backend/app/models/article.py backend/app/models/draft_group.py backend/app/models/inventory_count.py backend/app/models/order.py backend/app/services/article_service.py backend/app/services/inventory_service.py backend/app/services/order_service.py backend/tests/test_articles.py backend/tests/test_drafts.py backend/tests/test_inventory_count.py backend/tests/test_orders.py handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/backend.md handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/testing.md
rg -n 'lazy="dynamic"' backend/app/models -g '*.py'
cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q
cd backend && venv/bin/python -m pytest -q
```

Findings
- None in the implementation.
- Non-blocking handoff note:
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/testing.md` says the backend suite "remains green", which is true for the full-suite run, but the targeted slice listed just above it still reproduces one known cross-module isolation failure in `backend/tests/test_articles.py::TestWarehouseArticles::test_include_inactive_true_includes_inactive_articles`. This is already correctly described as pre-existing and unrelated to the relationship migration.

Validation Result
- Passed:
- repo search shows no remaining `lazy="dynamic"` relationship definitions under `backend/app/models`
- `Article.batches`, `Article.aliases`, `Article.suppliers`, `DraftGroup.drafts`, `InventoryCount.lines`, and `Order.lines` were all modernized away from legacy dynamic loading
- actual query-object call-site migration happened where it materially mattered:
- explicit `InventoryCountLine` queries now replace `count.lines.count()/filter()/all()/first()` patterns in `backend/app/services/inventory_service.py`
- explicit `OrderLine` query now replaces the old `order.lines.order_by(...).all()` path in `backend/app/services/order_service.py`
- the touched inventory-count tests were updated consistently with the new explicit-query pattern
- `cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q` -> `1 failed, 154 passed`
- the single failure is the same pre-existing cross-module fixture-isolation issue documented by the agents and not caused by this phase
- `cd backend && venv/bin/python -m pytest -q` -> `450 passed in 61.28s`

Closeout Decision
- Wave 3 Phase 5 is accepted and closed.

Residual Notes
- The article/inventory cross-module test isolation issue remains real but is pre-existing and outside the scope of this maintainability phase.
- No frontend work was required or introduced.

Next Action
- Treat the current worktree and this orchestrator closeout as the accepted Wave 3 Phase 5 baseline.
- Proceed to Wave 3 Phase 6 - Backend Helper & Numbering Deduplication.

## [2026-04-03 15:31 CEST] Orchestrator Follow-up - Residual Test Isolation Fix

Status
- completed

Scope
- Closed the previously documented non-blocking residual note about the pre-existing article/inventory cross-module test isolation issue.
- Applied the fix directly as orchestrator.

Files Changed
- `backend/tests/test_articles.py`
- `handoff/wave-03/phase-05-wave-03-sqlalchemy-relationship-modernization/orchestrator.md`

What Changed
- The warehouse test `test_include_inactive_true_includes_inactive_articles` no longer assumes that `WH-INACTIVE-003` must be the first search result for `q=inactive`.
- The test now asserts the correct contract instead:
- the warehouse inactive article is present in the paginated response
- that specific returned item remains inactive
- This keeps the test aligned with the actual list-contract, which allows other matching inactive articles from other module fixtures to coexist in the same result set.

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q
cd backend && venv/bin/python -m pytest -q
```

Validation Result
- `cd backend && venv/bin/python -m pytest tests/test_orders.py tests/test_inventory_count.py tests/test_articles.py tests/test_drafts.py -q` -> `155 passed`
- `cd backend && venv/bin/python -m pytest -q` -> `450 passed in 60.74s`

Closeout Note
- The earlier residual note about the article/inventory cross-module test isolation issue is now resolved.
