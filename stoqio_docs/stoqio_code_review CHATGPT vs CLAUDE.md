# STOQIO Code Review

## Review method

This review is being performed against the following source-of-truth hierarchy:

1. Current code behavior in the repository
2. `handoff/decisions/decision-log.md`
3. Phase handoff documentation in `handoff/`
4. Baseline product/spec documents in `stoqio_docs/`

That means not every mismatch versus the original spec is treated as a defect. Findings are classified as one of:

- **Bug / defect**
- **Intentional drift / approved change**
- **Documentation drift**
- **Incomplete migration / implementation gap**
- **Risk / maintainability issue**

## Constraints of this review session

- Static review only in this environment.
- I could not execute the backend test suite because required Python packages are not installed in the sandbox (`flask`, `flask_sqlalchemy`, `flask_jwt_extended`, `flask_migrate` missing).
- Findings below are therefore based on repository inspection, route/model/service tracing, and comparison against docs/handoff records.

---

## Part 1 — Repository baseline, structure, and documentation drift

### What looks good

- The monorepo is cleanly separated into `backend/`, `frontend/`, `scripts/`, `stoqio_docs/`, `handoff/`, and `memory/`.
- Backend structure is consistent with the intended service-layer architecture: `api/`, `models/`, `services/`, `utils/`.
- Frontend structure is also coherent: `api/`, `components/`, `pages/`, `store/`, `utils/`, `i18n/`.
- The handoff trail is unusually strong and materially useful for review. The decision log and per-phase handoff files make it possible to distinguish real bugs from approved behavioral drift.
- Test coverage breadth looks good at repository level: the backend contains dedicated test modules for auth, setup, drafts, approvals, articles/aliases, receiving, orders, employees, inventory count, reports, settings, and i18n.

### Findings

#### F-001 — Auth storage in docs/memory is outdated relative to current code and current decision log
- **Classification:** Documentation drift
- **Severity:** Medium
- **Why it matters:** This is a high-leverage behavioral contract. Anyone reviewing auth/session logic against the architecture doc alone will conclude the frontend is wrong, even though the decision log shows the opposite.
- **Evidence:**
  - `stoqio_docs/07_ARCHITECTURE.md:268-272` still says both tokens live only in Zustand and specifically says not to use `localStorage`.
  - `memory/MEMORY.md:13` repeats the same outdated statement.
  - `handoff/decisions/decision-log.md:520-527` explicitly changes the policy: refresh token is persisted in browser `localStorage`, access token remains memory-only.
  - `frontend/src/store/authStore.ts:11-40, 70-110` implements that new policy through `stoqio_refresh_token`.
- **Assessment:** Not a bug in the code. This is documentation/memory drift after a later accepted auth stabilization change.
- **Recommendation:** Update `stoqio_docs/07_ARCHITECTURE.md` and `memory/MEMORY.md` to match `DEC-FE-006` exactly, including bootstrap flow and the rule that only the refresh token may persist.

#### F-002 — Identifier backend lives under the Articles blueprint, which is valid but non-obvious from top-level API registration
- **Classification:** Intentional drift / approved structure
- **Severity:** Low
- **Why it matters:** At first glance the repository looks like it is missing a backend Identifier module because `backend/app/api/__init__.py` does not register a dedicated identifier blueprint, while the frontend clearly exposes `/identifier`.
- **Evidence:**
  - `frontend/src/routes.tsx:162-170` exposes `/identifier`.
  - `frontend/src/api/identifier.ts:59-92` calls `/identifier` and `/identifier/reports`.
  - `backend/app/api/__init__.py:10-36` registers no separate identifier blueprint.
  - `backend/app/api/articles/routes.py:103-150` defines the `/identifier*` endpoints inside the Articles blueprint.
- **Assessment:** This is not a defect. The endpoints exist and the frontend/backend contract is present. It is just structurally non-obvious.
- **Recommendation:** Keep as-is unless you want stricter module separation. If kept, mention this explicitly in either `backend/app/api/__init__.py` docstring or a short backend architecture note so reviewers do not misclassify it as a missing module.

