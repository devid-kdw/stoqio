## Phase Summary

Phase
- Wave 2 - Phase 8 - Direct Label Printer Support

Objective
- Add ADMIN-only direct label-printer support for article and batch barcodes while keeping the existing PDF barcode download flow intact.
- Store printer IP/port/model in Settings -> Barcode and keep the architecture open for future printer models.

Source Docs
- `stoqio_docs/13_UI_WAREHOUSE.md` § 7
- `stoqio_docs/18_UI_SETTINGS.md` § 8
- `stoqio_docs/05_DATA_MODEL.md`
- `stoqio_docs/02_DOMAIN_KNOWLEDGE.md` § 3
- `handoff/README.md`
- `handoff/decisions/decision-log.md`

Delegation Plan
- Backend:
- extend barcode settings persistence, add direct-print service/endpoint flow, add printer i18n messages, preserve PDF flow
- Frontend:
- extend Settings barcode UI, add ADMIN-only direct-print actions beside PDF fallback actions, keep printer-not-configured UX clear
- Testing:
- cover direct-print endpoints, ZPL generation, i18n additions, and barcode-settings round-trip

Acceptance Criteria
- ADMIN-only article and batch direct-print endpoints exist and return the locked success/error contracts
- Settings -> Barcode exposes and persists printer IP, port, and model
- Existing PDF barcode download flow remains unchanged
- Zebra ZPL generation exists and includes barcode, description, article code, and optional batch line
- Localized printer errors exist for `PRINTER_NOT_CONFIGURED`, `PRINTER_UNREACHABLE`, and `PRINTER_MODEL_UNKNOWN`
- Automated verification passes

## [2026-04-02 19:10 CEST] Orchestrator Validation - Phase Not Accepted Yet

Status
- changes requested

Scope
- Reviewed the backend, frontend, and testing deliveries for Wave 2 Phase 8.
- Re-ran targeted Phase 8 backend verification, frontend test/lint/build, and the full backend suite.
- Performed one direct reproduction of a suspected print-path edge case against the current backend implementation.

Docs Read
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/backend.md`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/frontend.md`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/testing.md`
- `backend/app/services/barcode_service.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/utils/i18n.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_barcode_service.py`
- `backend/tests/test_settings.py`
- `backend/tests/test_i18n.py`
- `frontend/src/api/articles.ts`
- `frontend/src/api/settings.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`

Files Reviewed
- `backend/app/services/barcode_service.py`
- `backend/app/api/articles/routes.py`
- `backend/app/services/settings_service.py`
- `backend/app/utils/i18n.py`
- `backend/seed.py`
- `backend/tests/test_articles.py`
- `backend/tests/test_barcode_service.py`
- `backend/tests/test_settings.py`
- `backend/tests/test_i18n.py`
- `frontend/src/api/articles.ts`
- `frontend/src/api/settings.ts`
- `frontend/src/pages/settings/SettingsPage.tsx`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/backend.md`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/frontend.md`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/testing.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_barcode_service.py tests/test_settings.py tests/test_i18n.py -q
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest -q
cd backend && venv/bin/python - <<'PY'
from unittest.mock import patch
from app import create_app
from app.extensions import db
from tests.conftest import _TestConfig
from app.models.article import Article
from app.models.category import Category
from app.models.uom_catalog import UomCatalog
from app.models.system_config import SystemConfig
from app.services import barcode_service

app = create_app(config_override=_TestConfig)
with app.app_context():
    db.create_all()
    cat = Category(key='cat', label_hr='Cat', label_en='Cat', is_personal_issue=False, is_active=True)
    uom = UomCatalog(code='kom', label_hr='kom', label_en='piece', decimal_display=False)
    db.session.add_all([cat, uom])
    db.session.flush()
    article = Article(
        article_no='ART-001',
        description='Test article',
        category_id=cat.id,
        base_uom=uom.id,
        has_batch=False,
        is_active=True,
        barcode='WHBAR001',
    )
    db.session.add(article)
    for key, value in [
        ('barcode_format', 'EAN-13'),
        ('barcode_printer', ''),
        ('label_printer_ip', '192.168.1.50'),
        ('label_printer_port', '9100'),
        ('label_printer_model', 'zebra_zpl'),
    ]:
        db.session.add(SystemConfig(key=key, value=value))
    db.session.commit()
    try:
        with patch('app.services.barcode_service._send_to_printer'):
            result = barcode_service.print_article_label(article.id)
        print('SUCCESS', result)
    except Exception as exc:
        print(type(exc).__name__, getattr(exc, 'error', None), getattr(exc, 'message', str(exc)), getattr(exc, 'status_code', None), getattr(exc, 'details', None))
PY
```

