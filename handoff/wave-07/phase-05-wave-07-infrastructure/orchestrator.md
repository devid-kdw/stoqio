## Phase Summary

Phase
- Wave 7 - Phase 5 - Infrastructure Hardening and CI/CD

Objective
- Remediate two infrastructure findings from the 2026-04-08 dual-agent code review:
  M-7 (deploy.sh has no real rollback path — pre-deploy state is not captured),
  N-3 (no CI/CD pipeline — no automated regression on push/PR).

Source Docs
- `handoff/README.md`
- `handoff/wave-07/README.md`
- `handoff/Findings/wave-06-post-hardening-code-review-findings.md` (M-7)
- `handoff/Findings/wave-06-second-opinion-review.md` (M-7, N-3)
- `handoff/decisions/decision-log.md`
- `scripts/deploy.sh`
- `backend/requirements.lock`
- `frontend/package.json`

Current Repo Reality
- `scripts/deploy.sh` has `set -euo pipefail` and a health check after service restart (added
  in Wave 6 Phase 4). However, no pre-deploy state is captured. If the deploy fails after
  `git pull` or `alembic upgrade`, there is no record of what revision or migration head was
  in place before the failure. An operator cannot roll back without this information.
- No `.github/workflows/` directory exists. There is no automated test run on push or PR.
  The wave-by-wave agent handoff process is the only quality gate. The L-5 verification conflict
  (orchestrator claimed tests passed, agents said they were not run) is structurally possible
  to recur without automated CI.

Contract Locks / Clarifications
- **M-7 deploy state capture**: At the top of the deploy, before any mutating step:
  1. Capture `PRE_DEPLOY_GIT_HEAD=$(git rev-parse HEAD)` and echo it
  2. Capture `PRE_DEPLOY_ALEMBIC_HEAD=$(venv/bin/alembic current 2>/dev/null | head -1)` and echo it
  3. Write both to a timestamped file in `/tmp/` for operator reference:
     `echo "PRE_DEPLOY_GIT_HEAD=$PRE_DEPLOY_GIT_HEAD" > /tmp/stoqio_predeploy_$(date +%Y%m%d_%H%M%S).txt`
  4. On deploy failure (via the existing trap), print clear rollback instructions:
     - For git: `git reset --hard $PRE_DEPLOY_GIT_HEAD`
     - For migrations: `alembic downgrade <PRE_DEPLOY_ALEMBIC_HEAD>` (with a WARNING that
       destructive migrations cannot be safely reversed)
     - For service: manual operator action required
  Do NOT implement automatic rollback — migration rollback is not safe to automate. The goal
  is to give the operator the information needed to roll back manually. Keep the shell simple.
  Do NOT add new dependencies, state machines, or lock files.
- **N-3 CI/CD pipeline**: Create `.github/workflows/ci.yml` with a minimal workflow:
  - Trigger: `push` to `main` and `pull_request` targeting `main`
  - Python job:
    - `actions/checkout@v4`
    - `actions/setup-python@v5` with Python 3.11
    - `pip install -r backend/requirements.lock`
    - `cd backend && python -m pytest tests/ -q --tb=short`
  - Frontend job (runs in parallel with python job):
    - `actions/checkout@v4`
    - `actions/setup-node@v4` with Node 20
    - `cd frontend && npm ci`
    - `cd frontend && npm run build`
    - `cd frontend && npm run lint`
  - No deployment automation — CI only (test + build + lint on push/PR)
  - Use `ubuntu-latest` as the runner
  - Give the workflow a clear name: "STOQIO CI"
  - Do NOT set up any secrets, deployment keys, or environment variables beyond what the
    tests need (tests use SQLite in-memory, so no DATABASE_URL is needed)
  - Do NOT add caching for now (keep it simple for a first CI pass)
- Do NOT change any application source files in this phase.

File Ownership (this phase only — do not touch other files)
- `scripts/deploy.sh`
- `.github/workflows/ci.yml` (new file)
- `handoff/wave-07/phase-05-wave-07-infrastructure/backend.md`

Delegation Plan
- Backend/Infra: update deploy.sh rollback info, create CI workflow, document

Acceptance Criteria
- `deploy.sh` captures and prints `PRE_DEPLOY_GIT_HEAD` and `PRE_DEPLOY_ALEMBIC_HEAD` before any mutating step
- `deploy.sh` trap prints clear manual rollback instructions referencing the captured head values
- `bash -n scripts/deploy.sh` passes (syntax check)
- `.github/workflows/ci.yml` exists and is valid YAML
- The workflow triggers on push and pull_request to main
- The workflow runs pytest and npm build/lint
- No application source files are changed

