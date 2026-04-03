#!/usr/bin/env bash

set -euo pipefail

trap 'echo "build.sh failed at line ${LINENO}: ${BASH_COMMAND}" >&2' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_STATIC_DIR="$ROOT_DIR/backend/static"
PACKAGE_LOCK="$FRONTEND_DIR/package-lock.json"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_file() {
  if [ ! -f "$1" ]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

require_command npm
require_file "$PACKAGE_LOCK"

cd "$FRONTEND_DIR"
echo "Installing frontend dependencies from package-lock.json..."
npm ci --include=dev --no-audit --no-fund

echo "Building frontend..."
npm run build

mkdir -p "$BACKEND_STATIC_DIR"
rm -rf "${BACKEND_STATIC_DIR:?}/"*
cp -R dist/. "$BACKEND_STATIC_DIR"/

echo "Frontend build copied to backend/static."
