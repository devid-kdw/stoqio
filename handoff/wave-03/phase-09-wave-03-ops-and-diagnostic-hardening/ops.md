## [2026-04-03 17:09 CEST] Ops DevOps Delivery

Status
- completed

Scope
- Hardened `scripts/build.sh` and `scripts/deploy.sh` for a more self-sufficient local-host deployment flow.
- Kept the accepted deployment model intact while making backend interpreter expectations and frontend dependency installation explicit.

Docs Read
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md`
- `README.md`
- `stoqio_docs/07_ARCHITECTURE.md`
- `stoqio_docs/stoqio_code_review CHATGPT vs CLAUDE.md`
- `scripts/build.sh`
- `scripts/deploy.sh`
- `frontend/package.json`
- `frontend/package-lock.json`

Files Changed
- `scripts/build.sh`
- `scripts/deploy.sh`
- `handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/ops.md`

Commands Run
```bash
date '+%Y-%m-%d %H:%M %Z'
git status --short
sed -n '1,260p' handoff/wave-03/phase-09-wave-03-ops-and-diagnostic-hardening/orchestrator.md
sed -n '1,240p' scripts/build.sh
sed -n '1,240p' scripts/deploy.sh
bash -n scripts/build.sh && bash -n scripts/deploy.sh
./scripts/build.sh
git diff -- scripts/build.sh scripts/deploy.sh
```

Tests
- Passed:
- `bash -n scripts/build.sh`
- `bash -n scripts/deploy.sh`
- `./scripts/build.sh`
- `build.sh` now performs a lockfile-aware frontend install via `npm ci --include=dev --no-audit --no-fund` before building.
- `deploy.sh` now requires an explicit backend Python interpreter path, defaulting to `backend/venv/bin/python`.
- Failed:
- None.
- Not run:
- A real `./scripts/deploy.sh` execution was intentionally not run because it performs `git pull` and service restart side effects.

Open Issues / Risks
- `deploy.sh` still depends on a working local backend virtualenv or an explicit `BACKEND_PYTHON` override, which is intentional but means operators must prepare the interpreter path before deploy.
- A host-level end-to-end deploy/restart smoke still needs a real local server because this workspace should not restart services.

Next Recommended Step
- Documentation agent should align README / architecture deployment instructions with the hardened script behavior.
