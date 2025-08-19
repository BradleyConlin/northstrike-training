from __future__ import annotations

import argparse
import json
import shutil
import statistics as stats
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def run_demo(planner: str, sim_seconds: float, seed: int | None) -> Path:
    """Run scripts.run_waypoint_demo -> artifacts/waypoint_run.csv, then move to a unique name."""
    out_csv_default = ART / "waypoint_run.csv"
    try:
        out_csv_default.unlink()
    except FileNotFoundError:
        pass

    cmd = [
        sys.executable,
        "-m",
        "scripts.run_waypoint_demo",
        "--sim-seconds",
        str(sim_seconds),
        "--dt",
        "0.02",
        "--wp-radius",
        "0.5",
        "--planner",
        planner,
    ]
    if planner == "rrt" and seed is not None:
        cmd += ["--rrt-seed", str(seed)]

    subprocess.run(cmd, check=True)

    target = ART / (
        f"sweep_{planner}_seed{seed}.csv" if seed is not None else f"sweep_{planner}.csv"
    )
    try:
        target.unlink()
    except FileNotFoundError:
        pass
    shutil.move(out_csv_default, target)
    return target


def compute_kpis(csv_path: Path) -> dict:
    json_out = csv_path.with_suffix(".json")
    try:
        json_out.unlink()
    except FileNotFoundError:
        pass
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.waypoint_kpi_report",
            "--csv",
            str(csv_path),
            "--json-out",
            str(json_out),
        ],
        check=True,
    )
    return json.loads(json_out.read_text())


def agg(vals):
    return {
        "mean": float(stats.mean(vals)),
        "std": float(stats.pstdev(vals)) if len(vals) > 1 else 0.0,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Seed sweep: compare A* vs RRT KPIs over multiple seeds."
    )
    ap.add_argument("--seeds", type=int, default=10, help="number of RRT seeds (A* runs once)")
    ap.add_argument("--sim-seconds", type=float, default=2.0, help="short run for CI/reporting")
    ap.add_argument("--out", default="artifacts/compare_planners_sweep.md")
    args = ap.parse_args(argv)

    # A* (no seed dependence in our current grid setup)
    astar_csv = run_demo("astar", args.sim_seconds, None)
    astar_k = compute_kpis(astar_csv)

    # RRT across seeds
    rrt_runs = []
    for sd in range(args.seeds):
        csv = run_demo("rrt", args.sim_seconds, sd)
        rrt_runs.append(compute_kpis(csv))

    def extract(metric):
        return [r[metric] for r in rrt_runs]

    # aggregates
    rrt_hits = extract("hits")
    rrt_avg = extract("avg_err")
    rrt_rms = extract("rms_err")
    rrt_max = extract("max_err")
    rrt_ratings = [r["rating"] for r in rrt_runs]
    green_count = sum(1 for r in rrt_ratings if r == "green")
    yellow_count = sum(1 for r in rrt_ratings if r == "yellow")
    red_count = sum(1 for r in rrt_ratings if r == "red")

    lines = []
    ts = datetime.now().isoformat(timespec="seconds")
    lines.append(f"# Planner KPI Seed Sweep ({ts})\n")
    lines.append(f"- A* single run CSV: `{astar_csv}`")
    lines.append(f"- RRT seeds: {args.seeds} (CSV files under `artifacts/sweep_rrt_seed*.csv`)\n")

    lines.append("## A* (single run)")
    lines.append("| hits | dur[s] |  avg[m] |  rms[m] |  max[m] | rating |")
    lines.append("|-----:|-------:|--------:|--------:|--------:|:------:|")
    lines.append(
        f"| {astar_k['hits']:>4} | {astar_k['duration_s']:6.2f} | {astar_k['avg_err']:7.3f} | "
        f"{astar_k['rms_err']:7.3f} | {astar_k['max_err']:7.3f} | {astar_k['rating']} |"
    )
    lines.append("")

    lines.append("## RRT (across seeds)")
    lines.append(f"- ratings: 🟢 {green_count} · 🟡 {yellow_count} · 🔴 {red_count}")
    lines.append("| metric | mean | std |")
    lines.append("|:------:|-----:|----:|")
    lines.append(f"| hits | {agg(rrt_hits)['mean']:.2f} | {agg(rrt_hits)['std']:.2f} |")
    lines.append(f"| avg_err [m] | {agg(rrt_avg)['mean']:.3f} | {agg(rrt_avg)['std']:.3f} |")
    lines.append(f"| rms_err [m] | {agg(rrt_rms)['mean']:.3f} | {agg(rrt_rms)['std']:.3f} |")
    lines.append(f"| max_err [m] | {agg(rrt_max)['mean']:.3f} | {agg(rrt_max)['std']:.3f} |")
    lines.append("")

    out_path = Path(args.out)
    out_path.write_text("\n".join(lines))
    print(f"Wrote: {out_path}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
