## Phase Summary

Phase
- Wave 4 - Phase 2 - Session Invalidation and Password Policy Hardening

Objective
- Ensure password changes fully terminate previously issued refresh-token sessions and raise the minimum password strength to a level appropriate for administrative accounts and semi-persistent refresh-token sessions.
- This phase covers:
- `F-SEC-004` — refresh-token invalidation after password change
- `F-SEC-005` — password minimum-length hardening

Source Docs
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-004`, `F-SEC-005`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-SET-001`, `DEC-FE-006`, `DEC-BE-009`)
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/models/user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`
- `backend/migrations/versions/`

Current Repo Reality
- Wave 4 Phase 1 is accepted and is the current baseline. This phase should build on that auth/config hardening rather than reopening it.
- `backend/app/models/user.py` currently includes:
- `id`
- `username`
- `password_hash`
- `role`
- `employee_id`
- `is_active`
- `created_at`
- There is no `password_changed_at` column yet.
- No Alembic migration exists yet for password-change timestamping.
- `backend/app/api/auth/routes.py` currently:
- issues refresh tokens via `create_refresh_token(...)`
- preserves the existing role-based refresh lifetime split
- rechecks that the user still exists and is active on `/refresh`
- does not yet reject refresh tokens issued before a later password change/reset
- The repo does not currently codify or test any password-change-vs-refresh-token issuance comparison. If Flask-JWT-Extended already emits a standard `iat`, Phase 2 still needs to make the repo contract explicit and consume it deliberately instead of relying on an unstated library default.
- `backend/app/services/settings_service.py` currently:
- creates users via `create_user(...)`
- performs admin-driven password reset/change through `update_user(..., payload["password"])`
- validates passwords with the old shared rule `len(password) >= 4` for every role
- updates `password_hash` without any session invalidation timestamp
- `backend/app/api/settings/routes.py` already locks the Settings user-edit payload shape:
- `POST /api/v1/settings/users`
- `PUT /api/v1/settings/users/{id}`
- per `DEC-SET-001`, password reset stays under the field name `password`
- Existing tests already cover:
- login / refresh / logout / revocation / inactive-user refresh rejection in `backend/tests/test_auth.py`
- Settings user create/update/deactivate flow in `backend/tests/test_settings.py`
- Existing settings tests already prove that an old password stops working after admin reset and the new password works, but they do not yet prove that an already-issued refresh token is invalidated by that password change.
- Frontend auth storage already persists the refresh token in `localStorage` (`DEC-FE-006`), so password-change-driven refresh invalidation is meaningful for real session termination rather than only for neat backend semantics.
- The locked docs still describe the older model and weaker password minimum in places. This phase is backend + testing only; broader docs alignment is not delegated here unless a blocker makes the runtime result misleading.

Contract Locks / Clarifications
- Do not change auth endpoint URLs, response shapes, token lifetimes, logout revocation behavior, or the persisted blocklist mechanism.
- This phase adds password-change invalidation on top of the existing refresh-token and revocation architecture; it does not replace them.
- Keep the Settings user-edit request contract unchanged:
- password reset field name remains `password` (`DEC-SET-001`)
- `username` remains immutable
- `password_changed_at` must be nullable so legacy rows are not broken by the schema change.
- Legacy/null `password_changed_at` rows must continue to refresh successfully unless another existing auth rule rejects them.
- Use UTC timestamp semantics consistently.
- Raise minimum password length only. Do not add new complexity rules, character-class rules, forced rotation, or forced first-login change behavior in this phase.
- No frontend work is in scope for this phase.
- No docs agent is in scope for this phase.

Delegation Plan
- Backend:
- add `password_changed_at`, migration, password-change stamping, refresh-token invalidation logic, and role-aware minimum password validation in Settings flows
- Testing:
- lock the new session invalidation and role-aware password-policy behavior with targeted auth/settings regression coverage

Acceptance Criteria
- `User` has a nullable `password_changed_at` timestamp column with a working migration from the current head revision.
- Every password change/reset flow in `settings_service.py` stamps `password_changed_at = utcnow()`.
- Refresh-token handling keeps the existing lifetime and revocation model but additionally rejects tokens issued before the user’s latest password change.
- The refresh rejection uses a clear 401 error code/message in the standard API error shape.
- Legacy rows with `password_changed_at IS NULL` are not accidentally rejected on refresh.
- Minimum password length is now:
- `ADMIN` → 12 characters
- all other roles → 8 characters
- The new minimum applies consistently in both user-creation and password-reset/change flows in `settings_service.py`.
- Validation errors are clear and deterministic.
- New/updated auth/settings tests pass and make the intended contract obvious to future reviewers.
- The phase leaves complete backend + testing + orchestrator handoff trail.

Validation Notes
- None yet.

Next Action
- Delegate to Backend first because the testing surface depends on the final schema field, refresh logic, and validation messages.

## Delegation Prompt - Backend Agent

You are the backend agent for Wave 4 Phase 2 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-004`, `F-SEC-005`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-SET-001`, `DEC-FE-006`, `DEC-BE-009`)
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`
- `handoff/wave-04/phase-01-wave-04-bootstrap-jwt-and-startup-hardening/orchestrator.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/models/user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`
- latest files under `backend/migrations/versions/`

