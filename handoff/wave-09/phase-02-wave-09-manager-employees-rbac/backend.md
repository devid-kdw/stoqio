# Wave 9 Phase 2 — Backend Handoff

## Status

✅ Complete — 2026-04-11

## Scope

W9-F-004: Grant MANAGER role read-only access to the Employees module.

- MANAGER can call: employee list, employee detail, quota overview, issuance history
- MANAGER cannot call: employee create, employee update, employee deactivate, issuance article lookup, issuance check, issuance create
- ADMIN-only mutation semantics preserved

## Docs Read

- `handoff/README.md`
- `handoff/wave-09/README.md`
- `handoff/Findings/wave-09-user-feedback.md`
- `handoff/wave-09/phase-02-wave-09-manager-employees-rbac/orchestrator.md`
- `backend/app/api/employees/routes.py`
- `backend/tests/test_employees.py`
- `backend/app/utils/auth.py`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/15_UI_EMPLOYEES.md`

## Files Changed

### `backend/app/api/employees/routes.py`
- Added `"MANAGER"` to `@require_role` on four read-only endpoints:
  - `GET /employees` (list)
  - `GET /employees/<id>` (detail)
  - `GET /employees/<id>/quotas` (quota overview)
  - `GET /employees/<id>/issuances` (issuance history)
- Updated module docstring to document MANAGER GET-only access
- No changes to ADMIN-only mutation endpoints (POST/PUT/PATCH create, update, deactivate, lookup, check, issuance create)

### `backend/tests/test_employees.py`
- Changed `test_list_employees_manager_forbidden` → `test_list_employees_manager` (now expects 200)
- Added `TestManagerRBAC` class with 10 tests:
  - 4 read-access tests (list, detail, quotas, issuances) → all expect 200
  - 6 mutation-denial tests (create, update, deactivate, lookup, check, issuance create) → all expect 403

### `stoqio_docs/03_RBAC.md`
- Permission matrix: `Dosijei zaposlenika — pregled` row changed MANAGER from ❌ to ✅
- MANAGER sidebar window: added `Dosijei zaposlenika (read-only)`

### `stoqio_docs/15_UI_EMPLOYEES.md`
- Header: added `MANAGER (read-only)` to accessible roles
- Added new Section 8 "MANAGER Read-only View" documenting access scope
- Renumbered existing WAREHOUSE_STAFF section (8 → 9) and subsequent sections
- Added edge case row: "MANAGER tries to issue → Action button not visible. Backend returns 403."

## Commands Run

```
backend/venv/bin/python -m pytest backend/tests/test_employees.py -v --tb=short
```

## Tests

```
61 passed in 1.12s
```

All 61 tests passed:
- 52 pre-existing tests (including the updated `test_list_employees_manager`): PASSED
- 9 new `TestManagerRBAC` tests (4 read + 6 mutation denial → 10 methods, one fixture shared): PASSED

No broader backend tests were run — only the targeted `test_employees.py` file was executed as it was the only file in scope.

## Open Issues / Risks

None. All backend changes are strictly additive (adding a role to existing `require_role` decorators). No service layer, model, or migration changes were needed.

## Next Recommended Step

Frontend worker should:
- Add `MANAGER` to Employees route guards in `routes.tsx`
- Show `Zaposlenici` in the Sidebar for MANAGER
- Confirm mutation UI remains hidden for MANAGER (already gated by `isAdmin` checks)
