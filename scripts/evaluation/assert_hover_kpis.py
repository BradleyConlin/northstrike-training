#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys

import pandas as pd


def deg_to_m_xy(lat0_deg: float, lat_deg, lon_deg):
    """Convert lat/lon (deg) to local meters around lat0_deg."""
    lat_m = (lat_deg - lat0_deg) * 111_320.0
    lon_m = (lon_deg - lon_deg.mean()) * (111_320.0 * math.cos(math.radians(lat0_deg)))
    return lat_m, lon_m


def compute_hover_kpis(df: pd.DataFrame) -> dict:
    dfi = df[df["in_air"] == 1].copy() if "in_air" in df.columns else df.copy()
    if dfi.empty:
        dfi = df.copy()
    alt_ref = float(dfi["rel_alt_m"].median())
    alt_err = dfi["rel_alt_m"] - alt_ref
    hover_rms = float((alt_err**2).mean() ** 0.5)
    hover_max = float(alt_err.abs().max())
    lat0 = float(dfi["lat"].median())
    lat_m, lon_m = deg_to_m_xy(lat0, dfi["lat"], dfi["lon"])
    r_xy = (lat_m**2 + lon_m**2) ** 0.5
    xy_rms = float((r_xy**2).mean() ** 0.5)
    xy_max = float(r_xy.max())
    return {
        "samples": int(len(dfi)),
        "alt_ref_m": round(alt_ref, 4),
        "hover_rms_m": round(hover_rms, 4),
        "hover_max_dev_m": round(hover_max, 4),
        "xy_rms_m": round(xy_rms, 4),
        "xy_max_m": round(xy_max, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="hover CSV (recorder output)")
    ap.add_argument("--min-samples", type=int, default=250)
    ap.add_argument("--max-hover-rms", type=float, default=1.6)
    ap.add_argument("--max-xy-rms", type=float, default=0.05)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    k = compute_hover_kpis(df)
    print("✅ KPIs:", k)

    failed = []
    if k["samples"] < args.min_samples:
        failed.append(f"samples {k['samples']} < {args.min_samples}")
    if k["hover_rms_m"] > args.max_hover_rms:
        failed.append(f"hover_rms_m {k['hover_rms_m']} > {args.max_hover_rms}")
    if k["xy_rms_m"] > args.max_xy_rms:
        failed.append(f"xy_rms_m {k['xy_rms_m']} > {args.max_xy_rms}")

    if failed:
        print("❌ hover thresholds FAILED:", "; ".join(failed))
        sys.exit(2)
    print("🎯 hover thresholds PASS")


if __name__ == "__main__":
    main()
