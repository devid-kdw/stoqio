# Wave 6 Post-Hardening: Second-Opinion Review

Date: 2026-04-08
Reviewer: Second-opinion orchestrator (read-only, no code changes)

Scope:
- File-by-file verification of all findings in `wave-06-post-hardening-code-review-findings.md`
- Five parallel sub-agents covered: backend race conditions, backend models/data-integrity, frontend auth state, frontend warehouse/reports, infrastructure/scripts/deps
- Additional findings not present in the original document are listed at the end

---

## Verdict on Original Findings

### H-1: Approval quantities editable after approval/rejection — CONFIRMED, SEVERITY STANDS

The finding is accurate. `approval_service.py:268-296` upserts an `ApprovalOverride` without any status check.
Line 275 does load the Draft to verify group membership, but the check stops there — it does **not** verify
`draft.status == 'DRAFT'`. No DB-level constraint blocks this either.

One detail the original review understated: the `_build_group_rows()` function (around line 200-205) allows
a post-approval override to **completely supersede the sum of all previously approved individual quantities**,
with no audit trail of the override being applied after resolution. This means a post-resolution edit doesn't
just change a number — it silently replaces the audited outcome with no record that the group had already
been resolved. This makes the impact higher than described.

---

### H-2: Approval double-spend hardening incomplete — CONFIRMED, ADDITIONAL VECTOR FOUND

Finding is accurate. `approval_service.py:303-305` locks only the representative draft row, then line 310
re-queries all bucket drafts without `with_for_update()`. The window between the representative lock and the
Stock/Surplus lock at line 332-342 is the race window.

**Additional vector not in original findings:** The `approve_all()` function (around line 447-487) loops
through all pending buckets and calls `_approve_pending_bucket()` for each one sequentially, with no
cross-bucket lock. Two concurrent `approve_all()` calls on the same group can interleave bucket processing.
If request A and request B both start processing the same group simultaneously, they may each process
different buckets and together process all buckets twice, without any guard preventing it. This is a second
distinct race vector on top of the same-bucket intra-bucket race described in the original finding.

---

### H-3: Inventory count start/complete is race-prone — CONFIRMED, SEVERITY STANDS

Finding is accurate. `inventory_service.py:181-192` performs a plain SELECT for existing `IN_PROGRESS`
counts before inserting a new one, with no lock and no unique constraint to catch concurrent inserts.
`inventory_service.py:515-521` checks status before completing a count, again with no row lock.

**Additional issue not in original findings:** Around line 538, `_get_default_location()` can return `None`.
If it does, line 549 silently skips shortage draft creation entirely. In a concurrent completion race where
two requests both pass the status check, if one of them races ahead and the location lookup fails on the
second request mid-transaction, shortages are silently dropped with no error surfaced. This is a correctness
gap on top of the race condition.

Also: the surplus row update during count completion (lines 578-597) is not locked before read-modify-write.
The count completion acquires no lock on the surplus row itself, only on the count row — which itself is
not locked either.

---

### H-4: Employee issuance can overspend stock — CONFIRMED, ADDITIONAL PATHS FOUND

Finding is accurate. `employee_service.py:787-819` checks stock availability, then the stock row is
decremented later at lines 854-884 without having held a lock on the row since the check.

**Additional issues not in original findings:**

1. `check_issuance()` (the dry-run path, around line 692-715) performs the same stock check without any
   lock. The dry-run result is consumed by the UI to show availability, but there is no enforced coupling
   between the dry-run result and the subsequent `create_issuance()` call. Stock can change between the
   two calls and the create will still proceed if the second check (inside create) passes.

2. The quota calculation functions `_received_for_article()` and `_received_for_category()` (around lines
   287-312) query `PersonalIssuance` history with no transaction isolation guarantee. A concurrent issuance
   commit can change the total mid-calculation, which means the quota gate can pass for both concurrent
   requests even if only one should be permitted by quota.