#### F-003 — The empty `backend/app/api/warehouse/` package is surprising but currently justified
- **Classification:** Intentional drift / approved structure
- **Severity:** Low
- **Why it matters:** Without context it looks like unfinished backend work for Warehouse.
- **Evidence:**
  - `backend/app/api/warehouse/README.md:1` explicitly states the folder is intentionally empty and Warehouse data is served through `/api/v1/articles`.
  - This aligns with the current shared Articles/Warehouse namespace approach.
- **Assessment:** Not a bug. The README prevents misinterpretation.
- **Recommendation:** No code change required.

#### F-004 — Root README understates the current backend responsibility
- **Classification:** Documentation drift
- **Severity:** Low
- **Why it matters:** The root README still describes the backend as “future static asset serving”, but the Flask app already includes SPA static serving / catch-all behavior.
- **Evidence:**
  - `README.md:7` says `backend/` is “Flask API and future static asset serving”.
  - `backend/app/__init__.py` already contains frontend static serving and SPA fallback routing.
- **Assessment:** Minor docs drift only.
- **Recommendation:** Update README wording to reflect present behavior, not future intent.

#### F-005 — Review execution is partially blocked by missing runtime dependencies in the current sandbox
- **Classification:** Review environment limitation
- **Severity:** Informational
- **Why it matters:** I can trace and inspect code, but I cannot honestly claim runtime verification yet.
- **Evidence:** local environment here is missing `flask`, `flask_sqlalchemy`, `flask_jwt_extended`, and `flask_migrate`.
- **Assessment:** This is not a repo defect. It only affects what I can verify in this session.
- **Recommendation:** Continue with deep static review first. Later, if needed, run a second pass in an environment where backend dependencies are installed so findings can be confirmed against tests and migrations.

### Part 1 verdict

The repo baseline is generally well organized and reviewable. The most important thing uncovered in this first pass is **not** a code bug but a **source-of-truth drift** around authentication token storage. That drift is material enough that it can easily cause false bug reports during future reviews unless the architecture docs and memory file are brought into line with `DEC-FE-006`.

### Suggested next review slice

Part 2 should inspect:
- auth bootstrap / refresh / logout flow end-to-end
- RBAC enforcement consistency between frontend routing and backend decorators
- setup gate behavior versus the documented/admin-only setup rules


## Part 7 — Operational/bootstrap leftovers, hidden linkage contracts, and deploy hygiene

### What looks good

- The migration chain itself is linear and recent handoff notes indicate fresh `alembic upgrade head` has been validated on clean PostgreSQL installs during stabilization work.
- The repo does preserve a strong handoff trail, which makes it possible to understand why some “odd-looking” contracts exist today instead of misclassifying all of them as random bugs.

### Findings

#### F-024 — `backend/seed_location.py` is now an obsolete bootstrap helper that conflicts with the Phase 4 single-location setup model
- **Classification:** Incomplete migration / stale operational artifact
- **Severity:** Medium
- **Why it matters:** The project moved to a strict first-run setup flow where **no location is pre-seeded** and the initial location must be created through `/setup`, with `Location.id = 1` reserved for the single supported v1 location. But the repo still contains `seed_location.py`, and older handoff/testing docs still instruct people to run it. That script seeds by **name** (`"Main Warehouse"`) instead of by the reserved ID/invariant, so it can quietly create or preserve a location state that no longer matches the current setup contract.
- **Evidence:**
  - `backend/seed_location.py:14-24` still inserts `Location(name='Main Warehouse', is_active=True)` and only checks whether that name already exists.
  - `stoqio_docs/08_SETUP_AND_GLOBALS.md:85-96` now says **no location is seeded** and the first ADMIN must create it via first-run setup.
  - `handoff/decisions/decision-log.md:85-86` locks in the newer rule that backend setup reserves `Location.id = 1` for the installation's single supported v1 location.
  - Older verification docs still tell operators/agents to run the obsolete helper:
    - `handoff/phase-03-authentication/testing.md:51-53`
- **Assessment:** This is not a runtime feature bug in the app flow, but it is a real repo-level risk because a new reviewer/operator can follow stale docs and bootstrap the database into a state that bypasses or muddies the intended setup lifecycle.
- **Recommendation:** Retire `backend/seed_location.py` entirely, or at minimum mark it clearly as obsolete and unsafe for current installs. Also scrub remaining handoff/testing instructions that still tell people to run it.

