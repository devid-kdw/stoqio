#!/usr/bin/env bash

set -euo pipefail

# Placeholders — will be populated after ROOT_DIR is resolved (before any mutating step)
PRE_DEPLOY_GIT_HEAD=""
PRE_DEPLOY_ALEMBIC_HEAD=""
PREDEPLOY_LOG=""

trap '
  echo "ERROR: deploy.sh failed at: $BASH_COMMAND" >&2
  echo "" >&2
  echo "Manual rollback instructions:" >&2
  echo "  Git:        git reset --hard '"'"'$PRE_DEPLOY_GIT_HEAD'"'"'" >&2
  echo "  Migrations: venv/bin/alembic downgrade '"'"'$PRE_DEPLOY_ALEMBIC_HEAD'"'"'" >&2
  echo "  WARNING:    Destructive migrations cannot be safely reversed. Review migration state before downgrading." >&2
  echo "  Service:    sudo systemctl status wms" >&2
  echo "  Pre-deploy state saved to: $PREDEPLOY_LOG" >&2
' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
BACKEND_VENV_DIR="${BACKEND_VENV_DIR:-$BACKEND_DIR/venv}"
BACKEND_PYTHON="${BACKEND_PYTHON:-$BACKEND_VENV_DIR/bin/python}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command git

if [ ! -x "$BACKEND_PYTHON" ]; then
  echo "Expected backend virtualenv Python at: $BACKEND_PYTHON" >&2
  echo "Create backend/venv or set BACKEND_PYTHON to a valid interpreter." >&2
  exit 1
fi

cd "$ROOT_DIR"

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

echo "Updating repository from ${GIT_REMOTE}/${GIT_BRANCH}..."
git pull --ff-only "$GIT_REMOTE" "$GIT_BRANCH"

cd "$BACKEND_DIR"
# Install from the pinned lock file rather than the version-ranged requirements.txt
# so that production deploys are fully reproducible.
# IMPORTANT: Regenerate requirements.lock and commit it whenever backend
# dependencies change (see the comment block at the top of requirements.lock).
if [ ! -f "$BACKEND_DIR/requirements.lock" ]; then
  echo "Missing backend/requirements.lock; refusing non-reproducible deploy." >&2
  echo "Regenerate and commit requirements.lock whenever backend dependencies change." >&2
  exit 1
fi
echo "Installing backend Python requirements from requirements.lock..."
"$BACKEND_PYTHON" -m pip install -r requirements.lock

cd "$ROOT_DIR"
# Run npm security audit — fail deploy on moderate/high/critical findings (F-SEC-015).
# Low findings are informational only and do not block deploy.
echo "Running npm security audit..."
cd "$ROOT_DIR/frontend"
if command -v npm >/dev/null 2>&1; then
  npm audit --audit-level=moderate
  echo "npm audit passed (no moderate/high/critical vulnerabilities)."
else
  echo "WARNING: npm not found; skipping npm audit." >&2
fi
cd "$ROOT_DIR"

echo "Building frontend assets..."
"$ROOT_DIR/scripts/build.sh"

if [ -f "$BACKEND_DIR/alembic.ini" ]; then
  cd "$BACKEND_DIR"
  echo "Applying backend migrations..."
  PYTHONPATH="$BACKEND_DIR${PYTHONPATH:+:$PYTHONPATH}" "$BACKEND_PYTHON" -m alembic upgrade head
else
  echo "Skipping Alembic upgrade: backend/alembic.ini not found."
fi

if command -v systemctl >/dev/null 2>&1; then
  echo "Restarting wms service..."
  sudo systemctl restart wms
  sleep 2
  if ! sudo systemctl is-active --quiet wms; then
      echo "ERROR: wms service failed to start. Check logs with: sudo journalctl -u wms -n 50"
      exit 1
  fi
  echo "Service wms is active and running."
else
  echo "systemctl not available; restart skipped."
fi
