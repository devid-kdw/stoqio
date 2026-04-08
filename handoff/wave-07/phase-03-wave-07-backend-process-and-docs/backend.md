## [2026-04-08] Backend Process and Documentation Cleanup Agent — Wave 7 Phase 3

Status
- completed (tests not run — Bash tool denied; all code changes verified by static inspection)

Scope
- M-8: seed.py uses pbkdf2 instead of scrypt — updated to scrypt, added scrypt assertion test
- L-1: report stock overview and surplus pagination bare int() calls can 500 — replaced with parse_positive_int()
- N-4: transaction log pagination passes raw strings to service — converted to int at route layer via parse_positive_int()
- L-3: stale pbkdf2 comment in auth.py — updated to scrypt; stale test name in test_auth.py renamed
- L-4: Wave 6 frontend handoff stale about eslint-plugin-security — correction note appended
- L-5: Wave 6 verification notes conflict — correction note appended to orchestrator.md
- L-6: README revoked-token cleanup docs outdated — updated to describe both automatic and manual cleanup
- L-7: requirements.lock contains stale python-barcode — removed after confirming no source imports it

Docs Read
- handoff/README.md
- handoff/wave-07/phase-03-wave-07-backend-process-and-docs/orchestrator.md
- handoff/decisions/decision-log.md (confirmed DEC-SEC-002 scrypt policy exists)
- backend/seed.py
- backend/tests/test_seed_hardening.py
- backend/tests/test_auth.py
- backend/app/api/reports/routes.py
- backend/app/api/employees/routes.py (parse_positive_int import pattern)
- backend/app/utils/auth.py
- backend/app/utils/validators.py (confirmed parse_positive_int signature)
- backend/app/services/report_service.py (confirmed get_transaction_log signature accepts int or None)
- backend/requirements.lock
- README.md
- handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md
- handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md
- handoff/templates/agent-handoff-template.md

Files Changed
- `backend/seed.py` — line 73: changed `method="pbkdf2:sha256"` to `method="scrypt"` in _seed_admin()
- `backend/tests/test_seed_hardening.py` — added new test `test_seed_admin_hashes_password_with_scrypt` that captures the password_hash kwarg passed to User() and asserts it starts with "scrypt:"
- `backend/tests/test_auth.py` — renamed test method `test_get_dummy_hash_returns_valid_pbkdf2_hash` to `test_get_dummy_hash_returns_valid_scrypt_hash`; updated its docstring to reference scrypt and DEC-SEC-002. Code logic unchanged.
- `backend/app/utils/auth.py` — updated comment at line 19 from "Using pbkdf2:sha256 keeps this aligned with the app's supported hash policy" to "Using scrypt keeps this aligned with the app's password hash policy (DEC-SEC-002)"
- `backend/app/api/reports/routes.py` — added import of `QueryValidationError, parse_positive_int` from app.utils.validators; replaced bare `int()` calls in get_stock_overview and get_surplus_report with `parse_positive_int()`; updated get_transaction_log to parse page/per_page with `parse_positive_int()` before passing to service; added `QueryValidationError` to all three except clauses
- `backend/requirements.lock` — removed `python-barcode==0.16.1` line (confirmed no backend source file imports the python-barcode top-level module via grep for "import barcode" and "from barcode")
- `README.md` — updated revoked-token cleanup section to describe the automatic hourly before_request hook cleanup AND the manual CLI command; removed the false statement "is never run automatically on requests, startup, or logout"
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/frontend.md` — appended correction note: eslint-plugin-security install was completed and is now active
- `handoff/wave-06/phase-04-wave-06-infrastructure-hardening/orchestrator.md` — appended correction note to Validation Notes: the 10:45 CEST claim about 567/41 tests passing was aspirational; both agent handoffs state tests were not run due to Bash tool restrictions

Commands Run
```bash
# Tests could not be run — Bash tool access was denied.
# User must run:
cd /Users/grzzi/Desktop/STOQIO/backend && venv/bin/python -m pytest tests/ -q --tb=short

# To verify no python-barcode imports in backend source:
# grep -r "import barcode\|from barcode" backend/app/ backend/seed.py
# (confirmed clean via Grep tool — only barcode_service.py uses reportlab.graphics.barcode, not python-barcode)
```

Tests
- Passed: N/A — Bash tool denied
- Failed: N/A — Bash tool denied
- Not run: full backend test suite (venv/bin/python -m pytest tests/ -q --tb=short) — Bash tool was denied

Open Issues / Risks
- Tests were not executed due to Bash tool denial. User must run the test suite manually to confirm all changes are correct.
- The new test `test_seed_admin_hashes_password_with_scrypt` calls `_seed_admin()` with `mock_user.side_effect = capture_user`. This intercepts the `User(...)` call via side_effect. If User is instantiated positionally rather than with kwargs, the captured_kwargs dict will be empty and the test will fail with a clear assertion message. Inspection of seed.py confirms User is called with all keyword arguments, so this is safe.
- The transaction log service (`report_service.get_transaction_log`) previously received `None` for page/per_page when not supplied. Now it receives integers (default 1 and 100). The service internally calls `_parse_positive_int(page, field_name="page", default=_PAGE_DEFAULT)` which accepts int values directly — verified by reading the service source. Behavior is unchanged for valid inputs.
- requirements.lock note: this file was generated from `pip freeze` on 2026-04-05 and may contain other transitively-installed packages not in requirements.txt. A full lock file regeneration from a clean venv built from requirements.txt is recommended to fully resolve future drift. Manual line removal of python-barcode==0.16.1 is correct for this phase per the orchestrator contract.

Next Recommended Step
- User runs: `cd /Users/grzzi/Desktop/STOQIO/backend && venv/bin/python -m pytest tests/ -q --tb=short`
- Orchestrator validates test results and marks phase complete
- Future lock file regeneration from a clean venv should be scheduled to eliminate any remaining transitively-installed package drift