Goal
- Ensure password changes terminate previously issued refresh-token sessions and enforce stronger role-aware minimum password length without changing route contracts or broader auth behavior.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend implementation/migration files plus `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/backend.md`.
- Do not edit frontend files or docs files in this phase.
- Prefer leaving backend test-file changes to the testing agent unless a tiny backend-owned regression test is absolutely required to make the implementation safe; if so, document why clearly in handoff.

Current Repo Reality You Must Respect
- `User` does not yet have `password_changed_at`.
- `settings_service.create_user(...)` and `settings_service.update_user(...)` still use the old `len(password) >= 4` rule regardless of role.
- `update_user(..., payload["password"])` is the active admin-driven password reset/change path and must keep using the field name `password` (`DEC-SET-001`).
- `/auth/refresh` currently rechecks user existence and activity but does not yet compare token issuance time against a password-change timestamp.
- Existing refresh-token lifetime behavior and revocation/blocklist behavior are already accepted and must remain intact.
- Frontend refresh-token persistence already exists (`DEC-FE-006`), so the session invalidation needs to work against the current architecture rather than requiring a frontend redesign.

Non-Negotiable Contract Rules
- Do not change auth endpoint URLs, response payload shapes, token lifetimes, logout semantics, or blocklist persistence behavior.
- Do not broaden into password complexity rules beyond minimum length.
- Do not introduce forced password change on first login.
- Do not change the Settings user payload shape or rename the `password` field.
- Keep `password_changed_at` nullable for compatibility.
- Legacy/null `password_changed_at` rows must continue to work unless another existing auth rule rejects them.
- Use UTC timestamp semantics.
- Keep the implementation narrow and security-focused.

Tasks
1. `F-SEC-004` — Refresh-token invalidation after password change:
- Add `password_changed_at` to the `User` model as a nullable UTC timestamp.
- Add a new Alembic migration from the current head revision for this column.
- Stamp `password_changed_at = utcnow()` every time `settings_service.py` changes/resets an existing user password.
- Include and/or deliberately consume an `iat` issued-at claim for refresh tokens.
- If Flask-JWT-Extended already provides `iat`, codify that contract in the repo logic rather than inventing an unnecessary parallel claim.
- Update `/api/v1/auth/refresh` so it rejects any refresh token whose issuance predates the user’s `password_changed_at`.
- Return a clear 401 error code/message in the standard error shape.
- Keep the existing refresh-token lifetimes and revocation/blocklist mechanism unchanged.
2. `F-SEC-005` — Password policy:
- Raise the minimum password length to:
- `ADMIN` → 12 characters
- all other roles → 8 characters
- Apply this validation consistently in:
- `create_user(...)`
- `update_user(...)` password reset/change path
- Return clear deterministic validation errors for policy failures.
- Do not add any other password complexity requirements in this phase.
3. Keep the implementation reader-friendly:
- make the role-aware password minimum logic easy to discover and reuse
- avoid duplicating inconsistent threshold constants/messages
4. Record clearly in handoff where:
- `password_changed_at` is added and stamped
- refresh-token invalidation is enforced
- password minimum validation is centralized/applied

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q`
- `git diff -- backend/app/models/user.py backend/app/api/auth/routes.py backend/app/services/settings_service.py backend/app/api/settings/routes.py backend/migrations/versions`
- If you add helper files or touch additional backend files, run the smallest targeted verification needed and record it.
- If feasible, run a safe disposable migration smoke (for example SQLite) and record it.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/backend.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests/verification run
- migration file created
- how refresh tokens are now invalidated after password change
- how legacy/null `password_changed_at` rows are handled
- how role-aware password minimums are enforced
- any residual docs drift or risk intentionally left out of scope
- If you discover a cross-agent contract clarification, add it to `handoff/decisions/decision-log.md` before finalizing.

Done Criteria
- Password changes terminate old refresh sessions.
- New refresh sessions after the password change still work normally.
- Role-aware minimum password length is enforced consistently.
- Migration and verification are recorded in handoff.

## Delegation Prompt - Testing Agent

You are the testing agent for Wave 4 Phase 2 of the STOQIO WMS project.

Read before coding:
- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (`F-SEC-004`, `F-SEC-005`)
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (`DEC-SET-001`, `DEC-FE-006`, `DEC-BE-009`)
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`
- backend handoff for this phase after backend finishes
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `backend/app/models/user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/api/settings/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`

