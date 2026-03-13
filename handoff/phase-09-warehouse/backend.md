## 2026-03-13 16:45:21 CET

### Status
Completed

### Scope
Implemented the Phase 9 Warehouse backend under `/api/v1/articles`, preserving the Draft Entry / Receiving exact-match lookup contract while adding Warehouse list/detail/create/update/deactivate/transactions/barcode-scaffold/lookups behavior.

### Docs Read
- `stoqio_docs/13_UI_WAREHOUSE.md`
- `stoqio_docs/09_UI_DRAFT_ENTRY.md` § 5, § 12, § 13
- `stoqio_docs/11_UI_RECEIVING.md` § 7, § 9
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 2, § 11
- `stoqio_docs/05_DATA_MODEL.md` § 2, § 3, § 4, § 7, § 8, § 9, § 16
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3.1, § 3.3, § 4
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md` (`DEC-FE-004`, `DEC-WH-001`, added `DEC-WH-002`, `DEC-WH-003`)
- `handoff/README.md`
- `handoff/phase-09-warehouse/orchestrator.md`

### Files Changed
- `backend/app/api/articles/routes.py`
- `backend/app/services/article_service.py`
- `backend/tests/test_articles.py`
- `handoff/decisions/decision-log.md`
- `handoff/phase-09-warehouse/backend.md`

### Commands Run
- `backend/venv/bin/pytest backend/tests/test_articles.py -q`
- `backend/venv/bin/pytest backend/tests/test_drafts.py -q`
- `backend/venv/bin/pytest backend/tests/test_phase2_models.py::test_article_number_is_normalized_to_uppercase_and_collides_on_case_only_duplicate -q`
- `backend/venv/bin/pytest backend/tests -q`

### Tests
- `backend/tests/test_articles.py -q` → `12 passed`
- `backend/tests/test_drafts.py -q` → `30 passed`
- `backend/tests/test_phase2_models.py::test_article_number_is_normalized_to_uppercase_and_collides_on_case_only_duplicate -q` → `1 passed`
- `backend/tests -q` → `129 passed`

### Open Issues / Risks
- Current v1 schema has no `UomCatalog.is_active`; Phase 9 therefore treats all UOM rows as active and cannot enforce inactive-UOM filtering yet. Logged in `DEC-WH-003`.
- Route-mode disambiguation for bare `GET /api/v1/articles` is now explicit: Warehouse clients must send pagination/filter params to enter list mode. Logged in `DEC-WH-002`.

### Next Recommended Step
- Frontend agent should call the Warehouse list with explicit pagination params (`page` and `per_page`) and use the new `/api/v1/articles/lookups/categories` and `/api/v1/articles/lookups/uoms` endpoints instead of assuming hardcoded filter/form values.
