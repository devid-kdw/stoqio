# Backend Handoff — Wave 1 Phase 7 My Entries Today Status

Reserved for backend agent entries. Append only.

---

## Entry — 2026-03-24 (Wave 1 Phase 7 Backend)

**Status**: Complete

**Scope**:
Add `GET /api/v1/drafts/my` — a dedicated, authenticated-user endpoint returning the caller's own `DAILY_OUTBOUND` draft lines for a given operational date. No changes to the existing `GET /api/v1/drafts` shape.

**Docs Read**:
- `stoqio_docs/09_UI_DRAFT_ENTRY.md`
- `stoqio_docs/03_RBAC.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md` § 4
- `handoff/README.md`
- `handoff/decisions/decision-log.md` (DEC-BE-016)
- `handoff/wave-01/phase-05-wave-01-rejection-reason-visibility/orchestrator.md`
- `handoff/wave-01/phase-07-wave-01-my-entries-today-status/orchestrator.md`
- `backend/app/api/drafts/routes.py`
- `backend/tests/test_drafts.py`

**Files Changed**:

| File | Change |
|------|--------|
| `backend/app/api/drafts/routes.py` | Added `GET /api/v1/drafts/my` route (additive only; existing routes untouched) |
| `backend/tests/test_drafts.py` | Added `TestMyDraftLines` class (14 new tests) |
| `handoff/wave-01/phase-07-wave-01-my-entries-today-status/backend.md` | This entry |

**Implementation Notes**:
- Route `GET /api/v1/drafts/my` placed between the existing `GET /drafts` and `POST /drafts` handlers.
- Uses `_get_operational_today()` as the default; accepts optional `?date=YYYY-MM-DD` validated via `date.fromisoformat()`, returning `400 VALIDATION_ERROR` on parse failure.
- Queries all `DAILY_OUTBOUND` `DraftGroup` rows for the operational date (any status), then filters `Draft` rows by `Draft.created_by == user.id`.
- Serialises with the existing `_serialize_draft()` helper — includes all required fields (`article_no`, `description`, `quantity`, `uom`, `batch_code`, `status`, `rejection_reason`, `created_at`), newest-first.
- `INVENTORY_SHORTAGE` groups excluded by the `group_type=DraftGroupType.DAILY_OUTBOUND` filter on the group query.
- No shared approval/draft serialisation helper was modified.
- Response shape: `{"lines": [...]}` — 200.

**Commands Run**:
```
backend/venv/bin/pytest backend/tests/test_drafts.py -q
backend/venv/bin/pytest backend/tests/test_approvals.py -q
```

**Tests**:
```
test_drafts.py:     54 passed in 0.90s  (was 40 before; 14 new)
test_approvals.py:  22 passed in 0.65s  (no regressions)
```

New test coverage in `TestMyDraftLines`:
- `test_operator_gets_200`
- `test_viewer_gets_403`
- `test_unauthenticated_gets_401`
- `test_default_date_returns_today`
- `test_explicit_date_param_returns_matching_entries`
- `test_explicit_date_param_excludes_other_dates`
- `test_invalid_date_param_returns_400`
- `test_invalid_date_format_returns_400`
- `test_returns_only_authenticated_user_lines`
- `test_required_fields_present_on_each_line`
- `test_pending_draft_line_has_null_rejection_reason`
- `test_rejected_line_has_rejection_reason_string`
- `test_excludes_inventory_shortage_group_lines`
- `test_newest_first_ordering`
- `test_existing_get_drafts_still_has_same_day_lines`

**Open Issues / Risks**: None. No spec gaps encountered.

**Assumptions**:
- `ADMIN` can call `/drafts/my` and will receive only their own submitted lines (matches orchestrator spec: "ADMIN can call the endpoint, but it still returns only the authenticated user's own submitted lines").
- `date.fromisoformat()` rejects both non-date strings and impossible dates (e.g. `2026-13-01`), which satisfies the ISO `YYYY-MM-DD` enforcement requirement.

**Next Recommended Step**: Frontend Agent — retarget the "Moji unosi danas" section to `GET /api/v1/drafts/my` and add 60-second auto-refresh per the orchestrator delegation prompt.

