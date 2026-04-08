# Wave 6 Post-Hardening Code Review Findings

Date: 2026-04-08

Scope:
- Read-only multi-agent review of the STOQIO repository after Wave 6 security/infrastructure hardening.
- No code changes were made during the review.
- This document is intended for a follow-up agent to read and challenge/confirm before remediation planning.

Review orchestration:
- Backend auth/security/IDOR review agent
- Backend domain/data-integrity review agent
- Frontend auth/routing/API-client review agent
- Frontend product/domain pages review agent
- Infrastructure/config/docs/dependency review agent
- Orchestrator spot-check of high-risk Wave 6 touchpoints

Status at review time:
- `git status --short` was clean before and after the read-only review.
- Tests/builds were not run as part of this review because the user requested feedback only.

## High Severity

### H-1: Approval quantities can be changed after approval/rejection via direct API

Files:
- `backend/app/api/approvals/routes.py`
- `backend/app/services/approval_service.py`

Evidence:
- `backend/app/api/approvals/routes.py:41` exposes `PATCH /approvals/<group_id>/lines/<line_id>`.
- `backend/app/services/approval_service.py:154` loads `ApprovalOverride` rows and applies them in detail serialization.
- `backend/app/services/approval_service.py:268` updates/creates an override without verifying that the group/bucket is still pending or that the underlying drafts are still `DRAFT`.

Impact:
- Resolved approval history can be mutated after stock and transaction side effects have already been recorded.
- The UI may hide edit controls for resolved rows, but the backend does not enforce the invariant.

Recommended direction:
- Add a backend status guard in `edit_aggregated_line`.
- Reject edits unless the relevant bucket contains pending `DRAFT` lines and the group is still actionable.
- Add regression tests for approved, rejected, partial/history rows.

### H-2: Approval double-spend hardening is incomplete for alternate draft IDs in the same bucket

File:
- `backend/app/services/approval_service.py`

Evidence:
- `backend/app/services/approval_service.py:303` locks only the `line_id` draft row supplied by the request.
- `backend/app/services/approval_service.py:310` then loads all `DRAFT` bucket rows without locking the bucket set.

Impact:
- The UI normally sends the representative bucket line id, but the API accepts any draft id in the bucket.
- Two concurrent requests using different draft ids from the same bucket can avoid contending on the same representative row and may double-process stock/transactions.

Recommended direction:
- Lock all pending drafts in the bucket, or canonicalize and lock a single deterministic representative row before processing.
- Add a regression test that attempts two approvals against different draft ids in the same bucket.

### H-3: Inventory count start/complete is race-prone

File:
- `backend/app/services/inventory_service.py`

Evidence:
- `backend/app/services/inventory_service.py:166` starts a count after a plain SELECT for existing `IN_PROGRESS` counts.
- `backend/app/services/inventory_service.py:513` completes a count without locking the count row or performing an atomic status transition.
- `backend/app/services/inventory_service.py:575` creates surplus/shortage side effects during completion.

Impact:
- Concurrent count starts can create multiple active inventory counts.
- Concurrent completion can duplicate surplus rows, shortage drafts, and/or transactions, or surface raw integrity errors.

Recommended direction:
- Add a DB-level guard for single active count where supported, or implement an atomic transition/lock pattern.
- Lock the count row during completion.
- Make side effects idempotent, especially shortage draft creation by `client_event_id`.

### H-4: Employee issuance can overspend stock under concurrent requests

File:
- `backend/app/services/employee_service.py`

Evidence:
- `backend/app/services/employee_service.py:110` reads the issuance stock row without `FOR UPDATE`.
- Availability is checked before persistence around `backend/app/services/employee_service.py:787`.
- The stock row is fetched again and decremented later around `backend/app/services/employee_service.py:853` and `backend/app/services/employee_service.py:883`.

Impact:
- Two simultaneous issuances can both pass availability checks against the same stock quantity.
- This can produce negative-stock integrity failures or inconsistent user-facing errors.

Recommended direction:
- Lock the stock row for the issuance transaction or use an atomic conditional update.
- Map race failures to the same business error as insufficient stock.