Verification Result
- `cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_barcode_service.py tests/test_settings.py tests/test_i18n.py -q` -> `132 passed`
- `cd frontend && CI=true npm run test` -> `5 files passed, 19 tests passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- `cd backend && venv/bin/python -m pytest -q` -> `437 passed`
- Direct reproduction of the current print path with:
- stored article barcode = `WHBAR001`
- `label_printer_model = zebra_zpl`
- `label_printer_ip = 192.168.1.50`
- `barcode_format = EAN-13`
- current backend result -> `BarcodeServiceError INVALID_BARCODE_VALUE Article barcode must contain 12 or 13 digits for EAN-13.`

Findings
- Blocking:
- Direct label printing is currently coupled to the PDF `barcode_format` setting in `backend/app/services/barcode_service.py` lines 443-450 and 472-479. That makes the supposedly ZPL/Code128 print path fail with `INVALID_BARCODE_VALUE` whenever global barcode settings are switched to `EAN-13` and an existing article/batch barcode is alphanumeric. The delegated Phase 8 contract explicitly says the ZPL label must print a Code128 barcode from the stored barcode value, so the direct-printer path must not depend on the PDF-format validation rules.
- Blocking:
- The frontend wraps both direct-print POST actions in `runWithRetry(...)` in `frontend/src/pages/warehouse/ArticleDetailPage.tsx` lines 452-455 and 514-516. `runWithRetry(...)` retries on network/5xx failures, which is unsafe for a non-idempotent printer side effect. A transient `502 PRINTER_UNREACHABLE` or transport error can cause an automatic second POST and duplicate printed labels if the first attempt partially or fully reached the printer.
- Medium:
- The delegated testing brief required the batch print endpoint to have the same unknown-model and unreachable coverage as the article print endpoint. Current backend route coverage in `backend/tests/test_articles.py` lines 1330-1369 only exercises those two failure modes for the article route; the batch route currently has coverage only for admin-only, not-configured, and success cases. The implementation may still be correct, but the promised parity coverage is not fully present.

Impact
- Phase 8 cannot yet be treated as an accepted baseline for direct label printing because one real runtime behavior contradicts the delegated contract and one frontend retry path introduces duplicate-print risk.

Residual Risks
- Manual real-printer verification was not run in this review session. Even after the blocking issues are fixed, an operator-side smoke test against an actual Zebra printer is still required before treating the phase as operationally validated.

Closeout Decision
- Wave 2 Phase 8 is not accepted yet.

Next Action
- Backend:
- decouple direct-print barcode resolution from the PDF `barcode_format` setting so the printer path always emits Code128 ZPL from the stored/generated barcode value
- Testing:
- add the missing batch-route parity tests for unknown-model and unreachable-printer behavior
- Frontend:
- remove automatic retry wrapping from the direct-print POST actions so label printing is single-shot

## [2026-04-02 19:18 CEST] Orchestrator Direct Fix + Final Validation

Status
- accepted

Scope
- Implemented the fixes for all findings from the earlier orchestrator review directly in the shared workspace.
- Re-ran targeted Phase 8 verification, rechecked the previously failing reproduction scenario, and re-ran the full backend suite after the fix.
- Recorded the direct-fix ownership here so future agents can see that the final accepted baseline differs slightly from the first agent-delivered implementation.

Files Changed By Orchestrator
- `backend/app/services/barcode_service.py`
- `backend/tests/test_articles.py`
- `frontend/src/pages/warehouse/ArticleDetailPage.tsx`
- `handoff/wave-02/phase-08-wave-02-direct-label-printer-support/orchestrator.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_barcode_service.py tests/test_settings.py tests/test_i18n.py -q
cd backend && venv/bin/python - <<'PY'
from unittest.mock import patch
from app import create_app
from app.extensions import db
from tests.conftest import _TestConfig
from app.models.article import Article
from app.models.category import Category
from app.models.uom_catalog import UomCatalog
from app.models.system_config import SystemConfig
from app.services import barcode_service

