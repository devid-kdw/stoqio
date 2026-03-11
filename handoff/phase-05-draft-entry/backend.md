# Phase 05 — Draft Entry Backend

**Timestamp**: 2026-03-11T18:26 CET

## Status

✅ Complete — all endpoints implemented, tested, zero regressions.

## Scope

Backend API for the Draft Entry screen (Phase 5):
- Draft CRUD: GET/POST/PATCH/DELETE `/api/v1/drafts`
- Article lookup: GET `/api/v1/articles?q={query}` (by article_no or barcode)
- Batch FEFO: batch-tracked articles return batches ordered by `expiry_date ASC`
- Validators: batch-code regex, quantity (>0), note (max 1000 chars)

## Docs Read

- `stoqio_docs/09_UI_DRAFT_ENTRY.md` — full
- `stoqio_docs/05_DATA_MODEL.md` § 10 (Draft), § 11 (DraftGroup)
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 5 (Draft → Approval workflow)
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3 (validation rules)
- `stoqio_docs/07_ARCHITECTURE.md` § 2 (API conventions)
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

## Files Changed

| File | Action |
|------|--------|
| `backend/app/utils/validators.py` | NEW — batch-code regex, quantity, note validation |
| `backend/app/api/articles/routes.py` | NEW — article lookup endpoint |
| `backend/app/api/drafts/routes.py` | NEW — draft CRUD endpoints |
| `backend/app/api/__init__.py` | MODIFIED — registered articles_bp and drafts_bp |
| `backend/tests/test_drafts.py` | NEW — 22 integration tests |

## Commands Run

```bash
cd backend && python -m pytest tests/test_drafts.py -v   # 22 passed
cd backend && python -m pytest tests/ -v                  # 69 passed, 0 failed
```

## Tests

22 new tests in `test_drafts.py`:

**Article lookup (6):**
- Lookup by article_no (case-insensitive)
- Lookup by barcode
- Article not found → 404
- Batch-tracked article returns FEFO-ordered batches
- Missing query param → 400
- MANAGER role → 403

**GET drafts (2):**
- Empty day returns empty list
- Unauthenticated → 401

**POST drafts (8):**
- Create line (no batch) → 201 with correct response shape
- Idempotency: same client_event_id → 200, no duplicate
- Zero quantity → 400
- Negative quantity → 400
- Missing article → 404
- Batch required for batch-tracked article → 400
- Create with batch → 201, batch_code in response
- MANAGER role → 403

**PATCH drafts (3):**
- Update quantity → 200
- APPROVED line → 400 INVALID_STATUS
- Not found → 404

**DELETE drafts (3):**
- Delete draft line → 200
- APPROVED line → 400
- Not found → 404

## Open Issues / Risks

1. **SQLite vs PostgreSQL in tests**: All tests use in-memory SQLite (per existing `conftest.py`). SQLite-compatible queries only (no `ILIKE`, no PG-specific). First PostgreSQL deploy should be verified manually.
2. **DraftGroup group_number sequence**: Uses `DraftGroup.id + 1` for simplicity. On PostgreSQL with concurrent inserts, the `group_number` UNIQUE constraint protects against duplicates, but a retry loop is not implemented — acceptable for v1 single-location, low-concurrency use.
3. **zoneinfo fallback**: `_get_operational_today()` falls back to UTC if `zoneinfo` is unavailable. Python 3.9+ includes `zoneinfo` in stdlib — not a risk for the documented Python 3.11+ requirement.

## Next Recommended Step

- Phase 5 frontend: implement `DraftEntryPage.tsx` calling these endpoints.
- Phase 6: Approvals backend (approve/reject drafts, stock mutation, surplus-first consumption).

## [2026-03-11 19:43] Orchestrator Follow-up (Codex)

Status
- completed

Scope
- Closed post-review backend gaps in Phase 5:
- retried transient `DraftGroup` creation conflicts instead of surfacing avoidable `409`
- stopped trusting client-provided `uom` and now derive/validate it from article master data
- strengthened Draft Entry tests so they assert the created line correctly and cover the new retry/UOM paths
- isolated the Draft Entry test UOM fixture from the shared backend suite so Phase 2 model tests no longer collide