Goal
- Lock the new session invalidation and role-aware password minimum behavior with regression tests that make the security contract obvious to future reviewers.

You are not alone in the codebase.
- Do not revert or overwrite unrelated edits.
- Your ownership is limited to backend test files plus `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/testing.md`.
- Do not broaden into runtime code changes or docs rewrites unless you hit a true blocker and document it clearly.

Non-Negotiable Contract Rules
- Keep behavior unchanged except for the intended hardening from this phase.
- Do not rewrite historical handoff files.
- Keep the accepted auth route shapes, lifetimes, and revocation semantics intact.
- The tests should make it obvious that password-change invalidation is layered on top of the existing refresh architecture rather than replacing it.

Minimum Required Coverage
1. `F-SEC-004` — session invalidation after password change:
- Change/reset a user password through the active Settings flow and assert that a refresh token issued before the change is rejected.
- Assert that a refresh token issued after the password change works normally.
- Assert that users with `password_changed_at IS NULL` are not accidentally rejected.
2. `F-SEC-005` — password minimums:
- `ADMIN` user creation fails below 12 characters.
- non-admin user creation fails below 8 characters.
- password change/reset fails below the applicable minimum.
- passwords meeting the minimum are accepted in both creation and reset/change flows.
3. Contract clarity:
- Prefer test names/assertions that explicitly mention role-aware minimums and refresh invalidation after password change.
- Reuse/extend the existing auth/settings test files when that keeps the contract easiest to discover.

Testing Guidance
- `backend/tests/test_auth.py` is the natural home for refresh invalidation coverage.
- `backend/tests/test_settings.py` is the natural home for create/reset password policy coverage.
- If the backend implementation adds a helper or a tiny additional behavior surface that is easier to test separately, a small new test file is acceptable, but avoid scattering the contract unnecessarily.
- Be careful with cached tokens/helpers in `test_settings.py`; make sure any token refresh invalidation assertions actually use the intended pre-change vs post-change token instances.

Verification
- Run at minimum:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q`
- Record exact results in handoff.
- If you rely on a migration/schema assumption for the tests, mention it clearly.

Handoff Requirements
- Append your work log to `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/testing.md`.
- Use the section shape required by `handoff/README.md`.
- Record:
- files changed
- commands run
- tests run
- which refresh invalidation behaviors were explicitly locked
- which role-aware password minimum behaviors were explicitly locked
- any residual ambiguity or docs drift left out of scope

Done Criteria
- The new password/session security behavior is obvious from the tests.
- Regression coverage locks the accepted contract.
- Verification is recorded in handoff.

## [2026-04-05 16:02 CEST] Orchestrator Review - Changes Requested

Status
- changes_requested

Scope
- Reviewed the delivered backend and testing handoffs for Wave 4 Phase 2.
- Compared the claimed contracts against the actual repo worktree and the runtime auth/settings flow.
- Re-ran the claimed automated verification and added a targeted end-to-end smoke covering the real password-reset path through the Settings API.

Docs Read
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/backend.md`
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/testing.md`
- `backend/app/models/user.py`
- `backend/migrations/versions/a2b3c4d5e6f7_add_password_changed_at_to_user.py`
- `backend/app/api/auth/routes.py`
- `backend/app/services/settings_service.py`
- `backend/tests/conftest.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`

Commands Run
```bash
git status --short
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q
cd backend && venv/bin/python -m pytest tests/test_auth.py -q -k 'RefreshInvalidationAfterPasswordChange'
cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'PasswordPolicyMinimumLength or test_create_user_duplicate_username_update_password_and_deactivate'
cd backend && venv/bin/python - <<'PY'
from tests.conftest import _TestConfig
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.enums import UserRole
from werkzeug.security import generate_password_hash

