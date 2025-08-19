from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def compute_kpis_df(df: pd.DataFrame) -> dict:
    required = ["t", "px", "py", "vx", "vy", "tx", "ty", "wp_index"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")

    # Tracking error vs current target
    err = np.hypot(df["tx"] - df["px"], df["ty"] - df["py"])

    # Sampling stats
    t = df["t"].to_numpy()
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 1.0
    sample_hz = 1.0 / dt if dt > 0 else float("nan")

    # Waypoint hits (count increments of wp_index)
    wp = df["wp_index"].astype(int).to_numpy()
    wp_prev = np.r_[-1, wp[:-1]]
    hit_mask = wp > wp_prev
    hits = int(hit_mask.sum())
    first_hit_s = float(t[hit_mask][0]) if hits > 0 else None
    last_hit_s = float(t[hit_mask][-1]) if hits > 0 else None

    speed = np.hypot(df["vx"], df["vy"]).to_numpy()

    k = {
        "avg_err": float(err.mean()),
        "med_err": float(np.median(err)),
        "rms_err": float(np.sqrt((err**2).mean())),
        "max_err": float(err.max()),
        "hits": hits,
        "first_hit_s": first_hit_s,
        "last_hit_s": last_hit_s,
        "duration_s": float(t[-1] - t[0]) if len(t) else 0.0,
        "sample_hz": sample_hz,
        "final_wp_index": int(wp.max()) if len(wp) else -1,
        "max_speed": float(speed.max()) if len(speed) else 0.0,
    }

    # Simple traffic-light rating on average error
    k["rating"] = "green" if k["avg_err"] < 0.30 else ("yellow" if k["avg_err"] < 0.60 else "red")
    return k


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compute KPIs from waypoint CSV logs.")
    ap.add_argument(
        "--csv", default="artifacts/waypoint_run.csv", help="Input CSV from a waypoint demo"
    )
    ap.add_argument(
        "--json-out", default="artifacts/waypoint_kpis.json", help="Where to write KPI JSON"
    )
    args = ap.parse_args(argv)

    df = pd.read_csv(args.csv)
    k = compute_kpis_df(df)

    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.json_out, "w") as f:
        json.dump(k, f, indent=2)

    # Human-readable summary
    print("Waypoint KPIs")
    print(f"- hits={k['hits']}  duration_s={k['duration_s']:.2f}  sample_hz={k['sample_hz']:.1f}")
    print(
        f"- avg_err={k['avg_err']:.3f}  med_err={k['med_err']:.3f}  "
        f"rms_err={k['rms_err']:.3f}  max_err={k['max_err']:.3f}"
    )
    print(f"- rating={k['rating']}")
    print(f"Wrote JSON: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
