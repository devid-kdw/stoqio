# Backend Agent — Phase 07 Wave 2: Installation-Wide Shell Branding

## Entry: 2026-04-02

---

### Status

Done. All tests pass.

---

### Scope

Add a minimal read-only `GET /api/v1/settings/shell` endpoint accessible to all authenticated roles (ADMIN, MANAGER, WAREHOUSE_STAFF, VIEWER, OPERATOR). Expose only the three shell-branding fields consumed by AppShell/Sidebar: `location_name`, `default_language`, and `role_display_names`. Keep all mutable Settings endpoints and the existing admin-only `GET /api/v1/settings/general` and `GET /api/v1/settings/roles` unchanged.

---

### Docs Read

- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (F-037)
- `stoqio_docs/18_UI_SETTINGS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (first 200 lines)
- `handoff/phase-14-settings/orchestrator.md` (not yet present — skipped)
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `frontend/src/store/settingsStore.ts` (referenced for shell consumer list)
- `frontend/src/components/layout/AppShell.tsx` (referenced for shell consumer list)
- `frontend/src/components/layout/Sidebar.tsx` (referenced for shell consumer list)
- `backend/app/utils/auth.py` (to confirm `require_role` / `verify_jwt_in_request` patterns)

---

### Files Changed

| File | Change |
|---|---|
| `backend/app/services/settings_service.py` | Added `get_shell_settings()` — reuses `_settings_location_or_404()`, `_system_config_value()`, `_role_display_name_map()`, `_serialize_role_row()`, and `_ROLE_ORDER` from the existing service. Returns `{location_name, default_language, role_display_names}`. |
| `backend/app/api/settings/routes.py` | Added `GET /api/v1/settings/shell` route guarded by `verify_jwt_in_request()` (any valid JWT). Added `flask_jwt_extended.verify_jwt_in_request` import. No existing routes modified. |
| `backend/tests/test_settings.py` | Appended 6 targeted tests: admin access, manager access, viewer access, anonymous 401, no-admin-field-leak assertion, and role display name value check. |

---

### Commands Run

```
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
```

Result: **21 passed** (15 pre-existing + 6 new).

---

### Tests

| Test | Assertion |
|---|---|
| `test_shell_endpoint_accessible_to_admin` | 200, correct payload shape and values |
| `test_shell_endpoint_accessible_to_manager` | 200, all three shell keys present |
| `test_shell_endpoint_accessible_to_viewer` | 200, all three shell keys present |
| `test_shell_endpoint_anonymous_rejected` | 401 for unauthenticated request |
| `test_shell_endpoint_does_not_expose_admin_only_fields` | `timezone`, `barcode_format`, `barcode_printer`, `export_format` absent |
| `test_shell_role_display_names_match_defaults` | All five default display names correct |

---

### Open Issues / Risks

- Frontend agent must update `settingsStore.ts` to call `/api/v1/settings/shell` instead of the admin-only endpoints, and `AppShell.tsx` must remove the `user?.role === 'ADMIN'` guard around `loadShellSettings()`.
- WAREHOUSE_STAFF and OPERATOR roles are not seeded in the settings test fixture; the existing `settings_target` user has role VIEWER. Tests for those roles would require new fixture users. Current tests cover ADMIN + MANAGER + VIEWER which is sufficient to verify cross-role access.

---

### Next Recommended Step

Frontend agent: update `settingsStore.ts` and `AppShell.tsx` to consume `GET /api/v1/settings/shell` for all authenticated sessions.
