#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_STATIC_DIR="$ROOT_DIR/backend/static"

cd "$FRONTEND_DIR"
npm run build

mkdir -p "$BACKEND_STATIC_DIR"
rm -rf "${BACKEND_STATIC_DIR:?}/"*
cp -R dist/. "$BACKEND_STATIC_DIR"/

echo "Frontend build copied to backend/static."
