#!/usr/bin/env python
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from observability.drift_detection.drift_ks import compare_csvs

BASE = Path("artifacts/drift/baseline.csv")
ALERT = Path("artifacts/drift/last_drift.json")
LOG = Path("artifacts/drift/drift_log.csv")


def main(cur_csv: str, threshold: float = 0.20):
    if not BASE.is_file():
        raise SystemExit("Missing baseline. Run scripts/observability/make_baseline.py first.")
    p95, per_col = compare_csvs(str(BASE), cur_csv, max_p95=threshold)
    status = "ok" if p95 <= threshold else "drift"
    ALERT.parent.mkdir(parents=True, exist_ok=True)
    ALERT.write_text(
        json.dumps({"status": status, "p95": p95, "per_col": per_col, "current": cur_csv}, indent=2)
    )
    # append CSV log
    is_new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["current_csv", "p95", "status"])
        w.writerow([cur_csv, f"{p95:.4f}", status])
    print(json.dumps({"status": status, "p95": p95}))


if __name__ == "__main__":
    cur = sys.argv[1] if len(sys.argv) > 1 else "artifacts/training/metrics.csv"
    thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.20
    main(cur, thr)
