# Backend Handoff — Wave 4 Phase 2: Session Invalidation and Password Policy Hardening

## Entry 1 — 2026-04-05

### Status

Complete. Both F-SEC-004 and F-SEC-005 implemented and verified. One pre-existing test in `test_settings.py` now correctly fails due to the new password-length enforcement; this is an intentional breakage that the testing agent must fix.

### Scope

- `backend/app/models/user.py` — add `password_changed_at` column (F-SEC-004)
- `backend/migrations/versions/a2b3c4d5e6f7_add_password_changed_at_to_user.py` — new migration from head `e1f2a3b4c5d6` (F-SEC-004)
- `backend/app/services/settings_service.py` — role-aware password minimum helpers + stamp `password_changed_at` on update (F-SEC-004, F-SEC-005)
- `backend/app/api/auth/routes.py` — refresh invalidation against `password_changed_at` using JWT `iat` claim (F-SEC-004)

### Docs Read

- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (F-SEC-004, F-SEC-005)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-SET-001, DEC-FE-006, DEC-BE-009)
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `backend/app/models/user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`
- `backend/migrations/versions/e1f2a3b4c5d6_add_revoked_token_expires_at_index.py` (head revision)

### Files Changed

| File | Change summary |
|---|---|
| `backend/app/models/user.py` | Added `password_changed_at = db.Column(db.DateTime(timezone=True), nullable=True)` |
| `backend/migrations/versions/a2b3c4d5e6f7_add_password_changed_at_to_user.py` | New migration from `e1f2a3b4c5d6`; adds nullable `password_changed_at` column to `user` table |
| `backend/app/services/settings_service.py` | Added `_min_password_length(role)` and `_validate_password_length(password, role)` helpers; replaced both hardcoded `len(password) < 4` checks; stamped `user.password_changed_at = datetime.now(timezone.utc)` in `update_user` password path |
| `backend/app/api/auth/routes.py` | Extended `datetime` import; added `password_changed_at` vs `iat` check in `/refresh` handler |

### Commands Run

```bash
# Migration smoke against disposable SQLite DB
cd backend
DATABASE_URL=sqlite:///smoke_test_w4p2.db FLASK_ENV=development venv/bin/alembic upgrade head
rm -f smoke_test_w4p2.db
# → All 11 revisions applied cleanly including new a2b3c4d5e6f7

# Test suite
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q --tb=short

# Git diff
git diff -- backend/app/models/user.py backend/app/api/auth/routes.py \
           backend/app/services/settings_service.py \
           backend/app/api/settings/routes.py backend/migrations/versions
```

### Tests

```
103 passed, 1 failed in 50.09s
```

**Passing:** All 49 `test_auth.py` tests plus 54 of 55 `test_settings.py` tests.

**Expected failure (testing agent must fix):**

`test_settings.py::test_create_user_duplicate_username_update_password_and_deactivate`

This test posts `"password": "pass1"` (5 chars) for an OPERATOR user. The new minimum is 8 for non-ADMIN roles, so `create_user` now correctly returns 400 instead of 201. The testing agent must update this test to use a password meeting the new minimum (e.g. `"pass12345"` for the OPERATOR, and verify `"pass-reset"` (10 chars) is sufficient for the MANAGER update). The test is otherwise correct in structure and should require only a password-string change.

### Where `password_changed_at` Is Added and Stamped

- **Model**: `backend/app/models/user.py:32` — nullable `DateTime(timezone=True)` column.
- **Migration**: `backend/migrations/versions/a2b3c4d5e6f7_...py` — `op.add_column("user", sa.Column("password_changed_at", ...))`.
- **Stamped at**: `backend/app/services/settings_service.py` in `update_user()`, immediately after `user.password_hash` is updated (line ~1173). Only set on the `"password"` branch of `update_user`, not on `create_user` (new users have no prior sessions to invalidate).

### How Refresh Invalidation Works

Location: `backend/app/api/auth/routes.py`, `/refresh` handler, lines ~175-190.

1. After confirming user exists and is active (existing check), if `user.password_changed_at is not None`:
2. Read `iat` from `get_jwt()` — Flask-JWT-Extended includes this standard Unix-timestamp claim in every token.
3. Convert `iat` to timezone-aware UTC: `datetime.fromtimestamp(iat, tz=timezone.utc)`.
4. If `token_issued_at < user.password_changed_at`, return `401 PASSWORD_CHANGED "Credentials have changed. Please log in again."`.

The existing revocation/blocklist check (handled by `@jwt_required(refresh=True)` + the `token_in_blocklist_loader`) runs **before** the route handler, so it is unaffected. The new check is layered on top.

### Legacy / NULL `password_changed_at` Rows

The guard is conditional: `if user.password_changed_at is not None`. Rows with a NULL value (all existing rows after migration, and any user who has never had an admin password reset) skip the timestamp comparison entirely and continue to use the pre-existing auth rules only. No breakage of legacy sessions.

### How Role-Aware Password Minimums Are Enforced

Two private helpers added at `backend/app/services/settings_service.py`:

- `_min_password_length(role: UserRole) -> int` — returns `12` for `ADMIN`, `8` for all other roles.
- `_validate_password_length(password: Any, role: UserRole) -> None` — raises `SettingsServiceError("VALIDATION_ERROR", "password must be at least {N} characters long for role {R}.", 400)` when the check fails.

`_validate_password_length` is called in:
- `create_user(...)` — uses the `role` parsed from the creation payload.
- `update_user(...)` — uses `user.role` at the time of the password check. Because the `"role"` update block runs before the `"password"` block, if both are in a single payload the new role is already reflected when the minimum is checked.

Error messages include both the required length and the role value so validation failures are self-explanatory.

### Residual Docs Drift / Out-of-Scope Items

- `stoqio_docs/05_DATA_MODEL.md` still describes the old `User` model without `password_changed_at`. Docs update is out of scope for this phase per the orchestrator.
- `stoqio_docs/03_RBAC.md` does not yet mention the stronger password minimums per role. Also out of scope.
- `settings_service.py` `update_user` stamps `password_changed_at` only on admin-driven changes through the Settings flow. A future self-service password-change endpoint (not in this codebase yet) would also need to stamp the field.
- The testing agent should also add positive-path tests confirming that refresh tokens issued *after* a password change work correctly, and that NULL `password_changed_at` does not block refresh.

### Next Recommended Step

Delegate to Testing agent. Key contracts to lock:
1. A refresh token issued before `update_user(password=...)` is called → 401 `PASSWORD_CHANGED`.
2. A refresh token issued after the password change → 200 (normal operation).
3. A user with `password_changed_at IS NULL` → refresh passes unchanged.
4. ADMIN user creation with < 12 chars → 400.
5. Non-admin user creation with < 8 chars → 400.
6. Password reset for an admin/non-admin below the applicable minimum → 400.
7. Fix `test_create_user_duplicate_username_update_password_and_deactivate` to use passwords meeting the new minimums.
