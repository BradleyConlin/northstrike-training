#!/usr/bin/env bash
set -euo pipefail
ALT="${ALT:-6}"          # meters
HOLD="${HOLD:-8}"        # seconds
HZ="${HZ:-20}"           # telemetry rate
CSV_DIR="datasets/flight_logs"
TS="$(date +%Y%m%d_%H%M%S)"
CSV="${CSV_DIR}/hover_${TS}.csv"

mkdir -p "${CSV_DIR}"

# 1) start recorder in background
python3 scripts/logging/mavsdk_telemetry_record.py --out "${CSV}" --hz "${HZ}" &
REC_PID=$!

# 2) run the SDK takeoff/hover/land
python3 scripts/control/mavsdk_takeoff_land.py --alt "${ALT}" --hold "${HOLD}"

# 3) stop recorder (gracefully)
sleep 2
kill -INT "${REC_PID}" || true
wait "${REC_PID}" || true

# 4) compute KPIs + log to MLflow (writes HTML into benchmarks/reports/hover_*)
python3 scripts/evaluation/hover_kpi_report.py --csv "${CSV}"
