#!/usr/bin/env bash

set -euo pipefail

trap 'echo "deploy.sh failed at line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

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
# Run npm security audit — fail deploy on high/critical findings (F-SEC-015).
# Low and moderate findings are informational only and do not block deploy.
echo "Running npm security audit..."
cd "$ROOT_DIR/frontend"
if command -v npm >/dev/null 2>&1; then
  npm audit --audit-level=high
  echo "npm audit passed (no high/critical vulnerabilities)."
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
else
  echo "systemctl not available; restart skipped."
fi