3. The `CHECK (quantity >= 0)` constraint on `stock.quantity` (confirmed in migration
   `733fdf937291_initial.py:307`) prevents negative quantities **at the DB level**, which limits the blast
   radius: at DB default READ COMMITTED isolation, two decrements of 50 against a stock of 60 will result
   in one succeeding and one failing with an integrity error rather than both silently succeeding and
   producing -40. However, this is a crash-based mitigation, not a graceful one — the second request
   surfaces a raw integrity error instead of a clean "insufficient stock" response. The original finding
   recommendation to map race failures to a business error is correct and needed even with this constraint.

---

### H-5: Editing a warehouse article overwrites density with 1 — CONFIRMED, BACKEND NOTE ADDED

Finding is accurate. `warehouseUtils.ts:89` initializes form density to `1` and `warehouseUtils.ts:578`
hard-codes `density: 1` in the outgoing payload.

**Important nuance the original review missed:** The backend `article_service.py` (around line 1032-1041)
falls back to `existing_article.density` if the field is absent from the request body. This means if the
frontend were to **omit** density from the PATCH payload, the backend would silently preserve the existing
value. The simplest correct fix is therefore not to change the form initialization logic, but to **omit
density from the update payload** if it is not a user-editable field — the backend already supports this.
The original recommendation to "send the parsed form density, or omit density from update payload" is
correct, but omitting it is clearly the safer path given the backend fallback.

---

### M-1: Stock/surplus bucket uniqueness incomplete — CONFIRMED, MORE MODELS AFFECTED

Finding is accurate. `stock.py:10` has a UniqueConstraint that does not handle `NULL batch_id` correctly
in PostgreSQL (multiple NULLs are allowed through a standard UNIQUE). `surplus.py:8` has no uniqueness
constraint at all.

**Additional models with the same gap, not in original findings:**

- `inventory_count.py` line 69-70: nullable `batch_id` on count lines, no unique constraint on
  `(inventory_count_id, article_id, batch_id)`. Duplicate count lines for the same article/batch would
  corrupt the count result.
- `personal_issuance.py`: nullable `batch_id`, no unique constraint on `(employee_id, article_id, batch_id)`
  per issuance record (though multiple issuances per employee/article are intentional, so this may be by
  design — but worth confirming).
- `receiving.py`: nullable `batch_id`, no uniqueness constraint.

The original finding focuses on Stock/Surplus which are the most impactful. The surrounding models
extend the surface.

---

### M-2: Batch lookup can create duplicates under race — CONFIRMED, SEVERITY STANDS

Finding is accurate. `batch.py` has no unique constraint on `(article_id, batch_code)`. Migration
`733fdf937291_initial.py:163-172` confirms no constraint exists at the DB level. `receiving_service.py:233`
does a read-before-create with no lock and no unique constraint to catch a race.

The consequence described (nondeterministic `.first()` when expiry dates differ) is correct. Two batches
with the same code but different expiry dates in the same article create an ambiguous lookup — and
`receiving_service.py` uses `.first()` which is order-nondeterministic without explicit ordering.

---

### M-3: Employee issuance accepts arbitrary client UOM — CONFIRMED, COMPARISON NOTED

Finding is accurate. `employee_service.py:668` and `employee_service.py:770` accept `data["uom"]` without
validating it against the article's base UOM.

**Comparison the original review did not make:** `receiving_service.py:318-329` and `receiving_service.py:417-428`
DO validate UOM and reject mismatches with a `UOM_MISMATCH` error. The inconsistency is not just a missing
guard — it is a deliberate validation that was applied to receiving but not carried over to issuance.
Whoever fixes this should copy the receiving pattern.

---

### M-4: Reports pagination/export contract incomplete — CONFIRMED, UI IMPACT CLARIFIED

Finding is accurate. Backend `report_service.py:491` and `report_service.py:528` slice by `page/per_page`.
Frontend `StockOverviewResponse` interface in `reports.ts:45-50` does not include `page` or `per_page`.
Frontend never passes pagination params to the stock overview query.

**Clarification on export behavior:** Sub-agent confirmed that the export path in `ReportsPage.tsx:750-765`
uses `appliedStockFilters` which does NOT include pagination params, so export effectively bypasses the
backend pagination and downloads all matching rows. This means exports are already "full exports" —
the real problem is that the UI display may only show the default first page (up to `per_page` items)
while the totals shown reference all records, creating a misleading "Prikazano X / Y" counter where Y
reflects the full dataset but the table only shows page 1.