#### F-025 — The bootstrap/admin tooling still encourages known default credentials, and `diagnostic.py` prints credential-sensitive information
- **Classification:** Risk / security hardening gap
- **Severity:** Medium
- **Why it matters:** The seed script creates a live `admin` user with the known password `admin123`, the README tells developers to run that seed script as part of setup, older handoff verification explicitly authenticates with those credentials, and `diagnostic.py` prints the stored password hash plus whether `admin123` matches. For local dev this is tolerable; for a Raspberry Pi deployment or any semi-production environment it is an avoidable footgun.
- **Evidence:**
  - `backend/seed.py:3-5, 48-60` documents and creates `admin / admin123`.
  - `README.md:17-25` includes `venv/bin/python seed.py` in the standard backend bootstrap path.
  - `handoff/phase-03-authentication/testing.md:60-73` explicitly verifies login with `admin / admin123`.
  - `backend/diagnostic.py:28-34` prints the password hash and whether the known default password matches.
- **Assessment:** This is more of an operational-security concern than an application bug, but it is meaningful because the repo is explicitly described as deployment-oriented, not just toy-local development.
- **Recommendation:** Keep a dev bootstrap path if needed, but move it to a safer pattern such as:
  - require an environment-provided initial admin password,
  - or generate a one-time random password on seed and print it once,
  - and remove the password-hash / password-match output from `diagnostic.py`.

#### F-026 — Inventory-shortage approval linkage depends on a hidden `client_event_id` naming convention instead of an explicit relational link
- **Classification:** Risk / maintainability issue
- **Severity:** Medium
- **Why it matters:** Inventory Count completion creates shortage drafts, and later summary logic discovers them by querying `Draft.client_event_id LIKE 'inv-count-{count_id}-line-%'`. This is documented and currently works, but it is a fragile hidden contract: any future refactor of client-event ID generation, draft import logic, or shortage-draft creation can silently break the linkage without a schema error.
- **Evidence:**
  - `backend/app/services/inventory_service.py:93-111` derives shortage summaries entirely from the deterministic `client_event_id` prefix pattern.
  - `backend/app/services/inventory_service.py:607-626` creates shortage drafts with `client_event_id = f"inv-count-{count_id}-line-{line.id}"`.
  - The handoff record explicitly acknowledges this as a deliberate compromise rather than a first-class schema relation:
    - `handoff/phase-08-wave-01-inventory-shortage-approval-status/backend.md`
    - `handoff/phase-08-wave-01-inventory-shortage-approval-status/orchestrator.md`
- **Assessment:** Not an immediate defect because the repo intentionally chose this approach. Still, it is exactly the kind of hidden contract that causes later regressions when new agents optimize or “clean up” IDs without realizing downstream logic depends on the naming pattern.
- **Recommendation:** Long-term, prefer an explicit relational link (for example `inventory_count_id` on shortage drafts or a dedicated linkage table). If you keep the current pattern for v1, at minimum centralize the format into a named helper/constant and add regression tests that fail loudly if the pattern changes.

#### F-027 — Deployment/build scripts are operationally brittle: frontend dependency installation and environment isolation are assumed rather than enforced
- **Classification:** Risk / deployment hygiene gap
- **Severity:** Medium
- **Why it matters:** `scripts/deploy.sh` pulls main, installs Python requirements into the active interpreter, builds the frontend, runs migrations, and restarts the service. But `scripts/build.sh` assumes frontend dependencies already exist and simply runs `npm run build`; `deploy.sh` does not run `npm install` / `npm ci`, does not activate a virtualenv, and does not include any smoke/lint/test gate before restart. On a machine where `node_modules` is missing/out of date or where the wrong Python environment is active, deployment can fail or behave inconsistently.
- **Evidence:**
  - `scripts/deploy.sh:8-23` runs `git pull`, `python3 -m pip install -r requirements.txt`, `./scripts/build.sh`, `alembic upgrade head`, then `systemctl restart wms`.
  - `scripts/build.sh:9-14` runs only `npm run build` before copying `frontend/dist` into `backend/static`.
  - The normal README dev path installs frontend dependencies manually (`README.md:30-33`), but the deploy script does not.
- **Assessment:** This is not a product-code bug, but it is a real ops fragility. It also helps explain why stale built assets and environment drift became recurring handoff themes.
- **Recommendation:** Harden deployment by making the scripts self-sufficient and explicit:
  - run `npm ci` (or at least verify `node_modules` / lockfile state) before frontend build,
  - install backend deps inside a known venv / service environment,
  - and consider adding at least a lightweight pre-restart verification step.