### H-5: Editing a warehouse article overwrites `density` with `1`

Files:
- `frontend/src/pages/warehouse/warehouseUtils.ts`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Evidence:
- `frontend/src/pages/warehouse/warehouseUtils.ts:89` initializes form `density` to `1` instead of `article.density`.
- `frontend/src/pages/warehouse/warehouseUtils.ts:578` hard-codes outgoing payload `density: 1`.
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx:349` sends that payload on article update.

Impact:
- Editing unrelated fields on an existing warehouse article can silently corrupt non-`1` density values.

Recommended direction:
- Preserve `article.density` in form state.
- Send the parsed form density, or omit density from update payload if it is intentionally not editable.
- Add a regression test for updating another field while preserving density.

## Medium Severity

### M-1: Stock/surplus bucket uniqueness is incomplete for nullable `batch_id`

Files:
- `backend/app/models/stock.py`
- `backend/app/models/surplus.py`
- `backend/app/services/receiving_service.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/employee_service.py`

Evidence:
- `backend/app/models/stock.py:10` defines uniqueness over `(location_id, article_id, batch_id)`.
- `backend/app/models/stock.py:25` makes `batch_id` nullable, and common databases allow multiple NULLs in a unique constraint.
- `backend/app/models/surplus.py:8` has no equivalent uniqueness at all.
- Mutation paths use `.first()` for buckets, e.g. `backend/app/services/receiving_service.py:462`, `backend/app/services/approval_service.py:331`, and `backend/app/services/employee_service.py:119`.

Impact:
- Duplicate no-batch stock/surplus buckets can exist.
- Mutations may update only one row while reports/counts aggregate differently.

Recommended direction:
- Add partial unique indexes or a non-null batch-key strategy.
- Include a cleanup/migration plan for existing duplicate buckets.

### M-2: Batch lookup can create duplicate article batch codes under race

Files:
- `backend/app/models/batch.py`
- `backend/app/services/receiving_service.py`

Evidence:
- `backend/app/models/batch.py:8` has no unique constraint for `(article_id, batch_code)`.
- `backend/app/services/receiving_service.py:233` does application-level lookup before creating a batch.

Impact:
- Concurrent receiving can create duplicate batch rows for the same article/code.
- Later `.first()` selection becomes nondeterministic, especially when expiry dates differ.

Recommended direction:
- Add a DB unique constraint/index for `(article_id, batch_code)`.
- Handle insert races by catching integrity errors and re-reading the winning row.

### M-3: Employee issuance accepts arbitrary client UOM

File:
- `backend/app/services/employee_service.py`

Evidence:
- `backend/app/services/employee_service.py:668` accepts `data["uom"]` in the dry-run check path.
- `backend/app/services/employee_service.py:770` accepts `data["uom"]` in the create path.
- The service deducts base-unit stock but writes issuance and transaction rows with the supplied UOM.

Impact:
- A caller can record a misleading unit while consuming base-unit stock.

Recommended direction:
- Reject UOM mismatches or ignore client UOM and always use the article master base UOM.
- Add tests for mismatched UOM on check and create issuance.

### M-4: Reports pagination/export contract is incomplete

Files:
- `backend/app/services/report_service.py`
- `frontend/src/api/reports.ts`

Evidence:
- `backend/app/services/report_service.py:491` slices stock overview items by `page/per_page`.
- `backend/app/services/report_service.py:528` slices surplus rows by `page/per_page`.
- `frontend/src/api/reports.ts:152` `StockOverviewQuery` has no `page` or `perPage`, unlike transaction log queries.
- `backend/app/services/report_service.py:1064` exports stock overview by calling `get_stock_overview(...)` without overriding default pagination.
- `backend/app/services/report_service.py:1131` exports surplus by calling `get_surplus_report()` with defaults.

Impact:
- Large report tables may show/export only the first page while the UI presents totals.
- Export endpoints may no longer export the full report despite older docs/spec implying full export.

Recommended direction:
- Decide whether stock/surplus report pages should be paginated in UI.
- If exports should be full exports, add an explicit unpaginated service path or streaming/export-specific query.
- Update API types and tests to lock the chosen behavior.

### M-5: Refreshed tokens do not refresh frontend user/role state

Files:
- `backend/app/api/auth/routes.py`
- `frontend/src/api/client.ts`
- `frontend/src/store/authStore.ts`
- `frontend/src/components/layout/ProtectedRoute.tsx`

Evidence:
- Backend refresh re-reads the DB user and mints an access token with current role claims around `backend/app/api/auth/routes.py:243`.
- `backend/app/api/auth/routes.py:251` returns only `{ "access_token": ... }`.
- `frontend/src/api/client.ts:91` stores only the new access token.
- `frontend/src/store/authStore.ts:105` `setAccessToken` leaves `user` unchanged.
- `frontend/src/components/layout/ProtectedRoute.tsx:17` gates routes using stale `user.role`.

Impact:
- A demoted user can keep seeing admin-only routes/UI until logout or reload.
- An upgraded user can remain blocked from new routes until logout or reload.
- Backend endpoint authorization still protects APIs, but the frontend state is inconsistent.

Recommended direction:
- Return user data from `/auth/refresh` and update auth store, or call `/auth/me` with the new access token before retrying requests.
- Add an interceptor/auth-store test covering role changes across refresh.

### M-6: Settings self role edit leaves frontend auth state stale

Files:
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/components/layout/ProtectedRoute.tsx`

