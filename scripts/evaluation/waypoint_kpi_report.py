#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

try:
    import mlflow
except Exception:
    mlflow = None  # optional for --help/import in CI
import pandas as pd

try:
    from mlflow.tracking import MlflowClient  # type: ignore
except Exception:
    MlflowClient = None  # type: ignore


def _set_mlflow() -> None:
    uri = os.environ.get("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    mlflow.set_tracking_uri(uri)
    try:
        MlflowClient().search_experiments()
        print(f"🛰️  MLflow tracking at {uri}")
    except Exception:
        print("⚠️  MLflow server unreachable; logging to local ./mlflow_local")
        mlflow.set_tracking_uri("file:./mlflow_local")
        print("🛰️  MLflow tracking at file:./mlflow_local")


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _github_base() -> str | None:
    try:
        url = subprocess.check_output(["git", "config", "remote.origin.url"], text=True).strip()
        if url.startswith("git@github.com:"):
            userrepo = url.split(":", 1)[1].removesuffix(".git")
            return f"https://github.com/{userrepo}"
        if url.startswith("https://github.com/"):
            return url.removesuffix(".git")
    except Exception:
        pass
    return None


def _great_circle_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_plan(path: Path) -> List[Tuple[float, float, float]]:
    plan = json.loads(path.read_text())
    items = plan.get("mission", {}).get("items", [])
    wps: List[Tuple[float, float, float]] = []
    for it in items:
        if int(it.get("command", 16)) != 16:  # MAV_CMD_NAV_WAYPOINT
            continue
        p = it.get("params", [])
        if len(p) >= 7:
            lat, lon, alt = float(p[4]), float(p[5]), float(p[6])
            wps.append((lat, lon, alt))
    if not wps:
        raise ValueError("No waypoints in plan.")
    return wps


def compute_kpis(df: pd.DataFrame, wps: List[Tuple[float, float, float]]) -> dict:
    if any(col not in df.columns for col in ["lat", "lon"]):
        raise ValueError("CSV must contain lat/lon")
    errs = []
    for _, r in df.iterrows():
        dmins = [_great_circle_m(r.lat, r.lon, lat, lon) for (lat, lon, _alt) in wps]
        errs.append(min(dmins))
    visited = sum(1 for e in errs if e < 5.0)  # within 5 m
    s = pd.Series(errs, dtype=float)
    return {
        "visited": int(visited),
        "total": int(len(wps)),
        "mean_err_m": float(s.mean()),
        "max_err_m": float(s.max()),
    }


def render_html(outdir: Path, csv_path: Path, kpis: dict) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    html_path = outdir / "mission_report.html"

    sha = _git_sha()
    base = _github_base()
    commit_link = f"{base}/commit/{sha}" if base else None
    csv_link = f"{base}/blob/{sha}/{csv_path}" if base else None
    local_csv = f"file://{csv_path.resolve()}"

    meta = f"""
    <p>
      <b>CSV:</b> <a href="{local_csv}">{csv_path}</a>
      &nbsp;|&nbsp; <b>Commit:</b> {('<a href="%s">%s</a>' % (commit_link, sha[:7])) if commit_link else sha}
      {('&nbsp;|&nbsp; <a href="%s">view CSV @ commit</a>' % csv_link) if csv_link else ''}
    </p>
    """

    body = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Mission KPIs</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }}
    code, pre {{ background: #f6f8fa; padding: 2px 6px; border-radius: 4px; }}
    .kpi {{ font-size: 18px; margin: 8px 0; }}
  </style>
</head>
<body>
  <h1>Mission KPIs</h1>
  {meta}
  <div class="kpi">Visited: <b>{kpis['visited']}/{kpis['total']}</b></div>
  <div class="kpi">Mean error: <b>{kpis['mean_err_m']:.2f} m</b></div>
  <div class="kpi">Max error: <b>{kpis['max_err_m']:.2f} m</b></div>
</body>
</html>
"""
    html_path.write_text(body)
    return html_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--experiment", type=str, default="kpi-mission")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    wps = load_plan(args.plan)
    kpis = compute_kpis(df, wps)

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = args.outdir or Path(f"benchmarks/reports/mission_{ts}")
    html_path = render_html(outdir, args.csv, kpis)

    _set_mlflow()
    mlflow.set_experiment(args.experiment)
    with mlflow.start_run(run_name=f"mission_{ts}") as run:
        mlflow.log_params({"schema_version": "1.0"})
        mlflow.log_metrics(
            {
                "visited": kpis["visited"],
                "mean_err_m": kpis["mean_err_m"],
                "max_err_m": kpis["max_err_m"],
            }
        )
        mlflow.log_artifact(str(html_path), artifact_path="report")
        print(
            f"🏃 View run {run.info.run_name} at: {mlflow.get_tracking_uri()}"
            f"/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id}"
        )
        print(
            f"🧪 View experiment at: {mlflow.get_tracking_uri()}/#/experiments/{run.info.experiment_id}"
        )
        print(
            f"✅ KPIs: visited {kpis['visited']}/{kpis['total']}, "
            f"mean_err={kpis['mean_err_m']:.2f} m, max_err={kpis['max_err_m']:.2f} m"
        )
        print(f"🧾 Report: {html_path}")


if __name__ == "__main__":
    main()