### Part 7 verdict

This slice did not surface a brand-new core business-logic defect on the level of stock/surplus/quota integrity. What it **did** reveal is that the repo still carries several **operational and maintainability leftovers** from earlier phases:
- an obsolete location-seeding helper that now conflicts with the setup model,
- a dev-friendly but deployment-risky default-admin bootstrap pattern,
- a brittle hidden linkage contract for inventory-generated shortage drafts,
- and deployment scripts that assume too much about the host environment.

These are exactly the kinds of issues that do not always fail tests immediately, but do create confusion, unsafe setups, and regressions later.

### Suggested next review slice

Part 8 should inspect:
- frontend pages/components for local state drift, duplicated mapping logic, and stale UI contracts not already covered,
- report/export and barcode flows for edge-case contract mismatches,
- and whether there are any remaining “accepted drift” areas that should now be folded back into the docs instead of living only in handoff notes.

## Part 8 — Frontend edge-case UX contracts, download/error handling, and remaining copy drift

### What looks good

- The frontend now has a reasonably consistent retry pattern for ordinary JSON requests through `runWithRetry(...)`, and many page modules do convert backend business errors into user-facing toasts.
- Download flows are not uniformly naive: the Warehouse barcode detail page already contains the **correct** blob-error parsing pattern via `getApiErrorBodyAsync(...)`, which provides a good local baseline for how the other download/export flows should behave.

### Findings

#### F-028 — Blob-download error handling is implemented inconsistently, so Reports exports and Order PDF download can lose backend business-error messages
- **Classification:** Bug / defect
- **Severity:** Medium
- **Why it matters:** Axios download requests use `responseType: 'blob'`. When the backend returns a structured JSON error for such a request (for example a 400/403 business error), the error body arrives as a `Blob`, not a plain object. The repo already has `getApiErrorBodyAsync(...)` specifically to parse those blob error bodies — but Reports export actions and Order PDF download still use the synchronous `getApiErrorBody(...)` helper instead. Result: these flows often fall back to generic toast text and lose the backend's actual localized message/details.
- **Evidence:**
  - `frontend/src/utils/http.ts:24-45` shows the split clearly:
    - `getApiErrorBody(...)` returns raw `error.response?.data`,
    - `getApiErrorBodyAsync(...)` is the helper that actually parses `Blob` JSON payloads.
  - **Correct implementation already exists** in Warehouse barcode download handling:
    - `frontend/src/pages/warehouse/ArticleDetailPage.tsx:414-425`
    - `frontend/src/pages/warehouse/ArticleDetailPage.tsx:439-455`
  - **But Reports exports still use the wrong sync parser** after blob downloads:
    - `frontend/src/pages/reports/ReportsPage.tsx:847-863`
    - `frontend/src/pages/reports/ReportsPage.tsx:873-881`
    - `frontend/src/pages/reports/ReportsPage.tsx:936-951`
  - **Order PDF download does the same**:
    - `frontend/src/pages/orders/OrderDetailPage.tsx:482-490`
  - Those flows call API methods that do use `responseType: 'blob'`:
    - `frontend/src/api/reports.ts:256-264`
    - `frontend/src/api/orders.ts:215-223`
- **Assessment:** Real defect. Users can get a vague generic failure toast even when the backend returned a more precise localized explanation.
- **Recommendation:** Standardize all blob-download error handlers on `await getApiErrorBodyAsync(error)` and use the parsed body for toasts. The Warehouse barcode flow is already the correct reference implementation.

#### F-029 — Mixed-language connection/fatal-state copy still exists outside auth/setup because the shared error baseline remains English
- **Classification:** Incomplete migration / implementation gap
- **Severity:** Low
- **Why it matters:** Earlier review slices already noted mixed-language auth/setup copy. This issue is broader: the shared HTTP connection error constant and several page-level fatal states still render English strings inside otherwise Croatian UI flows. That means even mature modules like Draft Entry and Order Detail can still fall back to English at exactly the moment the user most needs clarity.
- **Evidence:**
  - `frontend/src/utils/http.ts:9-10` still defines the shared connection copy in English: `"Connection error. Please check that the server is running and try again."`
  - `frontend/src/pages/drafts/DraftEntryPage.tsx:34-35, 596-600, 607-610` uses English `Connection error` / `Try again` page states.
  - `frontend/src/pages/orders/OrderDetailPage.tsx:498-502` still uses the same English fatal-state title/action.
  - Similar English full-page/fallback copy also remains in setup-related wrappers and a few other modules.
