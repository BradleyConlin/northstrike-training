#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5001
