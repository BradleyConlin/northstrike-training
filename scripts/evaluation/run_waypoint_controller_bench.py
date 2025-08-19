"""
Controller micro-bench: track 3 waypoints in a simple 2D double-integrator model.
Writes CSV per run and JSON/MD summaries into artifacts/.

Usage:
  python -m scripts.evaluation.run_waypoint_controller_bench --controller lqr --seeds 10 --sim-seconds 3.0
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path

# Make "src" imports work in dev without installing the package
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from controllers.lqr.lqr_position import Limits, LQRGains, LQRPos2D  # noqa: E402
from controllers.utils.pure_pursuit import PPConfig, PurePursuit2D  # noqa: E402

ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def kpis_from_csv(csv_path: Path) -> dict:
    xs, ys, errs = [], [], []
    hits = 0
    with csv_path.open() as f:
        rd = csv.DictReader(f)
        for row in rd:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
            errs.append(float(row["dist_to_wp"]))
            if row.get("hit") == "1":
                hits += 1
    if not errs:
        return {
            "hits": 0,
            "duration_s": 0.0,
            "sample_hz": 0.0,
            "avg_err": 0.0,
            "rms_err": 0.0,
            "max_err": 0.0,
            "rating": "red",
        }

    avg_err = sum(errs) / len(errs)
    rms_err = math.sqrt(sum(e * e for e in errs) / len(errs))
    max_err = max(errs)
    rating = "green" if rms_err < 1.5 and hits >= 2 else ("yellow" if rms_err < 2.5 else "red")
    # duration and hz are constant here, we’ll compute in run()
    return {
        "hits": hits,
        "avg_err": avg_err,
        "rms_err": rms_err,
        "max_err": max_err,
        "rating": rating,
    }


def run_once(controller: str, sim_seconds: float, sd: int, dt: float = 0.02) -> Path:
    random.seed(sd)
    # Three waypoints in a simple square-ish path
    wps = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    hit_radius = 0.75

    # state
    x, y = 0.0 + random.uniform(-0.5, 0.5), -1.0 + random.uniform(-0.5, 0.5)
    vx, vy = 0.0, 0.0
    wp_idx = 0

    # controllers
    lqr = LQRPos2D(LQRGains(2.0, 3.5, 0.1), limits=Limits(accel_max=3.0, i_limit=0.5))
    pp = PurePursuit2D(
        PPConfig(lookahead=2.5, desired_speed=4.0, accel_limit=3.0, vel_p=1.6, vel_d=0.0)
    )

    out = ART / f"controller_run_{controller}_seed{sd}.csv"
    with out.open("w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["t", "x", "y", "vx", "vy", "wx", "wy", "dist_to_wp", "hit"])

        t = 0.0
        steps = int(sim_seconds / dt)
        for _ in range(steps):
            wx, wy = wps[wp_idx]
            dist = math.hypot(wx - x, wy - y)
            hit = 0
            if dist <= hit_radius:
                hit = 1
                wp_idx = min(wp_idx + 1, len(wps) - 1)

            if controller == "lqr":
                ax, ay = lqr.step(dt, (x, y), (vx, vy), (wx, wy))
            elif controller == "pp":
                ax, ay = pp.accel_cmd((x, y), (vx, vy), (wx, wy))
            else:
                # ultra-simple PD baseline (position -> accel); for comparison only
                kp, kd, amax = 1.2, 0.3, 2.0
                ex, ey = wx - x, wy - y
                ax = kp * ex - kd * vx
                ay = kp * ey - kd * vy
                mag = math.hypot(ax, ay)
                if mag > amax and mag > 1e-6:
                    s = amax / mag
                    ax *= s
                    ay *= s

            # integrate double-integrator plant (very simple)
            vx += ax * dt
            vy += ay * dt
            x += vx * dt
            y += vy * dt

            wr.writerow(
                [
                    f"{t:.2f}",
                    f"{x:.3f}",
                    f"{y:.3f}",
                    f"{vx:.3f}",
                    f"{vy:.3f}",
                    f"{wx:.3f}",
                    f"{wy:.3f}",
                    f"{dist:.3f}",
                    hit,
                ]
            )
            t += dt

    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--controller", choices=["pid", "lqr", "pp"], default="lqr")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--sim-seconds", type=float, default=3.0)
    ap.add_argument("--dt", type=float, default=0.02)
    args = ap.parse_args(argv)

    json_runs = []
    for sd in range(args.seeds):
        csv_path = run_once(args.controller, args.sim_seconds, sd, dt=args.dt)
        k = kpis_from_csv(csv_path)
        k["duration_s"] = args.sim_seconds
        k["sample_hz"] = round(1.0 / args.dt, 1)
        json_runs.append(k)

    # write per-controller sweep JSON + short MD summary
    jpath = ART / f"controller_sweep_{args.controller}.json"
    jpath.write_text(json.dumps(json_runs, indent=2))

    # aggregate
    rms = [r["rms_err"] for r in json_runs]
    hits = [r["hits"] for r in json_runs]
    ratings = [r["rating"] for r in json_runs]
    md = []
    ts = datetime.now().isoformat(timespec="seconds")
    md.append(f"# Controller Micro-Bench – {args.controller.upper()} ({ts})\n")
    md.append(
        f"- ratings: 🟢 {ratings.count('green')} · 🟡 {ratings.count('yellow')} · 🔴 {ratings.count('red')}"
    )
    md.append("| metric | mean | std |")
    md.append("|:------:|-----:|----:|")
    md.append(f"| hits | {sum(hits)/len(hits):.2f} | {0.0:.2f} |")
    md.append(
        f"| rms_err [m] | {sum(rms)/len(rms):.3f} | "
        + (
            f"{(sum((x - sum(rms)/len(rms))**2 for x in rms)/len(rms))**0.5:.3f}"
            if rms
            else "0.000"
        )
        + " |"
    )
    (ART / f"controller_sweep_{args.controller}.md").write_text("\n".join(md) + "\n")

    print(f"Wrote JSON: {jpath}")
    print(f"Wrote MD:   {ART / f'controller_sweep_{args.controller}.md'}")


if __name__ == "__main__":
    main()