- **Assessment:** Not a functional bug, but still a product-consistency issue. The Croatian-first UI migration is visibly incomplete beyond just Login/Setup.
- **Recommendation:** Centralize these strings behind the same Croatian-first baseline used elsewhere in the app. Because the shared constant already exists, this is mostly a cleanup/normalization task rather than a deep refactor.

### Part 8 verdict

This slice uncovered one genuine frontend defect — **blob-download error parsing is inconsistent**, so some export/download flows throw away useful backend error messages even though the repo already contains the correct async parser. Beyond that, the remaining issue is mostly polish/product consistency: the app still has pockets of English fallback UI in critical error states.

### Suggested next review slice

Part 9 should inspect:
- whether any backend services still rely on implicit ordering or naming conventions beyond the ones already identified,
- whether there are any remaining obsolete scripts/docs that can mislead deployments,
- and finally produce a prioritized remediation shortlist from all findings so far.

## Part 9 — Cross-review synthesis against the project-aware external review

### Method used in this reconciliation pass

I compared the additional project-aware review (`stoqio-code-review CLAUDE.md`) against:
- the current repository state,
- the existing findings already recorded in this document,
- and the same source-of-truth hierarchy used for the rest of this review.

I only promoted claims into this document when I could confirm them directly from the codebase or when they clearly aligned with already-established handoff/doc drift patterns. This avoids simply merging two reviews into a larger but noisier list.

### Overlap with already-recorded findings

The external review strongly reinforces several findings that were already present in substance in this review:

- **Auth token storage documentation drift** is real and already captured in **F-001**.
- **The stale location/bootstrap helper problem** is real and already captured in **F-024**.
- **The inventory-shortage linkage via `client_event_id` naming convention** is real and already captured in **F-026**.
- **Blob-download error parsing inconsistency** in frontend export/download flows is real and already captured in **F-028**.
- **English fallback / mixed-language error-state UX** is broader than first noted and should now be treated as a repo-wide cleanup theme, not an isolated page issue.

So the external review is valuable not because it changes those conclusions, but because it independently confirms that they are not one-off reviewer interpretation errors.

### New confirmed findings added after comparison

#### F-030 — `DraftGroup.status` can remain persisted as `PENDING` even when the group's effective display status is `PARTIAL`
- **Classification:** Bug / defect
- **Severity:** High
- **Why it matters:** This creates a genuine data-consistency problem between persisted model state and the service-layer/computed state exposed to the UI. Today the UI mostly survives because pending/history views derive state from `Draft.status`, not only from `DraftGroup.status`. But any future reporting, filtering, admin tooling, or migration logic that trusts the stored group status can be wrong.
- **Evidence:**
  - `backend/app/services/approval_service.py:541-556` computes `status = _compute_group_display_status(group_id)` and then explicitly does nothing when the result is `PARTIAL`.
  - The code comment acknowledges the unresolved state directly: the service currently leaves the DB row as `PENDING` because `PARTIAL` is not in the persisted enum.
  - `backend/tests/test_approvals.py:710-748` verifies only the **computed API surface** (`status == "PARTIAL"` in history), not correction of the persisted `DraftGroup.status` field.
- **Assessment:** Real bug, not just tech debt. The repo currently relies on a computed-status escape hatch to mask an inconsistent persisted state.
- **Recommendation:** Pick one explicit design and make it real end-to-end:
  1. add `PARTIAL` to `DraftGroupStatus`, migrate the enum, and persist it properly, or
  2. formally make `DraftGroup.status` non-authoritative for resolved groups and replace it with a clearly documented/computed-only model. Right now it is in an ambiguous middle state.

