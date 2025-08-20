#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np

from src.controllers.fixedwing.l1 import l1_lateral_accel
from src.controllers.fixedwing.tecs import tecs_vertical_speed_cmd

OUT = Path("artifacts/fixedwing")
OUT.mkdir(parents=True, exist_ok=True)

Vec2 = Tuple[float, float]
WP = Tuple[float, float, float]  # x,y,alt


def _track_error_xy(p: Vec2, a: Vec2, b: Vec2) -> float:
    # distance from point p to line segment a->b (cross-track)
    ax, ay = a
    bx, by = b
    px, py = p
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    v2 = vx * vx + vy * vy
    if v2 < 1e-9:
        return math.hypot(wx, wy)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / v2))
    cx, cy = ax + t * vx, ay + t * vy
    return math.hypot(px - cx, py - cy)


def run_sim(dt: float = 0.05, steps: int = 2400, speed: float = 15.0):
    # rectangle mission with altitude profile
    wps: List[WP] = [
        (0.0, 0.0, 20.0),
        (400.0, 0.0, 60.0),
        (400.0, 400.0, 60.0),
        (0.0, 400.0, 40.0),
        (0.0, 0.0, 20.0),
    ]
    seg = 0
    # start near the first leg to limit initial transient
    pos = np.array([-20.0, -20.0, 20.0], dtype=float)
    chi = 0.0  # rad
    V = float(speed)

    xs, ys, zs, e_xtrack = [], [], [], []
    last_alt_cmd = wps[0][2]

    for _ in range(steps):
        wp_prev = (wps[seg][0], wps[seg][1])
        wp_next = (wps[(seg + 1) % len(wps)][0], wps[(seg + 1) % len(wps)][1])
        alt_cmd = wps[(seg + 1) % len(wps)][2]
        last_alt_cmd = alt_cmd

        vel = (V * math.cos(chi), V * math.sin(chi))
        a_y = l1_lateral_accel(
            (pos[0], pos[1]), vel, wp_prev, wp_next, L1_period=12.0, damping=0.75, a_max=15.0
        )
        chi += (a_y / V) * dt

        vdot = tecs_vertical_speed_cmd(pos[2], alt_cmd, V, kp_alt=0.8, vdot_lim_frac=0.35)

        pos[0] += V * math.cos(chi) * dt
        pos[1] += V * math.sin(chi) * dt
        pos[2] += vdot * dt

        xs.append(pos[0])
        ys.append(pos[1])
        zs.append(pos[2])
        e_xtrack.append(_track_error_xy((pos[0], pos[1]), wp_prev, wp_next))

        # advance when close laterally to next waypoint
        d2next = math.hypot(pos[0] - wp_next[0], pos[1] - wp_next[1])
        if d2next < 35.0:
            seg = (seg + 1) % len(wps)

    rmse_ct = float(np.sqrt(np.mean(np.square(e_xtrack))))
    alt_err_final = float(abs(zs[-1] - last_alt_cmd))  # error w.r.t. current setpoint

    traj_csv = OUT / "fw_traj.csv"
    with traj_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "alt"])
        w.writerows(zip(xs, ys, zs))

    metrics = {"rmse_xtrack_m": rmse_ct, "alt_final_err_m": alt_err_final}
    (OUT / "fw_metrics.json").write_text(json.dumps(metrics, indent=2))
    print("Wrote:", traj_csv, "and", OUT / "fw_metrics.json")
    print(json.dumps(metrics))
    return metrics


if __name__ == "__main__":
    run_sim()
