#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

import mlflow
from mlflow.tracking import MlflowClient


# ---------- utils ----------
def _set_mlflow() -> None:
    """Use server from env or fall back to local file store."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    try:
        mlflow.set_tracking_uri(uri)
        MlflowClient().search_experiments()  # smoke test
        print(f"🛰️  MLflow tracking at {uri}")
    except Exception:
        mlflow.set_tracking_uri("file:./mlflow_local")
        print("⚠️  MLflow server unreachable; logging to local ./mlruns")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters."""
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------- .plan parsing (supports coordinate[] and params[4..6]) ----------
def load_plan(plan_path: Path) -> List[Tuple[float, float, float]]:
    data = json.loads(plan_path.read_text())
    items = data.get("mission", {}).get("items", [])
    wps: List[Tuple[float, float, float]] = []

    for it in items:
        if not isinstance(it, dict):
            continue

        coord = it.get("coordinate")
        if isinstance(coord, list) and len(coord) >= 3:
            lat, lon, alt = coord[:3]
            wps.append((float(lat), float(lon), float(alt)))
            continue

        params = it.get("params")
        if isinstance(params, list) and len(params) >= 7:
            lat, lon, alt = params[4], params[5], params[6]
            if None not in (lat, lon, alt):
                wps.append((float(lat), float(lon), float(alt)))
                continue

        lat = it.get("latitude") or it.get("Latitude") or it.get("param5")
        lon = it.get("longitude") or it.get("Longitude") or it.get("param6")
        alt = it.get("altitude") or it.get("Altitude") or it.get("param7")
        if all(v is not None for v in (lat, lon, alt)):
            wps.append((float(lat), float(lon), float(alt)))

    if not wps:
        raise ValueError("No waypoints in plan.")
    return wps


# ---------- CSV loader ----------
@dataclass
class Sample:
    t_s: float
    lat: float
    lon: float
    rel_alt_m: float


def load_track(csv_path: Path) -> List[Sample]:
    rows = []
    for line in csv_path.read_text().strip().splitlines()[1:]:
        t_s, lat, lon, alt, *_ = line.split(",")
        rows.append(
            Sample(
                t_s=float(t_s),
                lat=float(lat),
                lon=float(lon),
                rel_alt_m=float(alt),
            )
        )
    if not rows:
        raise ValueError("No samples in CSV.")
    return rows


# ---------- KPI computation ----------
@dataclass
class MissionKPI:
    total_wps: int
    visited_wps: int
    hit_radius_m: float
    min_err_m: float
    mean_err_m: float
    max_err_m: float


def compute_kpis(
    wps: Iterable[Tuple[float, float, float]],
    track: List[Sample],
    hit_radius_m: float = 8.0,
) -> MissionKPI:
    waypoints = list(wps)
    # min distance from each waypoint to any recorded sample (simple, robust)
    per_wp_min = []
    all_min_d = []  # min distance of each sample to nearest waypoint (for mean/RMS-ish)
    for s in track:
        nearest = min(haversine_m(s.lat, s.lon, lat, lon) for lat, lon, _ in waypoints)
        all_min_d.append(nearest)
    for lat, lon, _alt in waypoints:
        dmin = min(haversine_m(s.lat, s.lon, lat, lon) for s in track)
        per_wp_min.append(dmin)

    visited = sum(d <= hit_radius_m for d in per_wp_min)
    min_err = min(per_wp_min) if per_wp_min else float("nan")
    mean_err = sum(all_min_d) / len(all_min_d) if all_min_d else float("nan")
    max_err = max(all_min_d) if all_min_d else float("nan")
    return MissionKPI(
        total_wps=len(waypoints),
        visited_wps=visited,
        hit_radius_m=hit_radius_m,
        min_err_m=min_err,
        mean_err_m=mean_err,
        max_err_m=max_err,
    )


# ---------- HTML report ----------
def write_report(out_dir: Path, k: MissionKPI, csv_path: Path, plan_path: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Mission KPI</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:24px}}
.card{{border:1px solid #ddd;border-radius:12px;padding:16px;max-width:760px}}
.kv{{display:grid;grid-template-columns:220px 1fr;row-gap:8px}}
.kv div:first-child{{color:#666}}
code{{background:#f6f8fa;padding:2px 6px;border-radius:6px}}
</style></head>
<body>
<h2>Mission KPI Report</h2>
<div class="card">
  <div class="kv">
    <div>Plan</div><div><code>{plan_path}</code></div>
    <div>Track CSV</div><div><code>{csv_path}</code></div>
    <div>Total waypoints</div><div>{k.total_wps}</div>
    <div>Visited within {k.hit_radius_m:.1f} m</div><div>{k.visited_wps} / {k.total_wps}</div>
    <div>Min lateral error (m)</div><div>{k.min_err_m:.2f}</div>
    <div>Mean lateral error (m)</div><div>{k.mean_err_m:.2f}</div>
    <div>Max lateral error (m)</div><div>{k.max_err_m:.2f}</div>
  </div>
</div>
</body></html>
"""
    out_file = out_dir / "mission_report.html"
    out_file.write_text(html)
    return out_file


# ---------- main ----------
def main() -> None:
    ap = ArgumentParser()
    ap.add_argument(
        "--csv",
        type=Path,
        default=Path("datasets/flight_logs/mission_latest.csv"),
        help="Mission CSV (defaults to symlink mission_latest.csv)",
    )
    ap.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="QGC .plan file",
    )
    ap.add_argument(
        "--radius",
        type=float,
        default=8.0,
        help="Waypoint hit radius (meters)",
    )
    args = ap.parse_args()

    # resolve symlink to get run timestamp for the report folder name
    csv_path = args.csv
    try:
        real_csv = csv_path.resolve(strict=True)
    except FileNotFoundError:
        raise SystemExit(f"CSV not found: {csv_path}")

    wps = load_plan(args.plan)
    track = load_track(real_csv)
    kpi = compute_kpis(wps, track, args.radius)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path("benchmarks/reports") / f"mission_{ts}"
    report = write_report(out_dir, kpi, real_csv, args.plan)

    # MLflow
    _set_mlflow()
    mlflow.set_experiment("kpi-mission")
    with mlflow.start_run(run_name=f"mission_{ts}"):
        mlflow.log_param("plan", str(args.plan))
        mlflow.log_param("hit_radius_m", args.radius)
        mlflow.log_metric("visited_wp", kpi.visited_wps)
        mlflow.log_metric("total_wp", kpi.total_wps)
        mlflow.log_metric("min_err_m", kpi.min_err_m)
        mlflow.log_metric("mean_err_m", kpi.mean_err_m)
        mlflow.log_metric("max_err_m", kpi.max_err_m)
        mlflow.log_artifact(str(report), artifact_path="report")

    print(
        f"✅ KPIs: visited {kpi.visited_wps}/{kpi.total_wps}, "
        f"mean_err={kpi.mean_err_m:.2f} m, max_err={kpi.max_err_m:.2f} m"
    )
    print(f"🧾 Report: {report}")


if __name__ == "__main__":
    main()