app = create_app(config_override=_TestConfig)

with app.app_context():
    db.create_all()
    admin = User(username='phase2_admin', password_hash=generate_password_hash('adminpass1234', method='pbkdf2:sha256'), role=UserRole.ADMIN, is_active=True)
    target = User(username='phase2_target', password_hash=generate_password_hash('viewerpass', method='pbkdf2:sha256'), role=UserRole.VIEWER, is_active=True)
    db.session.add_all([admin, target])
    db.session.commit()
    target_id = target.id

client = app.test_client()
admin_login = client.post('/api/v1/auth/login', json={'username': 'phase2_admin', 'password': 'adminpass1234'}, environ_base={'REMOTE_ADDR': '127.0.9.1'})
admin_token = admin_login.get_json()['access_token']
user_login = client.post('/api/v1/auth/login', json={'username': 'phase2_target', 'password': 'viewerpass'}, environ_base={'REMOTE_ADDR': '127.0.9.2'})
old_refresh = user_login.get_json()['refresh_token']
update = client.put(f'/api/v1/settings/users/{target_id}', json={'password': 'viewerpassNEW'}, headers={'Authorization': f'Bearer {admin_token}'})
old_refresh_resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {old_refresh}'})
new_login = client.post('/api/v1/auth/login', json={'username': 'phase2_target', 'password': 'viewerpassNEW'}, environ_base={'REMOTE_ADDR': '127.0.9.3'})
new_refresh = client.post('/api/v1/auth/refresh', headers={'Authorization': f"Bearer {new_login.get_json()['refresh_token']}"})
print('update_status', update.status_code)
print('old_refresh_status', old_refresh_resp.status_code)
print('old_refresh_payload', old_refresh_resp.get_json())
print('new_login_status', new_login.status_code)
print('new_refresh_status', new_refresh.status_code)
PY
```

Findings
- High: Phase 2 does not yet satisfy the main `F-SEC-004` contract in the real Settings password-reset flow. The refresh guard in `backend/app/api/auth/routes.py` only rejects when `iat < int(password_changed_at.timestamp())` (`backend/app/api/auth/routes.py:182`), so a refresh token issued earlier in the same second as the password reset is still accepted. I confirmed this through the real HTTP flow: login as the target user, reset that user's password through `PUT /api/v1/settings/users/{id}`, then call `/api/v1/auth/refresh` with the pre-change refresh token; the stale token still returned `200` and minted a new access token. That means “change password fully terminates previously issued sessions” is not actually true yet.
- Medium: The new auth tests do not lock the active Settings-flow contract the orchestrator delegated. `backend/tests/test_auth.py:851` proves only an artificial `password_changed_at = iat + 1 second` scenario, not the real same-second password-reset path. Because of that, the suite stays green while the real stale-session case still succeeds.
- Low: `backend/tests/test_settings.py:1256`, `backend/tests/test_settings.py:1266`, and `backend/tests/test_settings.py:1296` claim exact-minimum boundary coverage, but the accepted passwords used there are above the stated boundaries (`"Exactly12Chars"`, `"Exactly8!"`, `"Reset!789"`). The password-policy behavior is broadly covered, but the exact boundary claims in code/comments are looser than advertised.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q` → `114 passed in 56.43s`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q -k 'RefreshInvalidationAfterPasswordChange'` → `3 passed, 52 deselected in 1.13s`
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'PasswordPolicyMinimumLength or test_create_user_duplicate_username_update_password_and_deactivate'` → `8 passed, 51 deselected in 8.18s`
- The schema/migration pieces for `password_changed_at` exist in the repo and the settings-service password minimum logic is centralized and readable.
- Blocked:
- Real end-to-end refresh invalidation after password change is still bypassable when the refresh token issuance and password reset land in the same second. Manual smoke result:
- `update_status 200`
- `old_refresh_status 200`
- `new_login_status 200`
- `new_refresh_status 200`

Next Action
- Return to Backend for a narrow follow-up:
- make the refresh invalidation comparison fail closed for any token issued before the password reset, including the same-second case observed through the real Settings flow
- keep the existing lifetime and blocklist behavior unchanged while fixing that comparison
- Return to Testing for a narrow follow-up:
- add at least one test that goes through the active Settings password-reset flow and proves the pre-change refresh token is rejected
- tighten the “at minimum accepted” password-policy tests so they use true boundary-length passwords rather than above-minimum values
- Phase 2 is not accepted yet. Re-review after the backend/testing follow-up lands.