#### F-031 — Login/auth bootstrap surfaces are still materially English-first
- **Classification:** Incomplete migration / implementation gap
- **Severity:** Medium
- **Why it matters:** The login/setup path is the first UX every user sees. In the current repo it still presents major English-first copy even though operational pages are otherwise Croatian-oriented.
- **Evidence:**
  - `frontend/src/pages/auth/LoginPage.tsx:35, 56-59, 76-106` contains English labels and messages such as `Username and password are required.`, `STOQIO Login`, `Please sign in with your credentials`, `Username`, `Password`, `Sign in`.
  - `frontend/src/components/layout/SetupGuard.tsx:8-9, 84-86` still uses English connection/fallback copy.
  - The login path also shows English fallback toast text on auth failure (`Login failed. Please try again.`).
- **Assessment:** Not a backend defect, but this is a product-facing inconsistency significant enough to keep visible in the final remediation plan.
- **Recommendation:** Treat login/setup/auth failure copy as part of the same localization cleanup bucket as F-029, not as isolated page polish.

#### F-032 — Connection/fatal-state handling is only partially standardized; several key pages still bypass shared HTTP utilities
- **Classification:** Risk / maintainability issue
- **Severity:** Medium
- **Why it matters:** The repo already contains `frontend/src/utils/http.ts` with shared retry and error-body helpers, but adoption is incomplete. That leads to duplicated logic, inconsistent wording, and inconsistent blob-vs-JSON error handling.
- **Evidence:**
  - Shared utilities exist in `frontend/src/utils/http.ts`.
  - But `frontend/src/pages/approvals/ApprovalsPage.tsx`, `frontend/src/pages/drafts/DraftEntryPage.tsx`, and `frontend/src/pages/receiving/ReceivingPage.tsx` each still define local versions of network/server error handling and/or connection copy.
  - `frontend/src/components/layout/SetupGuard.tsx` also carries its own English fatal-state copy instead of pulling from a centralized shared baseline.
- **Assessment:** This does **not** mean the shared utility is “almost unused”; that would be overstated. It **is** true, however, that the repo is in a partially migrated state where some newer pages use shared helpers and some older/high-churn pages still duplicate them.
- **Recommendation:** Normalize on one shared HTTP/error-state layer and one localized copy baseline. This should be handled together with F-028 and F-029.

#### F-033 — `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` are emitted by services but missing from the i18n catalog
- **Classification:** Bug / defect
- **Severity:** Medium
- **Why it matters:** These are structured domain error codes, but the localization catalog does not define user-facing translations for them. As a result, users can receive English fallback messages in otherwise localized flows.
- **Evidence:**
  - `backend/app/services/receiving_service.py:384-391` raises `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED`.
  - `backend/app/services/order_service.py:422-429` also raises the same codes.
  - `backend/app/utils/i18n.py` does not define catalog entries for those codes.
  - `backend/tests/test_receiving.py:654` explicitly asserts one of those codes is emitted.
- **Assessment:** Real gap. This is a small fix with clear user-facing value.
- **Recommendation:** Add localized catalog entries for both codes and any corresponding detail text.

#### F-034 — Route-level query parsing helpers are still duplicated across multiple backend modules despite the repo already having a shared validation utility module
- **Classification:** Risk / maintainability issue
- **Severity:** Low
- **Why it matters:** This is not a correctness bug today, but it is exactly the kind of duplication that causes slightly different semantics and error text to drift over time.
- **Evidence:**
  - `backend/app/utils/validators.py` already exists as a shared validation utility module.
  - Yet `_parse_positive_int` and/or `_parse_bool_query` remain redefined in multiple route files, including `articles`, `orders`, `receiving`, `inventory_count`, `employees`, and `settings`.
- **Assessment:** Confirmed duplication. Lower severity than the stock/surplus/quota issues, but worth fixing while the codebase is still relatively compact.
- **Recommendation:** Move shared query parsing helpers into a single backend utility module and standardize error semantics there.

#### F-035 — The timing-safe login path depends on a hardcoded dummy PBKDF2 hash string
- **Classification:** Risk / maintainability issue
- **Severity:** Low
- **Why it matters:** The security intention is good: always call `check_password_hash(...)` even for nonexistent users. The fragility is that the dummy hash is hardcoded to a specific algorithm/format. If password hashing policy changes later, this constant can silently become stale.
- **Evidence:**
  - `backend/app/api/auth/routes.py:106-113` embeds a literal PBKDF2 hash string in `_dummy_hash`.
