#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

OUT = Path("artifacts/sysid")
OUT.mkdir(parents=True, exist_ok=True)


@dataclass
class true_params:
    m: float = 1.50
    kx: float = 0.40
    ky: float = 0.55


def gen_synth(T: float = 12.0, dt: float = 0.02, seed: int = 7, m=1.5, kx=0.4, ky=0.55):
    """Generate 2D point-mass with linear drag: v' = u/m - (k/m) v."""
    rng = np.random.default_rng(seed)
    n = int(T / dt)
    # piecewise-constant force steps
    seg = max(1, int(0.6 / dt))
    ux = np.repeat(rng.uniform(-3, 3, size=n // seg + 1), seg)[:n]
    uy = np.repeat(rng.uniform(-3, 3, size=n // seg + 1), seg)[:n]
    vx = np.zeros(n)
    vy = np.zeros(n)
    ax = np.zeros(n)
    ay = np.zeros(n)
    for t in range(1, n):
        ax[t] = (ux[t - 1] / m) - (kx / m) * vx[t - 1]
        ay[t] = (uy[t - 1] / m) - (ky / m) * vy[t - 1]
        vx[t] = vx[t - 1] + dt * ax[t]
        vy[t] = vy[t - 1] + dt * ay[t]
    # add a touch of accel noise
    ax_n = ax + rng.normal(0, 0.05, size=n)
    ay_n = ay + rng.normal(0, 0.05, size=n)
    tvec = np.arange(n) * dt
    return tvec, ux, uy, vx, vy, ax_n, ay_n


def fit_axis(u: np.ndarray, v: np.ndarray, a: np.ndarray):
    """
    Solve a[t] ~ b0*u[t-1] + b1*v[t-1]
    Then m = 1/b0, k = -(b1/b0)*m  (since a = (1/m)u - (k/m)v)
    """
    if len(a) < 2:
        return np.inf, np.nan, np.inf
    # align with simulator’s update: use (u[:-1], v[:-1]) -> a[1:]
    a1 = a[1:]
    u1 = u[:-1]
    v1 = v[:-1]
    Phi = np.stack([u1, v1], axis=1)  # [n-1, 2]
    theta, *_ = np.linalg.lstsq(Phi, a1, rcond=None)
    b0, b1 = theta
    if abs(b0) < 1e-9:
        return np.inf, np.nan, float("inf")
    m_est = 1.0 / b0
    k_est = -b1 * m_est
    mse = float(np.mean((a1 - Phi @ theta) ** 2))
    return (float(m_est), float(k_est), mse)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--T", type=float, default=12.0)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--m_true", type=float, default=true_params.m)
    ap.add_argument("--kx_true", type=float, default=true_params.kx)
    ap.add_argument("--ky_true", type=float, default=true_params.ky)
    args = ap.parse_args()

    t, ux, uy, vx, vy, ax, ay = gen_synth(
        args.T, args.dt, args.seed, args.m_true, args.kx_true, args.ky_true
    )

    m_x, kx_est, mse_x = fit_axis(ux, vx, ax)
    m_y, ky_est, mse_y = fit_axis(uy, vy, ay)
    m_est = float(np.mean([m_x, m_y]))

    diag_csv = OUT / "est_diagnostics.csv"
    with diag_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "ux", "uy", "vx", "vy", "ax", "ay"])
        for i in range(len(t)):
            w.writerow([t[i], ux[i], uy[i], vx[i], vy[i], ax[i], ay[i]])

    params = {
        "m_est": m_est,
        "kx_est": float(kx_est),
        "ky_est": float(ky_est),
        "mse_x": mse_x,
        "mse_y": mse_y,
        "T": args.T,
        "dt": args.dt,
        "seed": args.seed,
        "true": {"m": args.m_true, "kx": args.kx_true, "ky": args.ky_true},
    }
    (OUT / "est_params.json").write_text(json.dumps(params, indent=2))
    print("Wrote:", diag_csv, "and", OUT / "est_params.json")
    print(json.dumps(params))


if __name__ == "__main__":
    main()
