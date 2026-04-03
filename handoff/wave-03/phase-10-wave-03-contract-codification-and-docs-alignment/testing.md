## [2026-04-03 17:19 CEST] Testing Delivery

Status
- completed

Scope
- Added explicit regression coverage that makes the accepted Phase 10 contracts obvious to future reviewers.
- Locked lowercase `DraftSource` round-trip behavior.
- Locked the dual-mode `/api/v1/orders` contract so `q` exact-match compatibility and paginated list mode stay clearly separate.

Docs Read
- `/Users/grzzi/Desktop/stoqio_wave_3_implementation_and_orchestrator_prompts.md` (`W3-011`, `W3-012`)
- `handoff/README.md`
- `handoff/wave-03/phase-10-wave-03-contract-codification-and-docs-alignment/orchestrator.md`
- `handoff/wave-03/phase-10-wave-03-contract-codification-and-docs-alignment/backend.md`
- `backend/tests/test_drafts.py`
- `backend/tests/test_orders.py`
- `backend/app/models/enums.py`
- `backend/app/api/drafts/routes.py`
- `backend/app/api/orders/routes.py`

Files Changed
- `backend/tests/test_drafts.py`
- `backend/tests/test_orders.py`
- `handoff/wave-03/phase-10-wave-03-contract-codification-and-docs-alignment/testing.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_drafts.py tests/test_orders.py -q
```

Tests
- Added `backend/tests/test_drafts.py::TestCreateDraft::test_source_contract_round_trips_lowercase_wire_values`
- The test iterates over `DraftSource.scale` and `DraftSource.manual` and asserts the response serializes the same lowercase wire value that was submitted.
- Added `backend/tests/test_orders.py::TestOrdersContracts::test_q_mode_exact_match_and_list_mode_remain_separate_contracts`
- The test asserts `GET /api/v1/orders?q=...` stays in exact-match compatibility mode even if pagination/status params are present.
- The same test asserts list mode still returns the paginated contract independently with `page`, `per_page`, and `items`.
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_drafts.py tests/test_orders.py -q` -> `72 passed`

Open Issues / Risks
- None in the testing scope. The codified behavior is now explicit in both test names and assertions.

Manual Verification Checklist
- Not required beyond the automated backend regression slice for this phase.
- If future reviewers want a quick spot-check, the two new tests are the clearest contract anchors:
- `TestCreateDraft::test_source_contract_round_trips_lowercase_wire_values`
- `TestOrdersContracts::test_q_mode_exact_match_and_list_mode_remain_separate_contracts`

Next Recommended Step
- Documentation agent should align the relevant docs wording with the codified backend contract so the accepted behavior is obvious in prose too.