Validation Notes
- 2026-04-08: Orchestrator created Wave 7 Phase 5. Runs in parallel with Phases 1, 2, 3, 4.
- 2026-04-08: Phase 5 agent completed both fixes. deploy.sh syntax check: ✓ (bash -n). CI workflow .github/workflows/ci.yml created. Note: agent did not have Bash execution permission — orchestrator ran bash -n to verify syntax. GitHub Actions workflow cannot be validated locally; requires push to verify. Phase 5 closed.

Next Action
- Backend/infra agent implements. Can run simultaneously with Phases 1, 2, 3, 4.

---

## Delegation Prompt — Backend/Infrastructure Agent

You are the infrastructure hardening agent for Wave 7 Phase 5 of the STOQIO WMS project.

Read before coding:
- `handoff/README.md`
- `handoff/wave-07/phase-05-wave-07-infrastructure/orchestrator.md` (this file)
- `scripts/deploy.sh` (read fully)
- `backend/requirements.lock` (for Python version reference)
- `frontend/package.json` (for Node version reference)

Your fixes:

1. **M-7: Capture pre-deploy state in deploy.sh** (`scripts/deploy.sh`)
   Read the full script first to understand the current flow.
   Near the top of the script (after `set -euo pipefail` and the trap, but BEFORE the first
   mutating step like `git pull`), add:
   ```bash
   # Capture pre-deploy state for manual rollback reference
   PRE_DEPLOY_GIT_HEAD=$(git rev-parse HEAD)
   PRE_DEPLOY_ALEMBIC_HEAD=$(venv/bin/alembic current 2>/dev/null | head -1 || echo "unknown")
   PREDEPLOY_LOG="/tmp/stoqio_predeploy_$(date +%Y%m%d_%H%M%S).txt"
   {
     echo "PRE_DEPLOY_GIT_HEAD=$PRE_DEPLOY_GIT_HEAD"
     echo "PRE_DEPLOY_ALEMBIC_HEAD=$PRE_DEPLOY_ALEMBIC_HEAD"
     echo "DEPLOY_STARTED=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   } > "$PREDEPLOY_LOG"
   echo "Pre-deploy state saved to $PREDEPLOY_LOG"
   echo "  Git HEAD: $PRE_DEPLOY_GIT_HEAD"
   echo "  Alembic head: $PRE_DEPLOY_ALEMBIC_HEAD"
   ```
   Update the existing `trap` to include rollback instructions using the captured variables:
   ```bash
   trap '
     echo "ERROR: deploy.sh failed at: $BASH_COMMAND"
     echo ""
     echo "Manual rollback instructions:"
     echo "  Git:        git reset --hard '"'"'$PRE_DEPLOY_GIT_HEAD'"'"'"
     echo "  Migrations: venv/bin/alembic downgrade '"'"'$PRE_DEPLOY_ALEMBIC_HEAD'"'"'"
     echo "  WARNING:    Destructive migrations cannot be safely reversed. Review migration state before downgrading."
     echo "  Service:    sudo systemctl status wms"
     echo "  Pre-deploy state saved to: $PREDEPLOY_LOG"
   ' ERR
   ```
   Keep all existing deploy logic intact. Only add the state capture and update the trap.
   After editing, run `bash -n scripts/deploy.sh` to verify syntax.

2. **N-3: Create minimal CI workflow** (`.github/workflows/ci.yml`)
   Create the directory `.github/workflows/` if it doesn't exist.
   Create `.github/workflows/ci.yml` with the following content:
   ```yaml
   name: STOQIO CI

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     backend:
       name: Backend Tests
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: '3.11'
         - name: Install backend dependencies
           run: pip install -r backend/requirements.lock
         - name: Run backend tests
           run: cd backend && python -m pytest tests/ -q --tb=short

     frontend:
       name: Frontend Build and Lint
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with:
             node-version: '20'
         - name: Install frontend dependencies
           run: cd frontend && npm ci
         - name: Build frontend
           run: cd frontend && npm run build
         - name: Lint frontend
           run: cd frontend && npm run lint
   ```

After all fixes:
- Run: `bash -n scripts/deploy.sh` (syntax check only — do not run the deploy)
- Write your entry in `handoff/wave-07/phase-05-wave-07-infrastructure/backend.md`
  following the template in `handoff/templates/agent-handoff-template.md`
- Note in Open Issues / Risks: the GitHub Actions workflow requires the repo to be on GitHub
  and the workflow to be pushed — it cannot be verified locally by the agent.
