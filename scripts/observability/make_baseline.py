#!/usr/bin/env python
from __future__ import annotations

import json
from pathlib import Path

CAND = [
    "artifacts/training/metrics.csv",
    "artifacts/perception_out/detections.csv",
    "artifacts/waypoint_run.csv",
]
OUT = Path("artifacts/drift/baseline.csv")
META = Path("artifacts/drift/baseline_meta.json")


def main():
    src = None
    for p in CAND:
        if Path(p).is_file():
            src = p
            break
    if not src:
        raise SystemExit("No candidate CSV found to snapshot.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # just copy bytes (small files)
    OUT.write_bytes(Path(src).read_bytes())
    META.write_text(json.dumps({"source": src}, indent=2))
    print(f"Baseline -> {OUT}  (from {src})")


if __name__ == "__main__":
    main()
