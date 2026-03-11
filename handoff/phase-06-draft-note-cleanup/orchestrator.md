## Phase Summary

Phase
- phase-06-draft-note-cleanup

Objective
- Remove the legacy `Draft.note` schema column after Phase 6 approvals validation confirmed it is no longer needed.

Source Docs
- `handoff/phase-05-draft-entry/orchestrator.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `handoff/README.md`

Delegation Plan
- Backend:
- Remove `Draft.note` from the model and add a dedicated Alembic migration that drops the column safely.
- Frontend:
- None.
- Testing:
- Revalidate migration head schema and backend regression coverage after the cleanup.

Acceptance Criteria
- `Draft.note` is removed from the SQLAlchemy model and database head schema.
- Existing databases can reach head via Alembic migration.
- Draft Entry and Approvals backend flows still pass regression tests.

Validation Notes
- [2026-03-11 21:50] Cleanup scoped narrowly to schema/model/doc/test changes after Phase 6 acceptance. No approval behavior changes are included.
- [2026-03-11 21:50] Validation complete: `backend/tests/test_phase2_models.py -q` passed, targeted Draft/Approvals regression passed, and `backend/tests -q` passed with only existing JWT test-fixture warnings.

Next Action
- Run `alembic upgrade head` on existing local databases before further manual backend testing.
