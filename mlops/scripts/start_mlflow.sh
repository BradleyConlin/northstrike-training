#!/usr/bin/env bash
set -euo pipefail
MLROOT="${MLROOT:-./mlruns}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"
mkdir -p "$MLROOT"
exec mlflow server --host "$HOST" --port "$PORT" \
  --backend-store-uri "$MLROOT" \
  --default-artifact-root "$MLROOT/artifacts"