Evidence:
- `frontend/src/pages/settings/SettingsPage.tsx:1367` updates a user row and then only updates the local users table.
- `frontend/src/pages/settings/SettingsPage.tsx:2498` allows role edits in the user modal.
- `frontend/src/components/layout/ProtectedRoute.tsx:17` gates routes from `authStore.user.role`.

Impact:
- Editing the current user role leaves sidebar/route access inconsistent until refresh/relogin.

Recommended direction:
- Detect self role changes and force re-auth/navigation, or update the auth store consistently.
- Coordinate with the refresh-token role-state fix above.

### M-7: Deploy hardening still has no real rollback path

File:
- `scripts/deploy.sh`

Evidence:
- `scripts/deploy.sh:5` traps failures only to print the failed command.
- `scripts/deploy.sh:31` performs `git pull --ff-only`.
- Later steps install dependencies, build assets, run migrations, and restart the service without a restore path.

Impact:
- A failed deploy can leave repo/static/dependency/schema/service state partially advanced.
- This means the Wave 6 V-10 rollback finding is not materially remediated.

Recommended direction:
- Capture the pre-deploy revision and static artifact state before pulling/building.
- On failure, restore what can safely be restored and clearly report non-reversible migration state.
- Keep the shell simple, but make the rollback behavior real.

### M-8: `seed.py` still creates bootstrap admin with pbkdf2

File:
- `backend/seed.py`

Evidence:
- `backend/seed.py:73` uses `generate_password_hash(password, method="pbkdf2:sha256")`.
- This conflicts with DEC-SEC-002, which says new passwords and password resets use scrypt and future agents must not reintroduce pbkdf2 in password hashing calls.

Impact:
- A newly seeded admin starts with a legacy hash and relies on lazy migration after first login.

Recommended direction:
- Change seed admin hashing to `method="scrypt"`.
- Add/update seed hardening tests to assert the hash policy.

### M-9: Report default dates use UTC, not local operational date

File:
- `frontend/src/pages/reports/reportsUtils.ts`

Evidence:
- `frontend/src/pages/reports/reportsUtils.ts:7` uses `new Date().toISOString().slice(0, 10)`.
- `frontend/src/pages/reports/reportsUtils.ts:13` does the same after `setDate(1)`.

Impact:
- Around local midnight in Europe/Berlin or other non-UTC zones, the UI can default to the previous UTC date/month boundary.
- This affects initial report filters and the initial stock overview request.

Recommended direction:
- Format local dates using local date parts rather than UTC ISO strings, or use the configured operational timezone consistently.

## Low Severity / Process Drift

### L-1: Report pagination malformed integers can return 500

File:
- `backend/app/api/reports/routes.py`