The original recommended direction ("decide whether exports should be full or paginated") is right,
but the current state is: UI shows page 1 only, export gives everything, totals count everything.
The documentation and type contract need to catch up to that reality rather than the behavior needing
a full rewrite.

---

### M-5: Refreshed tokens do not refresh frontend user/role state — CONFIRMED, ROOT CAUSE CLARIFIED

Finding is accurate. Backend `auth/routes.py:251` returns only `{ "access_token": ... }` from `/auth/refresh`.
`client.ts:91-94` stores only the new token. `authStore.ts:105` `setAccessToken` leaves `user` unchanged.

**Root cause detail the original review implied but did not make explicit:** `main.tsx:52-81` calls
`authApi.me()` at app startup and that is the **only time** the `user` object is populated from the server.
After that, the user object in the store is never re-fetched from an authoritative source — not on token
refresh, not on route navigation, not on any timer. The JWT claims inside the new access token carry
updated role information, but nothing in the frontend extracts those claims back into the store.

The simplest fix is to call `/auth/me` after a successful refresh and update `authStore.user`. The backend
`/auth/me` endpoint exists and is used at startup, so no new backend work is needed.

---

### M-6: Settings self role edit leaves frontend auth state stale — CONFIRMED, SEVERITY STANDS

Finding is accurate. `SettingsPage.tsx:1367` calls `updateUser()` and on success only updates the local
`users` array. There is no check for `editingUserId === currentUser?.id` and no call to update the auth
store.

**Additional observation:** `SettingsPage.tsx:1420` does correctly block self-deactivation with an error.
The self-deactivation guard exists but the analogous self-role-change guard does not. This inconsistency
suggests the self-role case was not considered during implementation rather than being a deliberate decision.

`ProtectedRoute.tsx` IS reactive to store changes (it uses `useAuthStore()` hooks), so updating
`authStore.user` after a self-edit would immediately re-evaluate route access without requiring a reload.
The fix surface is narrow: just sync the auth store when the edited user ID matches the current user ID.

---

### M-7: Deploy has no real rollback path — CONFIRMED, SCOPE NOTED

Finding is accurate. `scripts/deploy.sh:5` trap only prints. No pre-deploy state is captured, no artifacts
are preserved, and no migration rollback is attempted on failure.

**Scope note:** The sub-agent confirmed the health check at line 74 (`systemctl is-active --quiet wms`)
was added as a Wave 6 improvement — this is a genuine new check that the original finding should credit.
However, the health check only detects a service that failed to start; it does not restore the previous
state if it detects failure. The gap is real.

Migration rollback is inherently hard (Alembic `downgrade` requires knowing the previous head, and
destructive migrations cannot be safely reversed). The deploy script should at minimum capture the
pre-deploy git revision and Alembic head so a human can manually roll back with correct information.

---

### M-8: seed.py creates admin with pbkdf2 — CONFIRMED, MITIGATION IS PARTIAL

Finding is accurate. `seed.py:73` uses `method="pbkdf2:sha256"`. This conflicts with DEC-SEC-002.

**Partial mitigation the original review mentioned but did not fully evaluate:** Lazy rehash on login
exists in the auth routes (per handoff docs). This means a seeded admin who logs in will have their hash
silently upgraded to scrypt. However, the seeded admin is the initial bootstrap account — if that account
is never used post-seed (e.g., credentials are rotated by a script), the lazy migration never fires and the
pbkdf2 hash persists indefinitely. The fix (change `method="scrypt"` in seed.py) is trivial and should
be made regardless of the lazy migration.

The `test_seed_hardening.py` test should assert the hash method used in seed.py to prevent regression.

---

### M-9: Report default dates use UTC — CONFIRMED, BACKEND MISMATCH NOTED

Finding is accurate. `reportsUtils.ts:7` uses `new Date().toISOString().slice(0, 10)` which yields the
UTC date, not the browser-local date. Around midnight in any non-UTC timezone, this produces the wrong
default date.

