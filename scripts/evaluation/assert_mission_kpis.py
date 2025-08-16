#!/usr/bin/env python3
"""
Assert basic mission KPIs against a QGC .plan.

Checks:
- How many waypoints were "visited" within a radius.
- Mean & max nearest-distance from flight track to waypoints.

Exit status:
- 0 on PASS, 1 on FAIL.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    r = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def load_plan(plan_path: Path) -> list[tuple[float, float]]:
    """Return [(lat, lon), ...] from a QGC .plan file."""
    data = json.loads(Path(plan_path).read_text())
    items = data.get("mission", {}).get("items", [])
    wps: list[tuple[float, float]] = []
    for it in items:
        coord = it.get("coordinate")
        if isinstance(coord, list) and len(coord) >= 2:
            try:
                lat = float(coord[0])
                lon = float(coord[1])
            except Exception:
                continue
            wps.append((lat, lon))
    if not wps:
        raise ValueError("No waypoints found in plan.")
    return wps


def compute_kpis(
    df: pd.DataFrame,
    waypoints: list[tuple[float, float]],
    visit_radius_m: float,
) -> dict:
    """Nearest-distance KPIs to each waypoint."""
    # Prefer in-air samples if present; fall back safely.
    if "in_air" in df.columns:
        dfi = df[df["in_air"] == 1].copy()
        if dfi.empty:
            dfi = df.copy()
    else:
        dfi = df.copy()

    dfi = dfi.dropna(subset=["lat", "lon"])
    if dfi.empty:
        raise ValueError("No valid lat/lon samples in CSV.")

    lats = dfi["lat"].to_numpy()
    lons = dfi["lon"].to_numpy()

    dists = []
    for lat_wp, lon_wp in waypoints:
        dmin = min(haversine_m(lat_wp, lon_wp, lat, lon) for lat, lon in zip(lats, lons))
        dists.append(dmin)

    visited = sum(d <= visit_radius_m for d in dists)
    mean_err = float(sum(dists) / len(dists))
    max_err = float(max(dists))

    return {
        "visited": visited,
        "total": len(waypoints),
        "mean_err": mean_err,
        "max_err": max_err,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="mission CSV from recorder")
    ap.add_argument("--plan", required=True, help="QGC .plan file")
    ap.add_argument("--require-visited", type=int, default=5)
    ap.add_argument("--visit-radius", type=float, default=15.0)
    ap.add_argument("--max-mean", type=float, default=12.0)
    ap.add_argument("--max-max", type=float, default=25.0)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    waypoints = load_plan(Path(args.plan))
    k = compute_kpis(df, waypoints, args.visit_radius)

    print(
        "✅ KPIs: visited {}/{}, mean_err={:.2f} m, max_err={:.2f} m".format(
            k["visited"], k["total"], k["mean_err"], k["max_err"]
        )
    )

    ok = (
        k["visited"] >= args.require_visited
        and k["mean_err"] <= args.max_mean
        and k["max_err"] <= args.max_max
    )
    if not ok:
        print("❌ mission thresholds FAIL")
        sys.exit(1)

    print("🎯 mission thresholds PASS")


if __name__ == "__main__":
    main()
