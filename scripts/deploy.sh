#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$ROOT_DIR"
git pull origin main

cd "$BACKEND_DIR"
python3 -m pip install -r requirements.txt

cd "$ROOT_DIR"
"$ROOT_DIR/scripts/build.sh"

if [ -f "$BACKEND_DIR/alembic.ini" ]; then
  cd "$BACKEND_DIR"
  alembic upgrade head
fi

if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl restart wms
else
  echo "systemctl not available; restart skipped."
fi
