## Phase Summary

Phase
- Wave 4 - Phase 3 - Export Sanitization and Printer Config Hardening

Objective
- Prevent Excel formula injection in XLSX exports and restrict label-printer target configuration to safe private-network printer destinations.
- This phase covers:
- `F-SEC-006` — Excel formula injection
- `F-SEC-007` — label-printer IP/port restriction

Status
- changes_requested

Scope
- Reviewed the delivered backend and testing handoffs for Wave 4 Phase 3.
- Compared the claimed contracts against the actual repo worktree and the runtime settings/export behavior.
- Re-ran the claimed automated verification and added a targeted barcode-settings smoke to validate the RFC 1918 restriction at the real API save path.
- Created this `orchestrator.md` because the phase folder was missing the required orchestrator handoff file.

Docs Read
- `handoff/README.md`
- `handoff/wave-04/phase-03-wave-04-export-sanitization-and-printer-config-hardening/backend.md`
- `handoff/wave-04/phase-03-wave-04-export-sanitization-and-printer-config-hardening/testing.md`
- `backend/app/services/report_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/utils/validators.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_settings.py`

Commands Run
```bash
git status --short
cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_settings.py -q
python3 - <<'PY'
import ipaddress
for raw in ['127.0.0.1','169.254.1.1','10.0.0.1','172.20.5.50','192.168.1.1','8.8.8.8','100.64.0.1']:
    addr = ipaddress.IPv4Address(raw)
    print(raw, 'is_private=', addr.is_private)
PY
cd backend && venv/bin/python - <<'PY'
from tests.conftest import _TestConfig
from app import create_app
from app.extensions import db
from app.models.location import Location
from app.models.system_config import SystemConfig
from app.models.role_display_name import RoleDisplayName
from app.models.enums import UserRole
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app(config_override=_TestConfig)
with app.app_context():
    db.create_all()
    if db.session.get(Location, 1) is None:
        db.session.add(Location(id=1, name='Test', timezone='UTC', is_active=True))
    defaults = {
        'default_language': 'hr',
        'barcode_format': 'Code128',
        'barcode_printer': '',
        'export_format': 'generic',
        'label_printer_ip': '',
        'label_printer_port': '9100',
        'label_printer_model': 'zebra_zpl',
    }
    for key, value in defaults.items():
        row = SystemConfig.query.filter_by(key=key).first()
        if row is None:
            db.session.add(SystemConfig(key=key, value=value))
        else:
            row.value = value
    for role, label in {
        UserRole.ADMIN: 'Admin',
        UserRole.MANAGER: 'Menadzment',
        UserRole.WAREHOUSE_STAFF: 'Administracija',
        UserRole.VIEWER: 'Kontrola',
        UserRole.OPERATOR: 'Operater',
    }.items():
        row = RoleDisplayName.query.filter_by(role=role).first()
        if row is None:
            db.session.add(RoleDisplayName(role=role, display_name=label))
    admin = User.query.filter_by(username='phase3_admin').first()
    if admin is None:
        db.session.add(User(username='phase3_admin', password_hash=generate_password_hash('pass', method='pbkdf2:sha256'), role=UserRole.ADMIN, is_active=True))
    db.session.commit()

client = app.test_client()
login = client.post('/api/v1/auth/login', json={'username':'phase3_admin','password':'pass'}, environ_base={'REMOTE_ADDR':'127.0.3.1'})
token = login.get_json()['access_token']
for ip in ['127.0.0.1', '169.254.1.1', '8.8.8.8', '192.168.1.25']:
    resp = client.put('/api/v1/settings/barcode', json={'barcode_format':'Code128','label_printer_ip':ip,'label_printer_port':9100}, headers={'Authorization': f'Bearer {token}'})
    print(ip, resp.status_code, resp.get_json())
PY
```

