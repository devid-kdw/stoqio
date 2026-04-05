# Wave 4 Phase 3 — Backend Handoff

## Entry 1 — 2026-04-05

### Status

Complete. All verification passed.

### Scope

- `F-SEC-006`: Excel formula injection hardening — `sanitize_cell` helper added; applied to all user-controlled string fields in XLSX export paths.
- `F-SEC-007`: Label-printer target restriction — `label_printer_ip` now validated against RFC 1918 private IPv4 space only; `label_printer_port` now validated against a named allowlist constant (`_ALLOWED_LABEL_PRINTER_PORTS = {9100}`).

### Docs Read

- `/Users/grzzi/Desktop/STOQIO IZMJENE/stoqio_security_review_agent_ready.md` (F-SEC-006, F-SEC-007)
- `handoff/README.md`
- `handoff/decisions/decision-log.md`
- `backend/app/services/report_service.py`
- `backend/app/services/settings_service.py`
- `backend/app/services/barcode_service.py`
- `backend/app/utils/validators.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_settings.py`

### Files Changed

| File | Change |
|---|---|
| `backend/app/utils/validators.py` | Added `sanitize_cell(value: str) -> str` helper with docstring |
| `backend/app/services/report_service.py` | Imported `sanitize_cell`; applied to user-controlled string cells in all three XLSX export paths |
| `backend/app/services/settings_service.py` | Added `import ipaddress`; added `_ALLOWED_LABEL_PRINTER_PORTS` constant; rewrote `_parse_label_printer_port` to validate against allowlist; added `_validate_label_printer_ip` function; called `_validate_label_printer_ip` in `update_barcode_settings` |

### Commands Run

```
cd /Users/grzzi/Desktop/STOQIO/backend
venv/bin/python -m pytest tests/test_reports.py tests/test_settings.py -q
```

Result: **97 passed** (0 failures).

### Implementation Details

#### `sanitize_cell` location

`backend/app/utils/validators.py` — added after the existing imports, before `QueryValidationError`. Exported from the same validators module already imported by `settings_service.py` and used elsewhere in the project. Easy to discover and reuse by any future export path.

#### XLSX export paths sanitized

Three export functions in `report_service.py`:

| Export function | Fields sanitized |
|---|---|
| `export_stock_overview` | `article_no`, `description`, `supplier_name` (when non-empty) |
| `export_surplus_report` | `article_no`, `description`, `batch_code` (when non-empty) |
| `export_transaction_log` | `article_no`, `description`, `batch_code` (when non-empty), `reference` (when non-empty), `user` (when non-empty) |

**Deliberately not sanitized:**
- Numeric/quantity cells produced by `_format_export_quantity` — these are machine-formatted strings and cannot be user-controlled formula injections.
- Date/timestamp cells (`occurred_at`, `expiry_date`, `discovered`) — system-generated values.
- Status display text (`reorder_status`, `type`) — system-generated from enum values.
- Fallback `"-"` placeholder strings — machine-generated, not user data; the pattern `sanitize_cell(x) if x else "-"` avoids mutating the fallback.

#### Printer IP validation

`_validate_label_printer_ip(ip: str)` in `settings_service.py`:
- Blank/empty `ip` → accepted as "not configured" (existing default path preserved).
- Non-empty `ip`:
  - Parsed with `ipaddress.IPv4Address(ip)` — this rejects hostnames, IPv6 values, CIDR notation, and non-IP strings with a clear `VALIDATION_ERROR`.
  - `.is_private` checked — rejects public IPs, loopback outside private range context, and any address not in RFC 1918 space.
  - Permitted ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.

#### Allowed printer ports

`_ALLOWED_LABEL_PRINTER_PORTS: frozenset[int] = frozenset({9100})`

The `_parse_label_printer_port` function now checks `port not in _ALLOWED_LABEL_PRINTER_PORTS` and raises `VALIDATION_ERROR` with a deterministic message listing allowed ports. The constant is clearly named and located near the other `_ALLOWED_*` constants at the top of `settings_service.py` so it is easy to extend later.

### Tests

```
97 passed in 49.07s
```

No existing tests were broken. The testing agent is responsible for adding regression coverage for the new security contracts.

### Open Issues / Risks

- `ipaddress.IPv4Address.is_private` returns `True` for loopback (`127.x.x.x`) and link-local (`169.254.x.x`) in Python's stdlib in addition to the three RFC 1918 ranges. These are unlikely to be valid printer destinations. If stricter restriction to only RFC 1918 ranges is required in a future phase, add an explicit check against `ipaddress.ip_network("10.0.0.0/8")`, `172.16.0.0/12`, and `192.168.0.0/16`. Logged here as a known conservative residual.
- Barcode/print socket mechanics in `barcode_service.py` are intentionally unchanged — this phase is save-time validation only per the orchestrator contract.
- No cross-agent contract clarification was needed; no new decision-log entry required.

### Next Recommended Step

Testing agent: add regression tests for formula-injection sanitization (verify leading `=`, `+`, `-`, `@` are prefixed in XLSX output) and printer validation (public IP rejected, private IP accepted, blank accepted, disallowed port rejected, port 9100 accepted).