- **Assessment:** This is not an immediate vulnerability. It is a maintenance trap that can quietly degrade the intended timing-equalization behavior later.
- **Recommendation:** Generate the dummy hash through the same supported hash function/policy used by the app, or centralize it in one auth utility with an explicit comment/test guarding future algorithm changes.

#### F-036 — Production config hard-fails weak/missing JWT secrets, but does not equivalently hard-fail an unset `DATABASE_URL`
- **Classification:** Risk / deploy hygiene gap
- **Severity:** Low
- **Why it matters:** In `Production`, the app refuses to start with a weak JWT secret, which is good. But it does not mirror that strictness for the DB URI. Instead it allows an empty database URI to flow deeper into app startup/runtime.
- **Evidence:**
  - `backend/app/config.py:34-48` sets `self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "")` in `Production.__init__`.
  - No equivalent `RuntimeError` is raised when that value is empty.
- **Assessment:** This is a startup-hardening gap, not a functional business-logic bug.
- **Recommendation:** Fail fast in `Production` when `DATABASE_URL` is missing, just as the code already does for `JWT_SECRET_KEY`.

#### F-037 — Shell branding/settings are loaded only for `ADMIN`, so non-admin users always fall back to default location/role labels
- **Classification:** Intentional simplification / possible product gap
- **Severity:** Low
- **Why it matters:** The sidebar and shell clearly support a dynamic location name and role display names, but the current loading logic only fetches those settings for `ADMIN`. That means non-admin roles always see fallback branding (`STOQIO`) and default role labels even when custom settings exist.
- **Evidence:**
  - `frontend/src/components/layout/AppShell.tsx:16-21` only calls `loadShellSettings()` when `user?.role === 'ADMIN'`.
  - `frontend/src/store/settingsStore.ts:13-17, 45-47` defines `DEFAULT_LOCATION_NAME` and default role-display labels.
  - `frontend/src/components/layout/Sidebar.tsx:13-32, 75-82` renders those values for all authenticated users.
- **Assessment:** This may be a conscious performance/permission simplification, so I am not classifying it as a hard bug. But it is a real product-contract gap if the expectation is that global naming/branding applies to all users.
- **Recommendation:** Decide explicitly whether shell branding is admin-only runtime state or installation-wide display state. If installation-wide, load it for all roles through a minimal read-only endpoint or bootstrap payload.

### Findings from the external review that I am **not** promoting as accepted findings

#### N-001 — “`python-barcode` is missing from `requirements.txt`” is **not supported by the current codebase**
- **Reason:** The barcode implementation does **not** import `python-barcode`.
- **Evidence:**
  - `backend/app/services/barcode_service.py` uses `reportlab.graphics.barcode.createBarcodeDrawing`.
  - `backend/requirements.txt` already includes `reportlab>=4.4,<5`.
- **Assessment:** I am not adding this as a repo defect. The current runtime dependency path is ReportLab, not `python-barcode`.

#### N-002 — “`INTEGER_UOMS` is defined in 3+ places” is **overstated**
- **Reason:** The canonical constant definition appears in one place: `frontend/src/utils/uom.ts`.
- **What is actually true instead:** formatting/step/scale helper logic that *uses* integer-UOM behavior is duplicated across several pages/modules.
- **Assessment:** The real maintainability issue is duplicated quantity-formatting behavior, not multiple conflicting constant definitions.

#### N-003 — “`utils/http.ts` is almost unused” is **too strong**
- **Reason:** Multiple pages already import from it (`Orders`, `OrderDetail`, `Reports`, `Settings`, `Identifier`, `Inventory`, and others).
- **What is actually true instead:** adoption is incomplete and uneven, especially in `DraftEntryPage`, `ApprovalsPage`, `ReceivingPage`, and setup/auth wrappers.
- **Assessment:** I am retaining the more precise formulation in **F-032** rather than the stronger claim.

### Part 9 verdict

The external review was useful and materially improved the overall review quality. It did **not** overturn the major earlier conclusions from this document, but it did help surface several additional issues worth carrying forward into the final remediation phase:

- one **real backend state-consistency bug** around persisted-vs-computed `DraftGroup` status,
- several **localization / UX consistency gaps** in login/setup/fatal states,
- one **small but real i18n defect** around receiving/order-line domain errors,
- and a few additional **deploy/maintainability cleanup items**.

It also helped filter out a few claims that sound plausible at first glance but are not actually supported by the current codebase.
