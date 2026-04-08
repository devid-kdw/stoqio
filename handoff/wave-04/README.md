# Wave 4 Handoffs

This folder stores all Wave 4 phase handoff folders.

Use the existing `handoff/README.md` protocol and create one subfolder per phase in the format:

- `phase-NN-wave-04-*`

## Security Recap After Phase 5

Wave 4 closed the security review findings `F-SEC-001` through `F-SEC-015`.
Future agents should treat the following as the accepted baseline unless a
concrete regression is found.

- Phase 1 closed bootstrap/JWT/startup hardening: seed/admin bootstrap now uses a one-time random password printed only after a successful seed transaction, production startup fails fast on missing or weak JWT/database configuration, and README setup guidance matches the real first-run flow.
- Phase 2 closed session/password hardening: refresh tokens are invalidated after password change/reset, including the same-second edge case, and password minimum boundary coverage now uses true boundary values.
- Phase 3 closed export/printer hardening: XLSX exports sanitize user-controlled cells against formula injection, and label-printer targets are restricted to explicit RFC 1918 IPv4 networks with the accepted printer port allowlist.
- Phase 4 closed diagnostics/settings-shell hardening: `backend/diagnostic.py` is a local support-only tool, avoids credential/hash output, redacts password-bearing database URIs, and `/api/v1/settings/shell` uses the shared active-user authorization path.
- Phase 5 closed operational follow-through: login throttling is DB-backed with per-IP and per-username buckets, Flask responses include browser security headers, backend deploys use `backend/requirements.lock`, deploy hard-fails if the lock file is missing, `.gitignore` covers common secret-bearing artifacts, `/api/v1/setup/status` is authenticated, `npm audit --audit-level=high` is part of deploy, and Vite was updated to `7.3.2` so the audit passes with no high/critical findings.

Phase 6 should be treated primarily as post-deployment/ops validation, not as a
continuation of security remediation. Reopen Wave 4 remediation only if the
deployment smoke, production audit, or a concrete code review finds a new
regression against the accepted phase handoffs.