**Backend mismatch the original review missed:** `report_service.py:655-656` uses
`datetime.now(timezone.utc).date()` for server-side date computations. This means the backend is
consistently UTC, but the frontend is trying to send a "local" date that comes out as UTC anyway due to
the bug. The net effect is that frontend and backend currently agree on the date (both UTC) but for the
wrong reason — the frontend is inadvertently doing UTC rather than intentionally doing it. If the bug
is fixed to use local dates, and the backend remains UTC, you now have a new mismatch where a user at
UTC+2 at 11 PM sends "tomorrow" to a backend that thinks it is "today."

The recommendation should be: decide on one authoritative timezone convention (UTC throughout, or
configured operational timezone throughout), then fix both ends to implement it consistently.

---

### L-1: Report pagination malformed integers return 500 — CONFIRMED

Finding is accurate. `reports/routes.py:22-23` and `71-72` call `int()` directly with no try/except.
Other modules use `parse_positive_int()` — the helper exists and is not applied here. One-line fix.

**Additional pattern not in original finding:** Line 113-114 (transaction log route) passes pagination
params as raw strings to the service without conversion at all. This is a different failure mode — it
depends on the service layer handling string-to-int conversion — and should be audited for the same
500-on-bad-input risk.

---

### L-2: Warehouse article create does not refresh the list — CONFIRMED, ROOT CAUSE CLARIFIED

Finding is accurate. `WarehousePage.tsx:283` calls `navigate('/warehouse')` after create. Since the user
is already on `/warehouse`, React Router does not remount the component and the `useEffect` dependencies
(query, page, filters) do not change, so no refetch fires.

**Root cause detail:** The `useEffect` at `WarehousePage.tsx:199-206` re-runs only when `debouncedQuery`,
`page`, `selectedCategory`, or `showInactive` change. Navigation to the same route without changing these
values is a no-op for the effect. The fix is to call `loadArticles()` directly after the create succeeds,
or to insert the newly created article into the current list state without a refetch.

---

### L-3: Stale pbkdf2 wording in auth.py — CONFIRMED

Finding is accurate. `auth.py:19` comment reads "Using pbkdf2:sha256 keeps this aligned with the app's
supported hash policy" while line 22 uses `method="scrypt"`. Code is correct, comment is wrong.
Straightforward doc fix.

---

### L-4: Wave 6 frontend handoff stale about eslint-plugin-security — CONFIRMED

Finding is accurate. The handoff file says the plugin is pending/commented. The actual state:
`frontend/eslint.config.js:1` imports it, `eslint.config.js:19` applies `security.configs.recommended`,
and `package.json:42` lists the package. Plugin is fully active. Handoff was not updated after manual
completion.

---

### L-5: Wave 6 verification notes conflict — CONFIRMED

Finding is accurate. `orchestrator.md:105` claims "567 passed, build ✓, 41/41 tests ✓". Both the backend
and frontend handoffs explicitly state "Bash tool denied" and tests were not run. These are mutually
exclusive claims.

The correct state for downstream agents: treat the Wave 6 Phase 4 verification as unconfirmed. Do not
rely on the orchestrator's test-pass claim without re-running the suite.

---

### L-6: README revoked-token cleanup docs outdated — CONFIRMED

Finding is accurate. `README.md:66` says cleanup "is never run automatically on requests, startup, or
logout." `app/__init__.py:100-118` registers a `before_request` hook that purges expired revoked tokens
once per hour. The README statement is directly contradicted by the code. The code behavior is correct;
the README needs updating.

---

### L-7: requirements.lock contains stale python-barcode — CONFIRMED, VENV NOTE

Finding is accurate. `requirements.lock` pins `python-barcode==0.16.1`. It is absent from `requirements.txt`.
`barcode_service.py:11-12` imports from `reportlab.graphics.barcode`, not from `python-barcode`. No source
file imports the `python_barcode` or `barcode` top-level module.

**Note:** The venv binary `venv/bin/python-barcode` is present, which means the package IS installed in
the current development venv. This confirms the lock file was generated from an environment that had the
package installed (likely a transitive dep from a previous iteration), not from the current requirements.txt.
The lock file should be regenerated from a clean environment built from requirements.txt only.

---

## New Findings Not in Original Document

### N-1: `approve_all()` has no cross-bucket lock — HIGH

