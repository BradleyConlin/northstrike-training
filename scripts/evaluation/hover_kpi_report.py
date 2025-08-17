"""
hover_kpi_report.py
Lightweight, CI-friendly KPIs for hover logs.

- Optional heavy deps are safely guarded (matplotlib, mlflow, jinja2, plotly).
- Core logic depends only on numpy/pandas.
- compute_hover_kpis(...) is the entrypoint used by tests.

Usage (optional):
  python -m scripts.evaluation.hover_kpi_report --csv path/to/log.csv --plot out.png
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

# --- Optional deps guarded for CI ---
try:
    import matplotlib.pyplot as plt  # optional in CI
except Exception:
    plt = None

try:
    import mlflow  # optional in CI
except Exception:
    mlflow = None

try:
    from jinja2 import Template  # optional in CI
except Exception:
    Template = None

try:
    import plotly.express as px  # optional in CI
except Exception:
    px = None


# ---------- Helpers ----------
def _find_col(df: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    cols = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in cols:
            return cols[name.lower()]
    return None


def _time_col(df: pd.DataFrame) -> Optional[str]:
    return _find_col(df, ["time_s", "t", "time", "timestamp", "sec", "secs"])


def _alt_col(df: pd.DataFrame) -> Optional[str]:
    # Common altitude/vertical-position names
    return _find_col(df, ["z", "alt", "altitude", "pos_z", "z_m", "height"])


def _sp_alt_col(df: pd.DataFrame) -> Optional[str]:
    # Common setpoint names for altitude
    return _find_col(df, ["z_sp", "alt_sp", "setpoint_z", "target_z", "z_des", "altitude_des"])


def _xy_cols(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    x = _find_col(df, ["x", "pos_x", "x_m"])
    y = _find_col(df, ["y", "pos_y", "y_m"])
    return x, y


def _valid_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


@dataclass
class HoverKPIs:
    n: int
    duration_s: float
    alt_mean: float
    alt_std: float
    alt_rmse: Optional[float]
    max_alt_dev: Optional[float]
    xy_std: Optional[float]
    hover_score: Optional[float]  # 0..1 (higher is better)

    def to_dict(self) -> Dict[str, Union[int, float, None]]:
        return {
            "n": self.n,
            "duration_s": float(self.duration_s),
            "alt_mean": float(self.alt_mean) if not math.isnan(self.alt_mean) else float("nan"),
            "alt_std": float(self.alt_std) if not math.isnan(self.alt_std) else float("nan"),
            "alt_rmse": float(self.alt_rmse) if self.alt_rmse is not None else None,
            "max_alt_dev": float(self.max_alt_dev) if self.max_alt_dev is not None else None,
            "xy_std": float(self.xy_std) if self.xy_std is not None else None,
            "hover_score": float(self.hover_score) if self.hover_score is not None else None,
        }


# ---------- Core KPI function ----------
def compute_hover_kpis(
    data: Optional[pd.DataFrame] = None,
    *,
    df: Optional[pd.DataFrame] = None,
    csv_path: Optional[str] = None,
    sampling_hz: Optional[float] = None,
) -> Dict[str, Union[int, float, None]]:
    """
    Compute basic hover KPIs from a DataFrame or CSV.

    Parameters
    ----------
    data/df : pandas.DataFrame
        Telemetry table; common columns are auto-detected.
    csv_path : str
        Path to CSV if DataFrame not provided.
    sampling_hz : float, optional
        Used only if no time column is present, to estimate duration.

    Returns
    -------
    dict:
        {
          n, duration_s, alt_mean, alt_std, alt_rmse, max_alt_dev, xy_std, hover_score
        }
    """
    if df is None:
        df = data
    if df is None and csv_path is not None:
        df = pd.read_csv(csv_path)

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return HoverKPIs(
            n=0,
            duration_s=0.0,
            alt_mean=float("nan"),
            alt_std=float("nan"),
            alt_rmse=None,
            max_alt_dev=None,
            xy_std=None,
            hover_score=None,
        ).to_dict()

    # Copy, coerce numeric
    df = df.copy()
    # Identify columns
    t_col = _time_col(df)
    z_col = _alt_col(df)
    zsp_col = _sp_alt_col(df)
    x_col, y_col = _xy_cols(df)

    # Coerce numeric for used columns
    if t_col:
        df[t_col] = _valid_numeric(df[t_col])
    if z_col:
        df[z_col] = _valid_numeric(df[z_col])
    if zsp_col:
        df[zsp_col] = _valid_numeric(df[zsp_col])
    if x_col:
        df[x_col] = _valid_numeric(df[x_col])
    if y_col:
        df[y_col] = _valid_numeric(df[y_col])

    df = df.replace([np.inf, -np.inf], np.nan).dropna(how="all")

    n = len(df.index)
    duration_s = 0.0
    if t_col and df[t_col].notna().any():
        t = df[t_col].dropna()
        if len(t) >= 2:
            duration_s = float(t.iloc[-1] - t.iloc[0])
    elif sampling_hz and sampling_hz > 0:
        duration_s = float(n / sampling_hz)

    alt_mean = float("nan")
    alt_std = float("nan")
    alt_rmse = None
    max_alt_dev = None

    if z_col and df[z_col].notna().any():
        z = df[z_col].dropna().astype(float)
        alt_mean = float(z.mean())
        alt_std = float(z.std(ddof=0))

        if zsp_col and df[zsp_col].notna().any():
            zsp = df[zsp_col].dropna().astype(float)
            # Align by index
            joined = pd.concat([z, zsp], axis=1, join="inner").dropna()
            if joined.shape[0] > 0:
                err = (joined.iloc[:, 0] - joined.iloc[:, 1]).to_numpy()
                alt_rmse = float(np.sqrt(np.mean(err**2)))
                max_alt_dev = float(np.max(np.abs(err)))
        else:
            # Without setpoint, characterize stability by std and peak-to-mean
            alt_rmse = None
            max_alt_dev = float(np.max(np.abs(z - z.mean()))) if len(z) else None

    xy_std = None
    if x_col and y_col and df[x_col].notna().any() and df[y_col].notna().any():
        xs = df[x_col].dropna().to_numpy(dtype=float)
        ys = df[y_col].dropna().to_numpy(dtype=float)
        # Standard deviation of radial distance from mean hover point
        r = np.sqrt((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
        xy_std = float(r.std(ddof=0)) if r.size > 0 else None

    # Simple composite score (bounded 0..1), higher is better.
    # Uses alt_std and xy_std if present; penalizes large deviations.
    def _score(val: Optional[float], good: float, bad: float) -> Optional[float]:
        # Map val in [good..bad] -> [1..0]
        if val is None or math.isnan(val):
            return None
        if val <= good:
            return 1.0
        if val >= bad:
            return 0.0
        return float(1.0 - (val - good) / (bad - good))

    s_alt = _score(alt_std, good=0.05, bad=0.5)  # meters
    s_xy = _score(xy_std, good=0.05, bad=1.0)  # meters
    parts = [v for v in (s_alt, s_xy) if v is not None]
    hover_score = float(np.mean(parts)) if parts else None

    kpis = HoverKPIs(
        n=int(n),
        duration_s=float(duration_s),
        alt_mean=alt_mean,
        alt_std=alt_std,
        alt_rmse=alt_rmse,
        max_alt_dev=max_alt_dev,
        xy_std=xy_std,
        hover_score=hover_score,
    ).to_dict()

    # Optional MLflow logging (no-op if mlflow is missing)
    if mlflow:
        try:
            with mlflow.start_run(run_name="hover_kpis"):
                for k, v in kpis.items():
                    if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
                        mlflow.log_metric(k, float(v))
        except Exception:
            pass

    return kpis


# ---------- Plotting (optional) ----------
def render_hover_plot(
    df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
    title: str = "Hover Altitude",
) -> None:
    """Simple altitude plot; no-op if matplotlib is unavailable."""
    if plt is None:
        return
    if df is None or df.empty:
        return

    t_col = _time_col(df)
    z_col = _alt_col(df)
    if not z_col:
        return

    t = df[t_col] if t_col else np.arange(len(df[z_col]), dtype=float)
    z = df[z_col]
    plt.figure(figsize=(8, 3))
    plt.plot(t, z, linewidth=1.5)
    plt.xlabel("time [s]" if t_col else "sample")
    plt.ylabel("altitude [m]")
    plt.title(title)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        plt.close()


# ---------- CLI (optional) ----------
def _main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=str, required=True, help="Path to CSV with hover telemetry")
    p.add_argument(
        "--sampling-hz", type=float, default=None, help="Sampling rate if no time column"
    )
    p.add_argument("--plot", type=str, default=None, help="Path to save a PNG plot (optional)")
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    kpis = compute_hover_kpis(df=df, sampling_hz=args.sampling_hz)
    print(json.dumps(kpis, indent=2, sort_keys=True))

    if args.plot:
        render_hover_plot(df, save_path=args.plot)


if __name__ == "__main__":
    _main()
