from __future__ import annotations

import argparse
import csv
import math
import os
import random

from planners.astar import plan_on_grid as astar_plan
from planners.rrt import plan_on_grid_rrt

from control.pid_pos import PIDPos2D
from scripts.run_waypoint_demo import demo_grid, load_pid_config  # reuse helpers
from sim.ekf_2d import EKF2D, EKFParams
from sim.quad_2d import Quad2D, QuadParams


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Waypoint demo with EKF & noisy position measurements")
    ap.add_argument("--grid-start", default="0,0")
    ap.add_argument("--grid-goal", default="19,9")
    ap.add_argument("--planner", choices=["astar", "rrt"], default="astar")
    ap.add_argument("--rrt-seed", type=int, default=0)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--sim-seconds", type=float, default=30.0)
    ap.add_argument("--wp-radius", type=float, default=0.2)
    ap.add_argument("--pid-config", default="configs/pid_pos.yaml")
    ap.add_argument("--pos-noise-std", type=float, default=0.3)
    ap.add_argument("--csv-out", default="artifacts/waypoint_run_ekf.csv")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(args.csv_out), exist_ok=True)

    # Plan on grid
    grid = demo_grid()
    sx, sy = (int(s) for s in args.grid_start.split(","))
    gx, gy = (int(s) for s in args.grid_goal.split(","))
    path_cells = (
        astar_plan(grid, (sx, sy), (gx, gy), allow_diag=True, simplify=True)
        if args.planner == "astar"
        else plan_on_grid_rrt(
            grid, (sx, sy), (gx, gy), seed=args.rrt_seed, allow_diag=True, simplify=True
        )
    )
    waypoints = [(x * args.scale, y * args.scale) for (x, y) in path_cells]

    # Controller and plant
    gains, limits = load_pid_config(args.pid_config)
    ctrl = PIDPos2D(gains_x=gains, limits=limits)
    quad = Quad2D(QuadParams(drag=0.15, accel_max=limits.accel_max))

    # EKF
    ekf = EKF2D(args.dt, EKFParams(r_pos=args.pos_noise_std**2))
    ekf.reset()

    # Sim loop
    dt = args.dt
    T = args.sim_seconds
    wp_i = 0
    pos = (0.0, 0.0)
    vel = (0.0, 0.0)
    rng = random.Random(42)

    with open(args.csv_out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "t",
                "px",
                "py",
                "vx",
                "vy",
                "zpx",
                "zpy",
                "ekf_px",
                "ekf_py",
                "ekf_vx",
                "ekf_vy",
                "tx",
                "ty",
                "wp_index",
            ]
        )
        t = 0.0
        while t <= T and wp_i < len(waypoints):
            target = waypoints[wp_i]
            ax, ay = ctrl.step(dt, pos, vel, target)
            px, py, vx, vy = quad.step(dt, ax, ay)
            pos, vel = (px, py), (vx, vy)

            # Noisy position measurement
            zpx = px + rng.gauss(0.0, args.pos_noise_std)
            zpy = py + rng.gauss(0.0, args.pos_noise_std)

            ekf_px, ekf_py, ekf_vx, ekf_vy = ekf.step(ax, ay, zpx, zpy)
            w.writerow(
                [
                    t,
                    px,
                    py,
                    vx,
                    vy,
                    zpx,
                    zpy,
                    ekf_px,
                    ekf_py,
                    ekf_vx,
                    ekf_vy,
                    target[0],
                    target[1],
                    wp_i,
                ]
            )

            if math.hypot(target[0] - px, target[1] - py) <= args.wp_radius:
                wp_i += 1
            t += dt

    print(f"Sim finished. Waypoints reached: {wp_i}/{len(waypoints)}")
    print(f"Wrote: {args.csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
