#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path
from typing import Tuple

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd


def latlon_to_meters(lat: np.ndarray, lon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Convert lat/lon deltas to local meters using equirectangular approximation."""
    lat0 = float(lat[0])
    lon0 = float(lon[0])
    k_lat = 111_320.0  # meters per deg latitude
    k_lon = 111_320.0 * math.cos(math.radians(lat0))
    dx = (lon - lon0) * k_lon
    dy = (lat - lat0) * k_lat
    return dx, dy


def compute_hover_kpis(df: pd.DataFrame) -> dict:
    """Compute basic hover KPIs from telemetry dataframe."""
    dfi = df[df.get("in_air", 1) == 1].copy()
    if len(dfi) == 0:
        dfi = df.copy()

    # Altitude error vs median (robust to brief takeoff/landing)
    rel_alt = dfi["rel_alt_m"].to_numpy(dtype=float)
    alt_ref = float(np.median(rel_alt))
    alt_err = rel_alt - alt_ref
    hover_rms_m = float(np.sqrt(np.mean(alt_err**2)))
    hover_max_dev_m = float(np.max(np.abs(alt_err)))

    # XY drift
    lat = dfi["lat"].to_numpy(dtype=float)
    lon = dfi["lon"].to_numpy(dtype=float)
    dx, dy = latlon_to_meters(lat, lon)
    r = np.sqrt(dx**2 + dy**2)
    xy_rms_m = float(np.sqrt(np.mean(r**2)))
    xy_max_m = float(np.max(r))

    return {
        "samples": int(len(dfi)),
        "alt_ref_m": alt_ref,
        "hover_rms_m": hover_rms_m,
        "hover_max_dev_m": hover_max_dev_m,
        "xy_rms_m": xy_rms_m,
        "xy_max_m": xy_max_m,
    }


def make_plots(df: pd.DataFrame, outdir: Path, alt_ref_m: float) -> Tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    # Altitude vs time
    fig1 = plt.figure()
    t = df["t"].to_numpy(dtype=float)
    alt = df["rel_alt_m"].to_numpy(dtype=float)
    plt.plot(t, alt, label="rel_alt_m")
    plt.axhline(alt_ref_m, linestyle="--", label="ref (median)")
    plt.xlabel("time [s]")
    plt.ylabel("altitude [m]")
    plt.title("Altitude over time")
    plt.legend()
    p1 = outdir / "altitude_over_time.png"
    fig1.tight_layout()
    fig1.savefig(p1, dpi=120)
    plt.close(fig1)

    # XY drift scatter
    fig2 = plt.figure()
    dx, dy = latlon_to_meters(df["lat"].to_numpy(), df["lon"].to_numpy())
    plt.plot(dx, dy, ".", markersize=2)
    plt.xlabel("east [m]")
    plt.ylabel("north [m]")
    plt.title("XY drift (ENU approx)")
    plt.axis("equal")
    p2 = outdir / "xy_drift.png"
    fig2.tight_layout()
    fig2.savefig(p2, dpi=120)
    plt.close(fig2)

    return p1, p2


def write_html(outdir: Path, kpis: dict, p1: Path, p2: Path) -> Path:
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Hover KPI Report</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;margin:24px;}}
table{{border-collapse:collapse;margin-bottom:16px;}}
td,th{{border:1px solid #ccc;padding:6px 10px;text-align:left;}}
img{{max-width:48%;}}
</style></head><body>
<h2>Hover KPI Report</h2>
<table>
<tr><th>Samples</th><td>{kpis['samples']}</td></tr>
<tr><th>Altitude ref (m)</th><td>{kpis['alt_ref_m']:.2f}</td></tr>
<tr><th>Altitude RMS (m)</th><td>{kpis['hover_rms_m']:.3f}</td></tr>
<tr><th>Altitude max dev (m)</th><td>{kpis['hover_max_dev_m']:.3f}</td></tr>
<tr><th>XY RMS (m)</th><td>{kpis['xy_rms_m']:.3f}</td></tr>
<tr><th>XY max (m)</th><td>{kpis['xy_max_m']:.3f}</td></tr>
</table>
<div>
  <img src="{p1.name}" alt="Altitude over time">
  <img src="{p2.name}" alt="XY drift">
</div>
</body></html>"""
    out = outdir / "hover_report.html"
    out.write_text(html, encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Telemetry CSV (from recorder)")
    ap.add_argument(
        "--outdir", default=None, help="Output directory (defaults under benchmarks/reports)"
    )
    ap.add_argument("--experiment", default="kpi-hover", help="MLflow experiment name")
    args = ap.parse_args()

    csv_path = Path(args.csv)
    df = pd.read_csv(csv_path)
    kpis = compute_hover_kpis(df)

    # Output directory
    ts = time.strftime("%Y%m%d_%H%M%S")
    outdir = Path(args.outdir) if args.outdir else Path("benchmarks/reports") / f"hover_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    # Plots + HTML
    p1, p2 = make_plots(df, outdir, kpis["alt_ref_m"])
    html = write_html(outdir, kpis, p1, p2)

    # Log to MLflow
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment(args.experiment)
    with mlflow.start_run(run_name=f"hover_{ts}"):
        mlflow.log_params({"csv": str(csv_path), "samples": kpis["samples"]})
        mlflow.log_metrics(
            {
                "hover_rms_m": kpis["hover_rms_m"],
                "hover_max_dev_m": kpis["hover_max_dev_m"],
                "xy_rms_m": kpis["xy_rms_m"],
                "xy_max_m": kpis["xy_max_m"],
            }
        )
        mlflow.log_artifacts(str(outdir))

    print("✅ KPIs:", {k: round(v, 4) if isinstance(v, float) else v for k, v in kpis.items()})
    print(f"🧾 Report: {html}")


if __name__ == "__main__":
    main()