Docs Read
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 3, § 4
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 5
- `handoff/README.md`

Files Changed
- `backend/app/api/drafts/routes.py`
- `backend/tests/test_drafts.py`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_drafts.py -q
backend/venv/bin/pytest backend/tests -q
```

Tests
- Passed:
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q` → `25 passed`
  - `backend/venv/bin/pytest backend/tests -q` → `72 passed`
- Failed:
  - None
- Not run:
  - PostgreSQL-specific concurrent-write smoke test outside the sandbox

Open Issues / Risks
- Draft-group race handling is now retried with a short backoff in application code without a schema change. That closes the reviewed bug for v1 behavior, but first PostgreSQL deployment should still get a brief manual concurrency smoke check.

Next Recommended Step
- Accept the backend follow-up and keep Phase 6 focused on approvals and stock mutation.

## [2026-03-11 20:13] Product Semantics Follow-up (Codex)

Status
- completed

Scope
- Aligned Phase 5 backend with the updated product decision that the optional note belongs to the whole daily draft, not to individual draft lines.
- Kept `Employee ID` as an optional line-level field on create, but removed line-level note handling from the active Draft Entry API workflow.

Docs Read
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/04_FEATURE_SPEC.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/10_UI_APPROVALS.md`
- `handoff/decisions/decision-log.md`
- `handoff/README.md`

Files Changed
- `backend/app/api/drafts/routes.py`
- `backend/app/utils/validators.py`
- `backend/tests/test_drafts.py`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_drafts.py -q
backend/venv/bin/pytest backend/tests -q
```

Tests
- Passed:
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q` → `29 passed`
  - `backend/venv/bin/pytest backend/tests -q` → `76 passed`
- Failed:
  - None
- Not run:
  - PostgreSQL-specific concurrency smoke test outside the sandbox

Open Issues / Risks
- `Draft.note` remains in the schema as a legacy field, but Phase 5 now treats `DraftGroup.description` as the only active note field in the operator workflow. If a future migration removes `Draft.note`, API and docs are already aligned for that cleanup.

Next Recommended Step
- Keep Phase 6 approvals work aligned with the new shared draft-note semantics and do not reintroduce line-level note handling in approval views.

## [2026-03-11 20:42] Numbering Follow-up (Codex)

Status
- completed

Scope
- Replaced the user-facing `DraftGroup.group_number` generation logic so it no longer derives from sparse database IDs.
- The next `IZL-####` number is now based on the maximum existing numeric suffix in `group_number`, which matches the intended visible numbering better than the previous `id + 1` approach.
- Clarified in the `Draft` model that the legacy line-level `note` column remains only for schema compatibility and is not part of the active v1 Draft Entry flow.

Docs Read
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/decisions/decision-log.md`
- `handoff/README.md`

Files Changed
- `backend/app/api/drafts/routes.py`
- `backend/app/models/draft.py`
- `backend/tests/test_drafts.py`
- `handoff/decisions/decision-log.md`

Commands Run
```bash
backend/venv/bin/pytest backend/tests/test_drafts.py -q
backend/venv/bin/pytest backend/tests -q
```

Tests
- Passed:
  - `backend/venv/bin/pytest backend/tests/test_drafts.py -q` -> `30 passed`
  - `backend/venv/bin/pytest backend/tests -q` -> `77 passed`
- Failed:
  - None
- Not run:
  - PostgreSQL-specific concurrent-write smoke test outside the sandbox

Open Issues / Risks
- The max-suffix strategy is safer than `id + 1` without adding a dedicated DB sequence, but it still depends on the existing `group_number` format staying canonical (`IZL-####`). Future schema work could replace this with a dedicated sequence if numbering requirements grow stricter.

Next Recommended Step
- Keep `group_number` generation behind helper logic and do not couple it back to primary keys in later phases.