app = create_app(config_override=_TestConfig)
with app.app_context():
    db.create_all()
    cat = Category(key='cat2', label_hr='Cat', label_en='Cat', is_personal_issue=False, is_active=True)
    uom = UomCatalog(code='kom2', label_hr='kom', label_en='piece', decimal_display=False)
    db.session.add_all([cat, uom])
    db.session.flush()
    article = Article(article_no='ART-001', description='Test article', category_id=cat.id, base_uom=uom.id, has_batch=False, is_active=True, barcode='WHBAR001')
    db.session.add(article)
    for key, value in [
        ('barcode_format', 'EAN-13'),
        ('barcode_printer', ''),
        ('label_printer_ip', '192.168.1.50'),
        ('label_printer_port', '9100'),
        ('label_printer_model', 'zebra_zpl'),
    ]:
        db.session.add(SystemConfig(key=key, value=value))
    db.session.commit()
    with patch('app.services.barcode_service._send_to_printer'):
        result = barcode_service.print_article_label(article.id)
    print(result)
PY
cd frontend && CI=true npm run test
cd frontend && npm run lint -- --max-warnings=0
cd frontend && npm run build
cd backend && venv/bin/python -m pytest -q
```

Fixes Applied
- Closed blocking backend issue:
- direct-print barcode resolution no longer depends on the PDF `barcode_format` setting
- `print_article_label()` and `print_batch_label()` now use a dedicated direct-print resolution path in `backend/app/services/barcode_service.py` that reuses the stored barcode when present and only falls back to generated values when missing
- verified reproduction now succeeds with:
- `barcode_format = EAN-13`
- `label_printer_model = zebra_zpl`
- stored barcode `WHBAR001`
- Closed blocking frontend issue:
- direct-print requests in `frontend/src/pages/warehouse/ArticleDetailPage.tsx` no longer use `runWithRetry(...)`
- article and batch direct-print actions are now intentionally single-shot, with an inline code comment documenting why retry is unsafe for real printer side effects
- Closed testing gap:
- added missing batch-route parity coverage in `backend/tests/test_articles.py` for:
- `PRINTER_MODEL_UNKNOWN`
- `PRINTER_UNREACHABLE`
- added a focused regression test proving the article direct-print path stays valid even when the global PDF barcode setting is `EAN-13`

Verification Result
- `cd backend && venv/bin/python -m pytest tests/test_articles.py tests/test_barcode_service.py tests/test_settings.py tests/test_i18n.py -q` -> `135 passed`
- direct reproduction after fix -> `{'status': 'sent', 'printer_ip': '192.168.1.50', 'model': 'zebra_zpl'}`
- `cd frontend && CI=true npm run test` -> `5 files passed, 19 tests passed`
- `cd frontend && npm run lint -- --max-warnings=0` -> passed
- `cd frontend && npm run build` -> passed
- `cd backend && venv/bin/python -m pytest -q` -> `440 passed`

Closeout Decision
- Wave 2 Phase 8 is formally accepted.

Residual Risks
- Manual real-printer validation is still outstanding. The accepted software baseline now matches the delegated contract, but Zebra hardware/layout confirmation on the actual label stock remains an operator-side smoke test.

Next Action
- Treat the current worktree as the accepted Phase 8 baseline.
- Future agents should preserve the explicit “single-shot” direct-print behavior and should not re-couple direct printer output to the PDF `barcode_format` rules.
