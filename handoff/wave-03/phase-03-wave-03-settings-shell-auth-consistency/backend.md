# Backend Handoff — Wave 3 Phase 3: Settings Shell Auth Consistency

---

## Entry 1 — 2026-04-03

### Status
COMPLETE

### Scope
W3-003: Align `GET /api/v1/settings/shell` with the active-user semantics enforced
by the rest of the protected API.  Route-only change; no shared auth logic was
modified.

### Docs Read
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (W3-003 finding)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/18_UI_SETTINGS.md`
- `handoff/wave-03/phase-01-*/orchestrator.md` and `backend.md`
- `handoff/wave-03/phase-02-*/orchestrator.md`

### Files Changed

| File | Change |
|------|--------|
| `backend/app/api/settings/routes.py` | Replaced `verify_jwt_in_request()` guard + removed unused import with `@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")` decorator on `get_shell_settings` |
| `backend/tests/test_settings.py` | Seeded two new users (`settings_staff` / WAREHOUSE_STAFF, `settings_operator` / OPERATOR) in `settings_data` fixture and `reset_settings_state`; added four new test functions for W3-003 coverage |

### What Changed in routes.py

**Before:**
```python
from flask_jwt_extended import verify_jwt_in_request
...
@settings_bp.route("/settings/shell", methods=["GET"])
def get_shell_settings():
    verify_jwt_in_request()
    ...
```

**After:**
```python
@settings_bp.route("/settings/shell", methods=["GET"])
@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")
def get_shell_settings():
    ...
```

`verify_jwt_in_request` import was removed from routes.py; it is already used
internally by `_build_role_wrapper` in `auth.py`.

`require_role` / `_build_role_wrapper` enforces:
- valid JWT (missing/invalid → 401 via Flask-JWT-Extended error handler)
- user row exists (missing → 401)
- `user.is_active` (inactive → 401)
- role is in the allowed set (forbidden role → 403, not reachable for this endpoint
  since all five defined roles are listed)

No changes to `settings_service.get_shell_settings()` or the payload shape.

### Fix Scope
Route-only.  No shared auth helper was modified.

### Commands Run
```
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q
```

### Tests

| Test | Result |
|------|--------|
| `test_shell_endpoint_accessible_to_admin` (pre-existing) | PASS |
| `test_shell_endpoint_accessible_to_manager` (pre-existing) | PASS |
| `test_shell_endpoint_accessible_to_viewer` (pre-existing) | PASS |
| `test_shell_endpoint_anonymous_rejected` (pre-existing) | PASS |
| `test_shell_endpoint_does_not_expose_admin_only_fields` (pre-existing) | PASS |
| `test_shell_role_display_names_match_defaults` (pre-existing) | PASS |
| `test_shell_endpoint_accessible_to_warehouse_staff` (new) | PASS |
| `test_shell_endpoint_accessible_to_operator` (new) | PASS |
| `test_shell_endpoint_inactive_user_rejected` (new) | PASS |
| `test_shell_endpoint_nonexistent_user_rejected` (new) | PASS |
| Full `tests/test_settings.py` | 52/52 PASS |
| `tests/test_auth.py` + `tests/test_settings.py` | 92/92 PASS |

**Note on inactive-user test session behaviour:** The test modifies `user.is_active`
via `_db.session` directly (no nested `app.app_context()`) so the commit is made on
the same SQLAlchemy scoped session that request handlers will use.  An earlier
draft that used a nested `with app.app_context():` block committed to a different
session scope, causing the outer session's identity-map cache to return a stale
active user and yield a false 200.  Using `_db.session` directly resolves the cache
isolation issue.

### Open Issues / Risks
None.  The change is route-only, minimal, and the full test suite is green.

### Next Recommended Step
Proceed to Wave 3 Phase 4 (Draft Serialization Performance Cleanup, W3-004).
