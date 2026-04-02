# Phase 06: Approvals (Testing)

## 2026-03-11: Approvals Integration Tests

**Status**: ✅ Review
**Scope**: Wrote robust integration tests for `Approvals` logic to strictly enforce business rules.

**Docs Read**:
- `10_UI_APPROVALS.md`
- `02_DOMAIN_KNOWLEDGE.md` §1 and §5
- `05_DATA_MODEL.md` §8, §9, §10, §11, §12, §16
- `03_RBAC.md`

**Files Changed**:
- `[NEW] backend/tests/test_approvals.py`

**Commands Run**:
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q`
- `backend/venv/bin/pytest backend/tests -q`

**Tests**:
- 15 total test scenarios covering all required logic (GET aggregation, GET details, approve stock, approve surplus+stock, insufficient stock, mixed approve, batch edits, row rejection, draft rejection, duplicate approval, manager access, transaction sign correctness, duplicate accounting logic, and `PARTIAL` group status computations).
- Tests confirm exactly 5 critical failures in the backend implementation as expected:
    - Missing aggregation/missing `lines` array.
    - Returning 400 instead of 409 for INSUFFICIENT_STOCK.
    - Duplicate accounting bug calculating 2x consumption.

**Open Issues / Risks**:
- The backend implementation of the Approval endpoints currently fails strict business requirements. Tests are designed to flag this.

**Next Recommended Step**:
- Developer needs to fix the `backend/app/services/approval_service.py` to ensure all tests in `test_approvals.py` pass.

## 2026-03-11 21:37 CET

**Status**: Completed
**Scope**: Cleaned the approvals test suite so it measures the actual Phase 6 contract, removed test-state leakage, and aligned the migration regression test with the new Phase 6 head migration.

**Docs Read**:
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`

**Files Changed**:
- `backend/tests/test_approvals.py`
- `backend/tests/test_phase2_models.py`

**Commands Run**:
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q`
- `backend/venv/bin/pytest backend/tests -q`

**Tests**:
- `backend/tests/test_approvals.py` now passes with `15 passed`.
- Full backend suite now passes with `92 passed`.

**Open Issues / Risks**:
- The remaining backend warnings are the pre-existing short JWT secret warnings from the test fixture configuration.

**Next Recommended Step**:
- Treat the cleaned approvals suite as the Phase 6 regression baseline for any later approvals or schema-cleanup work.