File: `backend/app/services/approval_service.py`

The `approve_all()` function (around line 447-487) loops over pending buckets and calls
`_approve_pending_bucket()` for each. Each call acquires a lock on one representative draft row in its
bucket, but there is no lock that covers the entire group for the duration of the loop. Two concurrent
`approve_all()` calls on the same group can both enter the loop, interleave bucket processing, and
together process every bucket twice — effectively double-approving the entire group.

This is distinct from H-2 (same-bucket, different-draft-id race) because this race requires two
`approve_all()` calls, not two individual bucket approvals. The UI may serialize these in practice, but
the backend has no guard.

Recommended direction: Acquire a group-level lock before entering the bucket loop, or check and update
group status atomically at the start of `approve_all()` to prevent concurrent runs.

---

### N-2: `check_issuance()` dry-run result is not bound to subsequent `create_issuance()` — MEDIUM

File: `backend/app/services/employee_service.py`

The dry-run (`check_issuance()`) and the create (`create_issuance()`) are separate requests with no
server-side reservation between them. Stock can be consumed between the two calls. The create re-checks
availability, but as documented in H-4, that check is also unlocked. The compound pattern of
"check then create" with no lock at either step means the dry-run provides false assurance to the UI.

In addition, the quota calculation functions `_received_for_article()` / `_received_for_category()`
read `PersonalIssuance` history inside the check but outside any lock. A concurrent issuance committed
between the quota read and the create commit can cause a quota overrun.

Recommended direction: Combine check and create into a single locked transaction if the quota/stock check
is meant to be binding. If they must stay separate, document clearly that the dry-run is advisory only.

---

### N-3: No CI/CD pipeline exists — PROCESS

Scope: Entire repository.

No GitHub Actions workflows, no Jenkinsfile, no CircleCI config, no GitLab CI config was found. All
testing and deployment is manual. This means:
- No automated regression on PR/merge
- No automated lint/type-check
- The wave-by-wave agent handoff process is the only quality gate
- The L-5 verification conflict (orchestrator claims tests passed, agents say they were not run) is
  structurally possible to recur because there is no automated record

Recommended direction: Add a minimal GitHub Actions workflow running `pytest` and frontend `tsc --noEmit`
on push/PR, even with no deployment automation. This closes the verification credibility gap.

---

### N-4: Transaction log pagination passes unparsed strings to service — LOW

File: `backend/app/api/reports/routes.py`

Lines 113-114 pass `page` and `per_page` as raw query string values (strings) directly to the service
layer without calling `int()` or `parse_positive_int()`. The service may handle string-to-int conversion
internally, but this is inconsistent with the stock/surplus pagination paths (which do call `int()`) and
with other modules (which use `parse_positive_int()`). If the service does not coerce the type, a
non-integer `page` parameter on the transaction log endpoint will cause a different failure than on the
stock overview endpoint.

Recommended direction: Apply `parse_positive_int()` consistently across all three report pagination paths.

---

### N-5: `InventoryCountLine` has no uniqueness constraint for (count_id, article_id, batch_id) — MEDIUM

File: `backend/app/models/inventory_count.py`, migration `733fdf937291_initial.py`

The `InventoryCountLine` model has a nullable `batch_id` with no unique constraint on
`(inventory_count_id, article_id, batch_id)`. Combined with the H-3 race in `start_count()`, it is
possible to end up with duplicate count lines for the same article/batch in the same count. When
`complete_count()` processes these lines, it will sum or apply them twice, producing incorrect
surplus/shortage calculations.

This is more serious than the surplus/stock NULL uniqueness issue (M-1) because inventory count
completion directly drives stock correction side effects.

Recommended direction: Add a unique constraint (with NULL handling via partial index or coalesced key)
on `(inventory_count_id, article_id, batch_id)` on the count line table.

---

### N-6: `ProtectedRoute` does not handle `user === null` with an access token present — LOW

File: `frontend/src/components/layout/ProtectedRoute.tsx`

