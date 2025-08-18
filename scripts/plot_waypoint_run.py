#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import pandas as pd

# matplotlib is not in CI; install locally if needed:
#   pip install matplotlib
try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("matplotlib is required for plotting. Try: pip install matplotlib") from e


def _unique_waypoints(tx: pd.Series, ty: pd.Series) -> list[tuple[float, float]]:
    """Deduplicate consecutive (tx,ty) entries into a waypoint list."""
    pts: list[tuple[float, float]] = []
    last = (None, None)
    for x, y in zip(tx, ty):
        cur = (float(x), float(y))
        if cur != last:
            pts.append(cur)
            last = cur
    return pts


def load_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required: Iterable[str] = ("t", "px", "py", "vx", "vy", "tx", "ty", "wp_index")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV missing required columns: {missing}")
    return df


def plot_xy(df: pd.DataFrame) -> None:
    plt.figure()
    plt.plot(df["px"], df["py"], label="truth (px,py)")
    if {"px_est", "py_est"}.issubset(df.columns):
        plt.plot(df["px_est"], df["py_est"], label="EKF (px,py)")
    wps = _unique_waypoints(df["tx"], df["ty"])
    if wps:
        xs, ys = zip(*wps)
        plt.scatter(xs, ys, marker="x", label="waypoints")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")
    plt.title("Trajectory")
    plt.legend()
    plt.axis("equal")


def plot_timeseries(df: pd.DataFrame) -> None:
    plt.figure()
    if {"px_est", "py_est"}.issubset(df.columns):
        dx = df["px"] - df["px_est"]
        dy = df["py"] - df["py_est"]
        pos_err = (dx * dx + dy * dy) ** 0.5
        plt.plot(df["t"], pos_err, label="|pos error|")
        plt.ylabel("position error [m]")
        plt.title("EKF position error vs time")
    else:
        speed = (df["vx"] * df["vx"] + df["vy"] * df["vy"]) ** 0.5
        plt.plot(df["t"], speed, label="speed")
        plt.ylabel("speed [m/s]")
        plt.title("Speed vs time")
    plt.xlabel("t [s]")
    plt.legend()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Plot waypoint run CSV.")
    ap.add_argument(
        "--csv",
        default="artifacts/waypoint_run.csv",
        help="Path to CSV (supports EKF and non-EKF formats).",
    )
    ap.add_argument(
        "--out",
        default="artifacts/waypoint_plot.png",
        help="Output PNG path (saved in addition to optional --show).",
    )
    ap.add_argument(
        "--show",
        action="store_true",
        help="Show interactive windows after saving the PNG.",
    )
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df = load_df(args.csv)

    plot_xy(df)
    plot_timeseries(df)

    # Save the last figure as a combined PNG by grabbing the active manager canvas
    # Preferably, save all figures to one image: we’ll just save the current figure
    # and also save each individual figure into numbered files.
    # 1) save combined grid (quick & simple: just current active figure)
    plt.savefig(args.out, dpi=150, bbox_inches="tight")

    # 2) also save individual figures (xy + timeseries)
    out_base = Path(args.out)
    for i, num in enumerate(plt.get_fignums(), start=1):
        plt.figure(num)
        plt.savefig(
            out_base.with_name(out_base.stem + f"_{i}" + out_base.suffix),
            dpi=150,
            bbox_inches="tight",
        )

    if args.show:
        plt.show()

    print(f"Wrote plots to: {args.out} (and numbered variants)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