Findings
- High: The `F-SEC-007` implementation does not actually enforce the required RFC 1918-only restriction. [`backend/app/services/settings_service.py:861`](/Users/grzzi/Desktop/STOQIO/backend/app/services/settings_service.py#L861) validates non-empty printer IPs with `ipaddress.IPv4Address(...).is_private`, but on this runtime `is_private` also returns `True` for loopback and link-local addresses such as `127.0.0.1` and `169.254.1.1`. The real save-path smoke confirmed both values are currently accepted with `200`, even though the phase contract explicitly narrowed the allowed space to only `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`.
- Medium: The testing coverage did not lock the actual RFC 1918 boundary that the phase asked for. [`backend/tests/test_settings.py:1322`](/Users/grzzi/Desktop/STOQIO/backend/tests/test_settings.py#L1322) covers public IPs, hostnames, CIDR notation, IPv6, and valid private examples, but it does not include a negative assertion for loopback or link-local addresses. Because of that gap, the suite stays green while the backend still accepts non-RFC-1918 targets.
- Low: The phase folder was missing the required orchestrator handoff file entirely. `handoff/README.md` requires the orchestrator to create/update `orchestrator.md` before delegation and append review results after validation. This review file is being created now to restore the handoff trail, but the missing orchestrator artifact means the phase did not previously have a complete coordination record.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_settings.py -q` → `119 passed in 57.78s`
- `F-SEC-006` export sanitization appears correctly covered by the added helper tests and XLSX integration test; no regression was found in the export path review.
- `F-SEC-007` port allowlist behavior appears correct for the currently documented allowlist of `{9100}`.
- Blocked:
- Real barcode-settings save-path validation still accepts non-RFC-1918 addresses:
- `127.0.0.1` → `200`
- `169.254.1.1` → `200`
- `8.8.8.8` → `400`
- `192.168.1.25` → `200`
- Runtime proof of the root cause:
- `127.0.0.1 is_private= True`
- `169.254.1.1 is_private= True`

Next Action
- Return to Backend for a narrow follow-up:
- replace the broad `.is_private` check with explicit RFC 1918 network membership checks against `10.0.0.0/8`, `172.16.0.0/12`, and `192.168.0.0/16`
- keep blank-IP acceptance and the current port allowlist behavior unchanged
- Return to Testing for a narrow follow-up:
- add explicit rejection tests for at least one loopback address (`127.0.0.1`) and one link-local address (`169.254.1.1`) so the RFC 1918 contract is truly locked
- Wave 4 Phase 3 is not accepted yet. Re-review after the backend/testing follow-up lands.

## [2026-04-05 16:46 CEST] Orchestrator Follow-Up - Fixes Implemented and Phase Accepted

Status
- accepted

Scope
- Implemented the narrow backend and testing follow-up directly as orchestrator so the previously documented review blocker is now closed.
- This follow-up work was done by the orchestrator, not by the earlier backend/testing deliveries, so future agents should treat the earlier `backend.md` and `testing.md` entries as the pre-fix state for this phase.
- Tightened printer-IP validation from broad `IPv4Address.is_private` semantics to explicit RFC 1918 network membership.
- Strengthened the Phase 3 printer-validation tests so loopback and link-local addresses are explicitly rejected.
- Hardened the new printer-validation test block itself so it no longer depends on module-level cached auth tokens or trips the login rate limiter during the full suite.

Files Changed
- `backend/app/services/settings_service.py`
- `backend/tests/test_settings.py`
- `handoff/wave-04/phase-03-wave-04-export-sanitization-and-printer-config-hardening/orchestrator.md`

Commands Run
```bash
cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'TestLabelPrinterTargetRestriction'
cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_settings.py -q
cd backend && venv/bin/python - <<'PY'
from tests.conftest import _TestConfig
from app import create_app
from app.extensions import db
from app.models.location import Location
from app.models.system_config import SystemConfig
from app.models.role_display_name import RoleDisplayName
from app.models.enums import UserRole
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app(config_override=_TestConfig)
with app.app_context():
    db.create_all()
    if db.session.get(Location, 1) is None:
        db.session.add(Location(id=1, name='Test', timezone='UTC', is_active=True))
    defaults = {
        'default_language': 'hr',
        'barcode_format': 'Code128',
        'barcode_printer': '',
        'export_format': 'generic',
        'label_printer_ip': '',
        'label_printer_port': '9100',
        'label_printer_model': 'zebra_zpl',
    }
    for key, value in defaults.items():
        row = SystemConfig.query.filter_by(key=key).first()
        if row is None:
            db.session.add(SystemConfig(key=key, value=value))
        else:
            row.value = value
    for role, label in {
        UserRole.ADMIN: 'Admin',
        UserRole.MANAGER: 'Menadzment',
        UserRole.WAREHOUSE_STAFF: 'Administracija',
        UserRole.VIEWER: 'Kontrola',
        UserRole.OPERATOR: 'Operater',
    }.items():
        row = RoleDisplayName.query.filter_by(role=role).first()
        if row is None:
            db.session.add(RoleDisplayName(role=role, display_name=label))
    admin = User.query.filter_by(username='phase3_admin').first()
    if admin is None:
        db.session.add(User(username='phase3_admin', password_hash=generate_password_hash('pass', method='pbkdf2:sha256'), role=UserRole.ADMIN, is_active=True))
    db.session.commit()

client = app.test_client()
login = client.post('/api/v1/auth/login', json={'username':'phase3_admin','password':'pass'}, environ_base={'REMOTE_ADDR':'127.0.3.1'})
token = login.get_json()['access_token']
for ip in ['127.0.0.1', '169.254.1.1', '8.8.8.8', '192.168.1.25']:
    resp = client.put('/api/v1/settings/barcode', json={'barcode_format':'Code128','label_printer_ip':ip,'label_printer_port':9100}, headers={'Authorization': f'Bearer {token}'})
    print(ip, resp.status_code, resp.get_json())
PY
```

Findings
- None. The previously documented RFC 1918 gap is resolved.

Validation Result
- Passed:
- `cd backend && venv/bin/python -m pytest tests/test_settings.py -q -k 'TestLabelPrinterTargetRestriction'` → `13 passed, 59 deselected in 12.83s`
- `cd backend && venv/bin/python -m pytest tests/test_reports.py tests/test_settings.py -q` → `121 passed in 64.45s`
- Manual barcode-settings smoke now behaves correctly:
- `127.0.0.1` → `400`
- `169.254.1.1` → `400`
- `8.8.8.8` → `400`
- `192.168.1.25` → `200`

Accepted Baseline After Follow-Up
- `F-SEC-006` remains accepted from the earlier Phase 3 implementation:
- shared `sanitize_cell(...)` helper exists
- user-controlled XLSX text cells are sanitized
- the export tests still prove machine-generated quantity strings are not blanket-mutated
- `F-SEC-007` is now fully closed:
- non-empty `label_printer_ip` must be a literal IPv4 address inside one of the explicit RFC 1918 networks only
- loopback and link-local addresses are rejected
- blank printer IP still represents the unconfigured state
- printer ports remain restricted through the named allowlist and `9100` is accepted
- the printer-validation test block now uses fresh per-test admin logins with distinct test IPs, so it is stable under the full suite and does not depend on earlier cached tokens

Next Action
- Wave 4 Phase 3 is complete.
- Future Wave 4 work should treat the accepted baseline as:
- XLSX export sanitization is active for user-controlled report cells
- label-printer settings accept only RFC 1918 IPv4 printer targets plus the configured allowlist port set
- loopback/link-local printer targets are considered regressions unless a future phase explicitly broadens scope
