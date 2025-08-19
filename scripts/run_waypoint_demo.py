from __future__ import annotations

import argparse
import csv
import math
import os

from planners.astar import plan_on_grid as astar_plan
from planners.rrt import plan_on_grid_rrt

from control.pid_pos import Limits, PIDGains, PIDPos2D
from sim.quad_2d import Quad2D, QuadParams

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def demo_grid(w: int = 20, h: int = 10):
    g = [[0 for _ in range(w)] for _ in range(h)]
    for x in range(5, 15):
        g[5][x] = 1
    return g


def load_pid_config(path: str | None):
    if not path or not os.path.exists(path) or yaml is None:
        return PIDGains(0.6, 0.02, 0.8), Limits(accel_max=2.0, i_limit=0.8)
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    gx = cfg.get("gains", {}).get("x", {})
    lim = cfg.get("limits", {})
    gains = PIDGains(
        float(gx.get("kp", 0.6)),
        float(gx.get("ki", 0.02)),
        float(gx.get("kd", 0.8)),
    )
    limits = Limits(
        float(lim.get("accel_max", 2.0)),
        float(lim.get("i_limit", 0.8)),
    )
    return gains, limits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Waypoint demo: A* -> PID -> Quad2D")
    ap.add_argument("--grid-start", default="0,0")
    ap.add_argument("--grid-goal", default="19,9")
    ap.add_argument("--planner", choices=["astar", "rrt"], default="astar")
    ap.add_argument("--rrt-seed", type=int, default=0)
    ap.add_argument("--scale", type=float, default=1.0, help="meters per grid cell")
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--sim-seconds", type=float, default=30.0)
    ap.add_argument("--wp-radius", type=float, default=0.2)
    ap.add_argument("--pid-config", default="configs/pid_pos.yaml")
    ap.add_argument("--csv-out", default="artifacts/waypoint_run.csv")
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

    # Sim loop
    dt = args.dt
    T = args.sim_seconds
    wp_i = 0
    pos = (0.0, 0.0)
    vel = (0.0, 0.0)

    with open(args.csv_out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "px", "py", "vx", "vy", "tx", "ty", "wp_index"])
        t = 0.0
        while t <= T and wp_i < len(waypoints):
            target = waypoints[wp_i]
            ax, ay = ctrl.step(dt, pos, vel, target)
            px, py, vx, vy = quad.step(dt, ax, ay)
            pos, vel = (px, py), (vx, vy)
            w.writerow([t, px, py, vx, vy, target[0], target[1], wp_i])

            # advance waypoint when close
            if math.hypot(target[0] - px, target[1] - py) <= args.wp_radius:
                wp_i += 1
            t += dt

    print(f"Sim finished. Waypoints reached: {wp_i}/{len(waypoints)}")
    print(f"Wrote: {args.csv_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
