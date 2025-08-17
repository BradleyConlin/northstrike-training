"""
hover_kpi_report.py (CI-safe)
- Imports only numpy/pandas at module import time.
- Plotting uses a lazy matplotlib import inside the function.
- Returns keys expected by tests, including 'samples'.
"""

from __future__ import annotations

import json
import math
from typing import Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd


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
    # Common altitude/vertical-position names used in logs/tests
    return _find_col(
        df,
        [
            "rel_alt_m",  # relative altitude (m)
            "abs_alt_m",  # absolute altitude (m)
            "z",
            "alt",
            "altitude",
            "pos_z",
            "z_m",
            "height",
        ],
    )


def _sp_alt_col(df: pd.DataFrame) -> Optional[str]:
    # Common setpoint names for altitude
    return _find_col(
        df,
        [
            "rel_alt_sp_m",
            "alt_sp_m",
            "z_sp",
            "alt_sp",
            "setpoint_z",
            "target_z",
            "z_des",
            "altitude_des",
        ],
    )


def _xy_cols(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    x = _find_col(df, ["x", "pos_x", "x_m"])
    y = _find_col(df, ["y", "pos_y", "y_m"])
    return x, y


def _valid_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


# ----------Compute Hover KPIs ----------


def compute_hover_kpis(
    data: Optional[pd.DataFrame] = None,
    *,
    df: Optional[pd.DataFrame] = None,
    csv_path: Optional[str] = None,
    sampling_hz: Optional[float] = None,
) -> Dict[str, Union[int, float, None]]:
    """
    Compute basic hover KPIs from a DataFrame or CSV.

    Returns dict with keys:
      samples, duration_s, alt_mean, alt_std, alt_rmse, hover_rms_m, max_alt_dev, xy_std, hover_score
    """
    if df is None:
        df = data
    if df is None and csv_path is not None:
        df = pd.read_csv(csv_path)

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {
            "samples": 0,
            "duration_s": 0.0,
            "alt_mean": float("nan"),
            "alt_std": float("nan"),
            "alt_rmse": None,
            "hover_rms_m": None,
            "max_alt_dev": None,
            "xy_std": None,
            "xy_rms_m": 0.0,
            "hover_score": None,
        }

    df = df.copy()

    # Identify columns
    t_col = _time_col(df)
    z_col = _alt_col(df)
    zsp_col = _sp_alt_col(df)
    x_col, y_col = _xy_cols(df)

    # Coerce numeric
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

    n = int(len(df.index))
    duration_s = 0.0
    if t_col and df[t_col].notna().any():
        t = df[t_col].dropna()
        if len(t) >= 2:
            duration_s = float(t.iloc[-1] - t.iloc[0])
    elif sampling_hz and sampling_hz > 0:
        duration_s = float(n / sampling_hz)

    alt_mean = float("nan")
    alt_std = float("nan")
    alt_rmse: Optional[float] = None
    max_alt_dev: Optional[float] = None

    if z_col and df[z_col].notna().any():
        z = df[z_col].dropna().astype(float)
        alt_mean = float(z.mean())
        alt_std = float(z.std(ddof=0))  # std == RMS around the mean

        if zsp_col and df[zsp_col].notna().any():
            zsp = df[zsp_col].dropna().astype(float)
            joined = pd.concat([z, zsp], axis=1, join="inner").dropna()
            if len(joined) > 0:
                err = (joined.iloc[:, 0] - joined.iloc[:, 1]).to_numpy()
                alt_rmse = float(np.sqrt(np.mean(err**2)))
                max_alt_dev = float(np.max(np.abs(err)))
        else:
            # Without a setpoint, characterize stability around the mean
            max_alt_dev = float(np.max(np.abs(z - z.mean()))) if len(z) else None

    # hover_rms_m is RMSE vs setpoint when available; otherwise RMS around mean (= alt_std)
    hover_rms_m: Optional[float] = (
        alt_rmse
        if alt_rmse is not None
        else (alt_std if not (isinstance(alt_std, float) and np.isnan(alt_std)) else None)
    )

    xy_std: Optional[float] = None
    if x_col and y_col and df[x_col].notna().any() and df[y_col].notna().any():
        xs = df[x_col].dropna().to_numpy(dtype=float)
        ys = df[y_col].dropna().to_numpy(dtype=float)
        r = np.sqrt((xs - xs.mean()) ** 2 + (ys - ys.mean()) ** 2)
        xy_std = float(r.std(ddof=0)) if r.size > 0 else None

    # xy_rms_m: RMS horizontal deviation (m); if XY not available, treat as 0.0 (stationary)
    xy_rms_m: Optional[float] = xy_std if xy_std is not None else 0.0

    # Composite score (0..1), higher is better
    def _score(val: Optional[float], good: float, bad: float) -> Optional[float]:
        if val is None or (isinstance(val, float) and math.isnan(val)):
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

    return {
        "samples": n,
        "duration_s": float(duration_s),
        "alt_mean": alt_mean,
        "alt_std": alt_std,
        "alt_rmse": alt_rmse,
        "hover_rms_m": hover_rms_m,
        "max_alt_dev": max_alt_dev,
        "xy_std": xy_std,
        "xy_rms_m": xy_rms_m,
        "hover_score": hover_score,
    }


# ---------- Optional plotting (lazy import) ----------
def render_hover_plot(
    df: pd.DataFrame,
    *,
    save_path: Optional[str] = None,
    title: str = "Hover Altitude",
) -> None:
    """No-op if matplotlib is unavailable."""
    try:
        import matplotlib.pyplot as plt  # lazy, optional
    except Exception:
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


# ---------- CLI ----------
def _main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=str, required=True)
    p.add_argument("--sampling-hz", type=float, default=None)
    p.add_argument("--plot", type=str, default=None)
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    kpis = compute_hover_kpis(df=df, sampling_hz=args.sampling_hz)
    print(json.dumps(kpis, indent=2, sort_keys=True))

    if args.plot:
        render_hover_plot(df, save_path=args.plot)


if __name__ == "__main__":
    _main()
