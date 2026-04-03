## Phase Summary

Phase
- Wave 3 - Phase 3 - Settings Shell Auth Consistency

Objective
- Align `GET /api/v1/settings/shell` with the same authenticated-user semantics as the rest of the protected application.

Source Docs
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-003`)
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/18_UI_SETTINGS.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `backend/app/utils/auth.py`
- `backend/app/api/settings/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/api/settings.ts`

Current Repo Reality
- Before this phase, `GET /api/v1/settings/shell` validated JWT presence directly in `backend/app/api/settings/routes.py` via `verify_jwt_in_request()`.
- That blocked unauthenticated access, but it bypassed the shared auth helper path used by the rest of the protected API to also enforce:
- current user row still exists
- current user is active
- The shell endpoint must remain readable for all active authenticated roles because frontend bootstrap and AppShell depend on it.

Contract Locks / Clarifications
- `/api/v1/settings/shell` must remain available to all active authenticated roles:
- `ADMIN`
- `MANAGER`
- `WAREHOUSE_STAFF`
- `VIEWER`
- `OPERATOR`
- Missing or invalid JWT must still return `401`.
- Inactive or nonexistent users must now be rejected consistently with the rest of the protected API.
- The response payload must remain unchanged:
- `location_name`
- `default_language`
- `role_display_names`
- This phase does not require frontend changes unless a backend payload regression is discovered.

Delegation Plan
- Backend:
- replace the route-level JWT-only guard with the shared helper path while preserving all-role access and the existing payload contract
- Testing:
- extend backend coverage for all supported roles plus inactive/nonexistent-user rejection

Acceptance Criteria
- All active authenticated roles can still load shell settings.
- Missing JWT is rejected with `401`.
- Inactive users cannot access `/api/v1/settings/shell`.
- Tokens for deleted/nonexistent users cannot access `/api/v1/settings/shell`.
- The shell payload shape remains unchanged.
- The phase leaves complete backend, testing, and orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Review backend and testing agent deliveries, rerun targeted verification, and record closeout decision.

## [2026-04-03 14:34 CEST] Orchestrator Review - Phase Accepted

Status
- accepted

Scope
- Reviewed the delivered backend and testing work for Wave 3 Phase 3.
- Compared agent handoffs against the actual modified code.
- Re-ran the requested verification matrix for the touched backend scope.

Docs Read
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/backend.md`
- `handoff/wave-03/phase-03-wave-03-settings-shell-auth-consistency/testing.md`
- `backend/app/api/settings/routes.py`
- `backend/app/utils/auth.py`
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `frontend/src/store/settingsStore.ts`
- `frontend/src/api/settings.ts`

Commands Run
```bash
git status --short
git diff -- backend/app/api/settings/routes.py backend/tests/test_settings.py
rg -n "def get_shell_settings|@settings_bp.route\\(\"/settings/shell\"|require_role\\(" backend/app/api/settings/routes.py backend/app/services/settings_service.py backend/app/utils/auth.py
rg -n "test_shell_endpoint_accessible_to_(admin|manager|viewer|warehouse_staff|operator)|test_shell_endpoint_(anonymous_rejected|inactive_user_rejected|nonexistent_user_rejected)|role_display_names|default_language|location_name" backend/tests/test_settings.py frontend/src/store/settingsStore.ts frontend/src/api/settings.ts
cd backend && venv/bin/python -m pytest tests/test_settings.py -q
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q
```

Findings
- None.

Validation Result
- Passed:
- `backend/app/api/settings/routes.py` now protects `GET /api/v1/settings/shell` through `@require_role("ADMIN", "MANAGER", "WAREHOUSE_STAFF", "VIEWER", "OPERATOR")`, which reuses the shared auth path that also validates current-user existence and active status.
- `settings_service.get_shell_settings()` remained unchanged, so the shell payload contract stays stable.
- `backend/tests/test_settings.py` now covers successful shell access for all five supported active roles.
- `backend/tests/test_settings.py` now covers both inactive-user rejection and nonexistent-user rejection for `/api/v1/settings/shell`.
- `frontend/src/store/settingsStore.ts` and `frontend/src/api/settings.ts` still expect the same shell payload fields (`location_name`, `default_language`, `role_display_names`), so no frontend regression was introduced by this phase.
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q` -> `52 passed`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q` -> `92 passed`

Closeout Decision
- Wave 3 Phase 3 is accepted and closed.

Next Action
- Proceed to Wave 3 Phase 4 - Draft Serialization Performance Cleanup.