Evidence:
- `backend/app/api/reports/routes.py:22` calls `int()` directly for stock overview `page`.
- `backend/app/api/reports/routes.py:71` calls `int()` directly for surplus `page`.
- `ValueError` is not converted to the standard 400 shape.

Recommended direction:
- Use shared query parser helpers, matching other API modules.

### L-2: Warehouse article create does not refresh the list

File:
- `frontend/src/pages/warehouse/WarehousePage.tsx`

Evidence:
- `frontend/src/pages/warehouse/WarehousePage.tsx:280` creates an article, closes the modal, then `navigate('/warehouse')`.

Impact:
- If the user is already on `/warehouse`, the list can remain stale until reload/filter/page change.

Recommended direction:
- Refresh the list after successful create or insert the returned row into current state when it belongs to the active filter/page.

### L-3: Stale pbkdf2 wording remains after scrypt migration

Files:
- `backend/app/utils/auth.py`
- `backend/tests/test_auth.py`

Evidence:
- `backend/app/utils/auth.py` comments still describe the dummy hash as pbkdf2-aligned even though the code uses scrypt.
- `backend/tests/test_auth.py` has a test name/doc wording referring to pbkdf2 while asserting a scrypt hash.

Recommended direction:
- Update comments/test names so the security contract is not misleading.

### L-4: Wave 6 frontend handoff is stale about `eslint-plugin-security`

Files:
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`
- `frontend/package.json`
- `frontend/eslint.config.js`

Evidence:
- Handoff says the security plugin is pending/manual/commented out.
- `frontend/package.json` includes `eslint-plugin-security`.
- `frontend/eslint.config.js` imports and applies `security.configs.recommended`.

Recommended direction:
- Update the handoff record to reflect the current repo reality.

### L-5: Wave 6 verification notes conflict

Files:
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/backend.md`
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md`

Evidence:
- The Phase 4 orchestrator claims full backend suite, frontend build, and tests passed.
- Backend/frontend handoffs say the agent did not have Bash execution permission and tests/build were not run.

Recommended direction:
- Reconcile the evidence trail so future agents do not trust an incorrect verification claim.

### L-6: README revoked-token cleanup docs are outdated

Files:
- `README.md`
- `backend/app/__init__.py`

Evidence:
- README says expired revoked-token cleanup is never run automatically on requests/startup/logout.
- Runtime registers a `before_request` cleanup in `backend/app/__init__.py`.

Recommended direction:
- Update README to explain both the automatic hourly request-triggered cleanup and the manual CLI command.

### L-7: `requirements.lock` contains stale `python-barcode`

Files:
- `backend/requirements.lock`
- `backend/requirements.txt`
- `backend/app/services/barcode_service.py`

Evidence:
- `backend/requirements.lock` pins `python-barcode==0.16.1`.
- `backend/requirements.txt` does not declare it.
- Current barcode generation uses ReportLab (`reportlab.graphics.barcode`), not `python-barcode`.

Impact:
- Deploy dependency surface is larger than the source dependency list implies.

Recommended direction:
- Regenerate `requirements.lock` from `requirements.txt` in the approved dependency workflow and verify no runtime import depends on `python-barcode`.

## Suggested Follow-Up Order

1. Confirm and fix the three backend transactional/data-integrity risks first:
   approval bucket locking, inventory count start/complete locking, employee issuance stock locking.
2. Add DB uniqueness/migration work for stock/surplus/batch buckets.
3. Fix frontend data corruption in warehouse density.
4. Resolve auth role-state refresh/self-edit behavior.
5. Decide report pagination/export contract and update tests/docs.
6. Close Wave 6 infra/process drift: deploy rollback, seed scrypt, stale handoffs, stale README, stale lock file.

## Questions for Second-Opinion Agent

- Are any high-severity race findings already mitigated by production DB isolation or deployment topology, or do they require code/DB constraints regardless?
- Should report exports intentionally export only the current/default page after Wave 6 pagination, or should they export all matching records?
- Should self role changes immediately log out the current user, or should the frontend refresh `/auth/me` and navigate based on the new role?
- What is the preferred DB strategy for nullable `batch_id` uniqueness: partial unique indexes or a materialized batch key column?
