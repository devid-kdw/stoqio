## Phase Summary

Phase
- Phase 6 - Approvals

Objective
- Deliver the approvals workflow end to end, then close the review findings with a cleaned regression suite and code fixes that match the documented Phase 6 contract.

Source Docs
- `stoqio_docs/10_UI_APPROVALS.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md`
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/08_SETUP_AND_GLOBALS.md`
- `stoqio_docs/03_RBAC.md`
- `handoff/README.md`

Validation Notes
- Initial agent delivery left Phase 6 incomplete: the approvals test suite mixed real failures with contract mismatches and fixture leakage.
- Orchestrator follow-up first cleaned `backend/tests/test_approvals.py` so the suite asserted:
  - representative `line_id`
  - `draft_group_id` and `rows` contract fields
  - isolated `ApprovalOverride` state between tests
  - UOM code correctness in aggregated rows
- After test cleanup, the remaining real defects were:
  - pending approvals list omitted aggregated rows
  - approvals detail returned UOM FK ids instead of UOM codes
  - insufficient stock returned `400` instead of `409`
  - the new approval override migration was empty and the override uniqueness was unsafe for `NULL batch_id`
- Orchestrator follow-up fixed those backend issues and also closed frontend review issues around fatal retry handling and stale post-action refresh.
- Post-Phase-6 schema cleanup for legacy `Draft.note` was completed separately in `handoff/phase-06-draft-note-cleanup/` after approvals validation confirmed no hidden dependency remained.

Verification
- `backend/venv/bin/pytest backend/tests/test_approvals.py -q` -> `15 passed`
- `backend/venv/bin/pytest backend/tests -q` -> `92 passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> pass
- `cd frontend && npm run build` -> pass
- Post-closeout cleanup verification:
  - `backend/venv/bin/pytest backend/tests/test_phase2_models.py -q` -> `2 passed`
  - `backend/venv/bin/pytest backend/tests/test_drafts.py backend/tests/test_approvals.py -q` -> `45 passed`
  - `backend/venv/bin/pytest backend/tests -q` -> `92 passed`

Residual Notes
- Vite still reports the existing main-chunk size warning; no functional regression was observed.
- Existing databases must still run `alembic upgrade head` to pick up the approvals and `Draft.note` cleanup migrations before manual runtime testing.

Next Action
- Phase 6 can be treated as closed on the current codebase and documentation baseline.
- Apply `alembic upgrade head` on any existing local/dev/prod database before further manual verification or deployment.