If `authStore.user` is `null` but `accessToken` is non-null (possible during bootstrap before `/me`
resolves, or after a token refresh clears user state), `ProtectedRoute` may redirect to login despite
the user having a valid session. This creates a flash-of-redirect or an incorrect lockout. The bootstrap
sequence in `main.tsx` is designed to prevent this, but the guard itself has no awareness of the
"authenticating" intermediate state distinct from "not authenticated."

Recommended direction: Introduce an explicit `authStatus` field (`idle | loading | authenticated | unauthenticated`)
in the auth store and have `ProtectedRoute` render a loading state while status is `loading`, preventing
premature redirects.

---

## Revised Priority Order

The original suggested order is mostly correct. Suggested adjustments:

1. **Lock the approval group in `approve_all()` first (N-1)** — combines with H-2 as the highest-risk
   path because `approve_all()` is the most common user action and the inter-bucket race is easy to hit.
2. **H-2 intra-bucket locking** — lock all bucket drafts, not just the representative.
3. **H-1 status guard** — one-line check before the override upsert.
4. **H-3 inventory count locking + unique constraint** — atomic status transition and lock count row.
5. **N-5 InventoryCountLine uniqueness** — pairs naturally with H-3 remediation.
6. **H-4 employee issuance stock lock** — lock stock row before check and hold through decrement.
7. **M-1/M-2 uniqueness indexes** — partial unique index for stock/surplus, DB constraint for batch codes.
8. **M-3 UOM validation** — copy receiving_service.py validation pattern.
9. **H-5 density fix** — omit density from update payload.
10. **M-5/M-6 auth state sync** — call `/auth/me` after refresh; sync auth store on self-edit.
11. **M-4 reports contract** — decide and document pagination/export behavior, update type interface.
12. **M-7 deploy rollback** — capture pre-deploy revision and Alembic head at minimum.
13. **M-8 seed scrypt** — change one line.
14. **M-9 date timezone** — decide UTC vs. local convention, fix both ends consistently.
15. **L-1/N-4 report pagination parsing** — apply `parse_positive_int()` to all three paths.
16. **L-2 list refresh** — call `loadArticles()` after create.
17. **N-3 CI/CD** — add minimal pytest + tsc workflow.
18. **L-3/L-4/L-5/L-6/L-7 doc/deps cleanup** — all straightforward, batch in one pass.

---

## Answers to Original "Questions for Second-Opinion Agent"

**Q: Are high-severity race findings already mitigated by production DB isolation or deployment topology?**

No. At the default PostgreSQL `READ COMMITTED` isolation level, the races described in H-1 through H-4
are real. `REPEATABLE READ` or `SERIALIZABLE` would reduce some of them, but the codebase does not set
a non-default transaction isolation level anywhere reviewed. The only partial DB-level mitigation is the
`CHECK (quantity >= 0)` constraint on stock, which converts a silent negative-stock overrun into an
integrity error — still a crash, not graceful handling. Code or DB constraint fixes are required regardless
of isolation level.

**Q: Should report exports intentionally export only the current/default page?**

No — the current behavior (exports bypass pagination, UI shows only page 1) is the right UX outcome but
the wrong implementation. Export should be a deliberate, documented full-export path. The UI display
decision (paginate or show all) should be made explicitly and the type contract updated to match.

**Q: Should self role changes immediately log out the current user, or refresh `/auth/me` and navigate?**

Refreshing `/auth/me` and navigating based on the new role is the better UX. Forced logout is disruptive
and unnecessary — the backend already issues a new access token with updated claims on next refresh. The
fix sequence should be: detect self-edit, call `/auth/me` with current access token, update auth store,
let `ProtectedRoute` react to the new role. If the new role has fewer permissions, React Router will
redirect automatically.

**Q: Preferred DB strategy for nullable `batch_id` uniqueness?**

Partial unique index is the more surgical fix:
- `CREATE UNIQUE INDEX uq_stock_no_batch ON stock (location_id, article_id) WHERE batch_id IS NULL;`
- The existing constraint already covers the non-NULL case.

This avoids a schema column migration and works in PostgreSQL without touching existing rows. For Surplus,
a full uniqueness constraint (partial for NULL, covering for non-NULL) needs to be added from scratch.
A materialized batch key (replacing NULL with a sentinel) is an alternative but adds schema complexity
and requires a data migration.
