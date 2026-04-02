# Backend Handoff - Phase 03 Wave 02 Croatian-First Localization

## 2026-03-27 17:42:20 CET

Status
- completed

Scope
- Added the missing backend localization catalog entries for `ORDER_LINE_REMOVED` and `ORDER_LINE_CLOSED` only.
- Verified by code trace that Orders and Receiving already forward service exceptions through the shared `api_error(...)` path, so no route or service contract changes were needed.
- Added focused backend regression coverage for localized order-line domain errors.

Docs Read
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md` (`F-033`)
- `stoqio_docs/11_UI_RECEIVING.md`
- `stoqio_docs/12_UI_ORDERS.md`
- `stoqio_docs/07_ARCHITECTURE.md` § 2
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `handoff/wave-02/phase-03-wave-02-croatian-first-localization/orchestrator.md`
- `backend/app/utils/i18n.py`
- `backend/app/utils/errors.py`
- `backend/app/api/orders/routes.py`
- `backend/app/api/receiving/routes.py`
- `backend/app/services/order_service.py`
- `backend/app/services/receiving_service.py`
- `backend/tests/test_i18n.py`
- `backend/tests/test_receiving.py`

Files Changed
- `backend/app/utils/i18n.py`
- `backend/tests/test_i18n.py`
- `handoff/wave-02/phase-03-wave-02-croatian-first-localization/backend.md`

Commands Run
```bash
rg -n "ORDER_LINE_(REMOVED|CLOSED)|api_error\\(" backend/app/utils/i18n.py backend/app/api/orders/routes.py backend/app/api/receiving/routes.py backend/app/services/order_service.py backend/app/services/receiving_service.py backend/tests/test_i18n.py backend/tests/test_receiving.py
sed -n '1,260p' backend/app/utils/i18n.py
sed -n '1,260p' backend/app/api/orders/routes.py
sed -n '1,260p' backend/app/api/receiving/routes.py
sed -n '1,380p' backend/tests/test_i18n.py
./venv/bin/pytest tests/test_i18n.py -q
```

Tests
- Passed: `./venv/bin/pytest tests/test_i18n.py -q` -> `23 passed in 1.61s`
- Failed: None

Open Issues / Risks
- None introduced by this backend-only localization change.

Next Recommended Step
- Frontend agent should continue the targeted Croatian-first login/setup/fatal-state copy sweep and keep using the shared connection-error baseline where the phase scope calls for it.
