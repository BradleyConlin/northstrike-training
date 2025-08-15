#!/usr/bin/env bash
set -euo pipefail
MLROOT="${MLROOT:-./mlflow_server}"         # backend (experiments)
ARTROOT="${ARTROOT:-./mlflow_artifacts}"    # artifacts live OUTSIDE the backend store
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"
mkdir -p "$MLROOT" "$ARTROOT"
exec mlflow server --host "$HOST" --port "$PORT" \
  --backend-store-uri "$MLROOT" \
  --default-artifact-root "$ARTROOT"
