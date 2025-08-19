from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def run_demo(planner: str, sim_seconds: float, seed: int) -> Path:
    """Run scripts.run_waypoint_demo to produce a CSV, then move it to a unique name."""
    out_csv_default = ART / "waypoint_run.csv"
    # Clean any previous default output
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
    if planner == "rrt":
        cmd += ["--rrt-seed", str(seed)]

    subprocess.run(cmd, check=True)
    assert out_csv_default.exists(), "expected demo to produce artifacts/waypoint_run.csv"

    target = ART / f"compare_{planner}.csv"
    try:
        target.unlink()
    except FileNotFoundError:
        pass
    shutil.move(out_csv_default, target)
    return target


def compute_kpis(csv_path: Path) -> dict:
    """Call waypoint_kpi_report to get KPIs as JSON and return the dict."""
    json_out = csv_path.with_suffix(".json")
    try:
        json_out.unlink()
    except FileNotFoundError:
        pass
    cmd = [
        sys.executable,
        "-m",
        "scripts.evaluation.waypoint_kpi_report",
        "--csv",
        str(csv_path),
        "--json-out",
        str(json_out),
    ]
    subprocess.run(cmd, check=True)
    data = json.loads(json_out.read_text())
    return data


def fmt_row(name: str, k: dict) -> str:
    return (
        f"| {name:6} | {k['hits']:>3} | {k['duration_s']:6.2f} | "
        f"{k['avg_err']:7.3f} | {k['rms_err']:7.3f} | {k['max_err']:7.3f} | {k['rating']} |"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compare A* vs RRT KPIs on the waypoint demo.")
    ap.add_argument("--sim-seconds", type=float, default=2.0, help="short run for CI/reporting")
    ap.add_argument("--rrt-seed", type=int, default=123)
    ap.add_argument("--out", default="artifacts/compare_planners.md")
    args = ap.parse_args(argv)

    astar_csv = run_demo("astar", args.sim_seconds, args.rrt_seed)
    rrt_csv = run_demo("rrt", args.sim_seconds, args.rrt_seed)

    astar_k = compute_kpis(astar_csv)
    rrt_k = compute_kpis(rrt_csv)

    lines = []
    ts = datetime.now().isoformat(timespec="seconds")
    lines.append(f"# Planner KPI Compare ({ts})\n")
    lines.append(f"- A* CSV: `{astar_csv}`")
    lines.append(f"- RRT CSV: `{rrt_csv}`\n")
    lines.append("| Planner | hits | dur[s] |  avg[m] |  rms[m] |  max[m] | rating |")
    lines.append("|:-------:|-----:|-------:|--------:|--------:|--------:|:------:|")
    lines.append(fmt_row("A*", astar_k))
    lines.append(fmt_row("RRT", rrt_k))
    lines.append("")

    out_path = Path(args.out)
    out_path.write_text("\n".join(lines))
    print(f"Wrote: {out_path}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
