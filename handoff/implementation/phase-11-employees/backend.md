# Phase 11 — Employees Backend

## Status

COMPLETE. All 42 new employee tests pass. Full suite: 181 passed, 0 failed.

---

## Scope

Implemented the full Employees backend:
- Employee CRUD (`list`, `get`, `create`, `update`, `deactivate`)
- Quota overview (`GET /{id}/quotas`)
- Issuance history (`GET /{id}/issuances`)
- Issuance article lookup (`GET /lookups/articles`)
- Issuance dry-run check (`POST /{id}/issuances/check`)
- Issuance create (`POST /{id}/issuances`)
- Blueprint registered in `api/__init__.py`

---

## Docs Read

- `stoqio_docs/15_UI_EMPLOYEES.md` — full
- `stoqio_docs/05_DATA_MODEL.md` § 5, 19, 20, 21
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `stoqio_docs/03_RBAC.md`
- `handoff/decisions/decision-log.md`
- Phase 11 orchestration note (all locked contract rules)

---

## Files Changed

| File | Action |
|------|--------|
| `backend/app/services/employee_service.py` | **Created** — all business logic |
| `backend/app/api/employees/routes.py` | **Created** — thin routes, RBAC decorators |
| `backend/app/api/employees/__init__.py` | **Updated** — added package docstring |
| `backend/app/api/__init__.py` | **Updated** — registered `employees_bp` |
| `backend/tests/test_employees.py` | **Created** — 42 integration tests |

---

## Commands Run

```bash
backend/venv/bin/pytest backend/tests/test_employees.py -q   # 42 passed
backend/venv/bin/pytest backend/tests --tb=line -q            # 181 passed
```

---

## Tests

42 tests in `test_employees.py` covering:
- Employee CRUD (create, list, search, inactive toggle, get, update, deactivate)
- RBAC: WAREHOUSE_STAFF GET-only, MANAGER and non-auth blocked
- Quota overview: empty, category-level, article-level, WAREHOUSE_STAFF read
- Issuance history: empty, field shape (issued_by is username string, batch_code present)
- Article lookup: personal-issue filter, non-PI exclusion, batches with available qty, FEFO ordered
- Check endpoint: NO_QUOTA, OK, BLOCKED (→ 400), NOT_PERSONAL_ISSUE, BATCH_REQUIRED, WSTAFF forbidden
- Create: basic, stock decrement, Transaction created, batch article, errors, WARN (201 + warning), BLOCK (400), quota priority (emp+article > global), batch_code in history

---

## Implementation Decisions

### DEC-EMP-001 (logged in decision-log.md)
`PersonalIssuance` decrements the matching `Stock` row within the same DB transaction. For batch-tracked articles the specific `(location_id, article_id, batch_id)` row is decremented. For non-batch articles the `(location_id, article_id, NULL)` row is decremented when it exists; if no stock row exists the Transaction audit record is still written (protective-equipment articles may be issued before stock is formally received via the normal receiving flow).

### Quota Priority — strictly followed
1. `employee_id + article_id` override (highest)
2. `article_id` override, `employee_id` NULL
3. `job_title + category_id` default, `article_id` NULL, `employee_id` NULL

### Test isolation note
Tests add AnnualQuota rows to the shared in-memory DB. To prevent quota state from leaking across tests (polluting priority lookups), quota tests that exercise article-level logic use `employee_id`-specific quotas (highest priority) rather than global article overrides. This is a deliberate test-design choice, not a code issue.

---

## Open Issues / Risks

- No stock decrement for non-batch articles when no stock row exists (documented — acceptable per v1 scope).
- Transaction requires `Location.id = 1` (per DEC-BE-003). If no location exists at runtime, Transaction is skipped silently; PersonalIssuance is still committed. Consider adding a startup guard if this is a concern.
- Quota year boundary: `reset_month` > 1 (e.g., March fiscal year) is supported but not explicitly tested. Default seed data uses `reset_month = 1`.
- Category-level quota `received` sums across ALL articles in the category (not just those with article-level overrides excluded). This is intentional — category and article quotas are independent constraints.

---

## Next Recommended Step

Frontend agent: implement `EmployeesPage` and `EmployeeDetailPage` using the locked API contract. All 10 endpoints are live. The `POST /issuances/check` dry-run and `GET /lookups/articles` (with inline `batches[]` FEFO-ordered) are ready for the issuance form.
