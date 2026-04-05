# Testing Handoff — Wave 4 Phase 2: Session Invalidation and Password Policy Hardening

## Entry 1 — 2026-04-05

### Status

Complete. 114 passed, 0 failed. All F-SEC-004 and F-SEC-005 contracts locked.

### Scope

- `backend/tests/test_auth.py` — added `TestRefreshInvalidationAfterPasswordChange` (F-SEC-004)
- `backend/tests/test_settings.py` — fixed broken test + added `TestPasswordPolicyMinimumLength` (F-SEC-005)
- `backend/app/api/auth/routes.py` — bug fix: timezone-naive/aware comparison + iat integer-second precision fix (backend-owned, documented below)

### Docs Read

- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (F-SEC-004, F-SEC-005)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-SET-001, DEC-FE-006, DEC-BE-009)
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/backend.md`
- `backend/app/models/user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`

### Files Changed

| File | Change summary |
|---|---|
| `backend/tests/test_auth.py` | Added `TestRefreshInvalidationAfterPasswordChange` class (3 tests) |
| `backend/tests/test_settings.py` | Fixed `"pass1"` → `"pass12345"` in `test_create_user_duplicate_username_update_password_and_deactivate`; added `TestPasswordPolicyMinimumLength` class (7 tests) |
| `backend/app/api/auth/routes.py` | Two production-logic fixes required by test failures (see below) |

### Commands Run

```bash
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q --tb=short
```

### Tests

```
114 passed in 57.15s
```

### Backend Runtime Fix Required (documented here per handoff protocol)

While writing the refresh-invalidation tests, two bugs were discovered in the backend `routes.py` refresh handler and fixed as part of this testing phase:

**Bug 1 — offset-naive vs offset-aware datetime comparison (`TypeError`)**

SQLite returns naive datetimes for `DateTime(timezone=True)` columns; PostgreSQL returns aware datetimes. The original comparison `token_issued_at < user.password_changed_at` raised `TypeError` on SQLite. Fix: normalize `pca` to UTC-aware if `pca.tzinfo is None` before comparing.

**Bug 2 — sub-second precision mismatch**

JWT `iat` is a whole-second Unix integer. `password_changed_at` has microsecond precision. Comparing a whole-second aware datetime against a microsecond-precise timestamp can incorrectly reject tokens issued in the same second as a password change. Fix: compare `iat < int(pca.timestamp())` (integer comparison at second resolution) instead of comparing datetime objects. A token issued in the same second as the change is allowed; a token issued in an earlier second is rejected.

Both fixes are in `backend/app/api/auth/routes.py` within the `if user.password_changed_at is not None:` block.

### F-SEC-004: Refresh Invalidation Behaviors Locked

All three tests live in `TestRefreshInvalidationAfterPasswordChange` in `backend/tests/test_auth.py`.

**Test methodology note:** Both the "before" and "after" tests manipulate `password_changed_at` directly in the DB rather than relying on wall-clock timing. The test decodes the token's `iat` claim (without signature verification — test-only) and sets `password_changed_at = iat ± 1 second` to make the comparison deterministic regardless of test execution speed.

1. `test_refresh_token_issued_before_password_change_is_rejected`
   — sets `password_changed_at = token_iat + 1s` → refresh returns 401 `PASSWORD_CHANGED`

2. `test_refresh_token_issued_after_password_change_works`
   — sets `password_changed_at = token_iat - 1s` → refresh returns 200 with new access token

3. `test_null_password_changed_at_does_not_block_refresh`
   — user with `password_changed_at IS NULL` (no admin reset ever) → refresh returns 200 unchanged

### F-SEC-005: Password Policy Behaviors Locked

`TestPasswordPolicyMinimumLength` in `backend/tests/test_settings.py` (7 tests):

**create_user — below minimum rejected:**
- ADMIN < 12 chars → 400 VALIDATION_ERROR, message contains "12"
- OPERATOR < 8 chars → 400 VALIDATION_ERROR, message contains "8"
- MANAGER < 8 chars → 400 VALIDATION_ERROR

**create_user — at minimum accepted:**
- ADMIN exactly 12 chars → 201
- OPERATOR exactly 8 chars → 201

**update_user (password reset) — below minimum rejected:**
- VIEWER reset with 5-char password → 400 VALIDATION_ERROR, message contains "8"

**update_user (password reset) — at minimum accepted:**
- MANAGER reset with 9-char password → 200

**Broken test fixed:**
`test_create_user_duplicate_username_update_password_and_deactivate` — changed both occurrences of `"pass1"` to `"pass12345"` (8 chars, meets OPERATOR minimum). The `"pass-reset"` password (10 chars) for the MANAGER update was already sufficient.

### README Verification

`README.md` was updated in Phase 1 and does not reference a specific bootstrap password. No further README changes required for this phase.

### Residual Ambiguity / Out-of-Scope Items

- `stoqio_docs/` still describes the old `User` model and weaker password policy. Out of scope per orchestrator.
- `settings_service.py` only stamps `password_changed_at` on admin-driven password resets. A future self-service password-change endpoint would also need to stamp it and would need corresponding test coverage.
- The test infrastructure for F-SEC-004 uses direct DB manipulation rather than the Settings API to avoid wall-clock race conditions. An integration-style test that goes through the full Settings API flow and uses a brief sleep would be an acceptable alternative but is more fragile.

### Next Recommended Step

Orchestrator validation: verify 114/114 pass, review test names for contract clarity, accept or request minor additions.