## [2026-04-05 16:10 CEST] Orchestrator Follow-Up - Fixes Implemented and Phase Accepted

Status
- accepted

Scope
- Implemented the narrow follow-up fixes directly as orchestrator so the previously documented review blockers are now closed.
- This follow-up work was done by the orchestrator, not by the earlier backend/testing deliveries, so future agents should treat the prior `backend.md` and `testing.md` entries as the pre-fix state for this phase.
- Updated refresh-token invalidation so it now fails closed for stale sessions even when the password reset and the old token issuance happen in the same second.
- Strengthened the auth regression coverage to go through the active Settings password-reset flow instead of only manipulating `password_changed_at` directly in the DB.
- Tightened the password-policy boundary tests so the “exactly at minimum” cases now use true 12-character and 8-character passwords.

Files Changed
- `backend/app/api/auth/routes.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_settings.py`
- `handoff/wave-04/phase-02-wave-04-session-invalidation-and-password-policy-hardening/orchestrator.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_auth.py -q -k 'RefreshInvalidationAfterPasswordChange'
cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'PasswordPolicyMinimumLength or test_create_user_duplicate_username_update_password_and_deactivate'
cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q
cd backend && venv/bin/python - <<'PY'
from tests.conftest import _TestConfig
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.enums import UserRole
from werkzeug.security import generate_password_hash

app = create_app(config_override=_TestConfig)

with app.app_context():
    db.create_all()
    admin = User(username='phase2_admin_fix', password_hash=generate_password_hash('adminpass1234', method='pbkdf2:sha256'), role=UserRole.ADMIN, is_active=True)
    target = User(username='phase2_target_fix', password_hash=generate_password_hash('viewerpass', method='pbkdf2:sha256'), role=UserRole.VIEWER, is_active=True)
    db.session.add_all([admin, target])
    db.session.commit()
    target_id = target.id

client = app.test_client()
admin_login = client.post('/api/v1/auth/login', json={'username': 'phase2_admin_fix', 'password': 'adminpass1234'}, environ_base={'REMOTE_ADDR': '127.0.9.11'})
admin_token = admin_login.get_json()['access_token']
user_login = client.post('/api/v1/auth/login', json={'username': 'phase2_target_fix', 'password': 'viewerpass'}, environ_base={'REMOTE_ADDR': '127.0.9.12'})
old_refresh = user_login.get_json()['refresh_token']
update = client.put(f'/api/v1/settings/users/{target_id}', json={'password': 'viewerpassNEW'}, headers={'Authorization': f'Bearer {admin_token}'})
old_refresh_resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {old_refresh}'})
new_login = client.post('/api/v1/auth/login', json={'username': 'phase2_target_fix', 'password': 'viewerpassNEW'}, environ_base={'REMOTE_ADDR': '127.0.9.13'})
new_refresh = client.post('/api/v1/auth/refresh', headers={'Authorization': f"Bearer {new_login.get_json()['refresh_token']}"})
print('update_status', update.status_code)
print('old_refresh_status', old_refresh_resp.status_code)
print('old_refresh_payload', old_refresh_resp.get_json())
print('new_login_status', new_login.status_code)
print('new_refresh_status', new_refresh.status_code)
PY
```

Findings
- None. The previous same-second refresh invalidation gap and the boundary-test mismatch are resolved.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_auth.py -q -k 'RefreshInvalidationAfterPasswordChange'` → `3 passed, 52 deselected in 1.67s`
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'PasswordPolicyMinimumLength or test_create_user_duplicate_username_update_password_and_deactivate'` → `8 passed, 51 deselected in 8.39s`
- `cd backend && venv/bin/python -m pytest tests/test_auth.py tests/test_settings.py -q` → `114 passed in 57.12s`
- Manual Settings-flow smoke now behaves correctly:
- `update_status 200`
- `old_refresh_status 401`
- `old_refresh_payload {'details': {}, 'error': 'PASSWORD_CHANGED', 'message': 'Credentials have changed. Please log in again.'}`
- `new_login_status 200`
- `new_refresh_status 200`

Next Action
- Wave 4 Phase 2 is complete.
- Future Wave 4 work should treat the accepted baseline as:
- refresh tokens still keep the standard JWT `iat`
- refresh tokens now also snapshot `password_changed_at` so same-second stale sessions are invalidated deterministically
- auth tests explicitly cover the active Settings password-reset flow
- password minimum boundary tests now use true exact-minimum values
