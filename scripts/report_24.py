#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Dict, List, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

GREEN = "🟢"
YELLOW = "🟡"
RED = "🔴"

AREAS: List[Tuple[int, str]] = [
    (1, "Simulation & Data-Generation Tools"),
    (2, "Path-Planning Algorithms"),
    (3, "Flight-Control Algorithms"),
    (4, "Sensor Fusion & State Estimation"),
    (5, "Perception & Computer Vision"),
    (6, "Multi-Agent Coordination & Swarm Behaviour"),
    (7, "Domain-Specific Models & Tools"),
    (8, "Training Infrastructure & Tools"),
    (9, "Compatibility Considerations"),
    (10, "MLOps & Experiment Tracking"),
    (11, "RL Stack & Safety-Aware Training"),
    (12, "SysID & Flight-Model Calibration"),
    (13, "Fixed-Wing Control (TECS & L1)"),
    (14, "Hardware-in-the-Loop (HIL) & Bench Testing"),
    (15, "Domain Randomization & Sim-to-Real"),
    (16, "Evaluation Benchmarks & KPIs"),
    (17, "Post-Deployment Observability & Drift"),
    (18, "Edge Packaging & Performance Budgets"),
    (19, "Data Labeling, QA & Governance"),
    (20, "Safety, Compliance & SOPs (Transport Canada)"),
    (21, "Secrets & Config Hygiene"),
    (22, "CI/CD & Release Engineering"),
    (23, "Architecture Decision Records (ADRs)"),
    (24, "Mission & Parameter Bundles"),
]

# Baseline (what we last saw) — #18 will be computed live below
BASELINE: Dict[int, str] = {
    1: GREEN,
    2: GREEN,
    3: GREEN,
    4: GREEN,
    5: GREEN,
    6: GREEN,
    7: GREEN,
    8: GREEN,
    9: GREEN,
    10: GREEN,
    11: GREEN,
    12: GREEN,
    13: GREEN,
    14: GREEN,
    15: GREEN,
    16: GREEN,
    17: GREEN,
    18: RED,  # <- will be recomputed from budgets
    19: RED,
    20: RED,
    21: YELLOW,
    22: GREEN,
    23: GREEN,
    24: YELLOW,
}


def _load_yaml(path: str) -> dict:
    if yaml is None:
        return {}
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _docker_image_size_mb(image: str) -> float | None:
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", "-f", "{{.Size}}", image],
            check=True,
            capture_output=True,
            text=True,
        )
        size_bytes = int(r.stdout.strip())
        return size_bytes / (1024 * 1024)
    except Exception:
        return None


def _file_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _check_edge_budgets(
    budgets_path="budgets.yaml",
    perf_json_path="artifacts/perf.json",
    image="northstrike-eval:latest",
) -> Tuple[bool, List[str]]:
    notes: List[str] = []
    cfg = _load_yaml(budgets_path)
    limits = cfg or {}
    # Defaults if budgets.yaml missing
    p50_max = float(limits.get("p50_ms_max", 15.0))
    p95_max = float(limits.get("p95_ms_max", 30.0))
    fps_min = float(limits.get("fps_min", 60.0))
    img_max = float(limits.get("image_size_mb_max", 2500.0))

    # Perf JSON
    perf = _file_json(perf_json_path)
    p50 = float(perf.get("p50_ms", 1e9))
    p95 = float(perf.get("p95_ms", 1e9))
    fps = float(perf.get("fps", 0.0))

    ok_p50 = p50 <= p50_max
    ok_p95 = p95 <= p95_max
    ok_fps = fps >= fps_min

    notes.append(f"p50: {p50:.2f} ms (max {p50_max:.2f}) -> {'OK' if ok_p50 else 'FAIL'}")
    notes.append(f"p95: {p95:.2f} ms (max {p95_max:.2f}) -> {'OK' if ok_p95 else 'FAIL'}")
    notes.append(f"fps: {fps:.2f} (min {fps_min:.2f}) -> {'OK' if ok_fps else 'FAIL'}")

    # Image size
    size_mb = _docker_image_size_mb(image)
    if size_mb is None:
        notes.append(f"image: {image} -> size unknown (docker not available?) -> FAIL")
        ok_img = False
    else:
        ok_img = size_mb <= img_max
        notes.append(
            f"image size: {size_mb:.1f} MB (max {img_max:.1f}) -> {'OK' if ok_img else 'FAIL'}"
        )

    overall = ok_p50 and ok_p95 and ok_fps and ok_img
    return overall, notes


def render(status: Dict[int, str]) -> str:
    greens = sum(1 for v in status.values() if v == GREEN)
    yellows = sum(1 for v in status.values() if v == YELLOW)
    reds = sum(1 for v in status.values() if v == RED)

    lines = []
    lines.append("# 24-Point Status Snapshot\n")
    lines.append(f"**Totals:** {GREEN} {greens} · {YELLOW} {yellows} · {RED} {reds}\n")
    lines.append("\n| # | Area | Status |")
    lines.append("|---:|------|:------:|")
    for idx, name in AREAS:
        lines.append(f"| {idx} | {name} | {status.get(idx, ' ')} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="-", help="'-' for stdout, else path to write")
    ap.add_argument("--image", default="northstrike-eval:latest")
    ap.add_argument("--perf-json", default="artifacts/perf.json")
    ap.add_argument("--budgets", default="budgets.yaml")
    args = ap.parse_args()

    # Start from baseline, then compute #18 live
    status = dict(BASELINE)

    ok18, notes18 = _check_edge_budgets(
        budgets_path=args.budgets,
        perf_json_path=args.perf_json,
        image=args.image,
    )
    status[18] = GREEN if ok18 else RED

    # Optional overrides if user wants to force statuses:
    overrides = _load_yaml("reports/status_overrides.yaml")
    if overrides:
        for k, v in overrides.items():
            try:
                k_i = int(k)
                if v in (GREEN, YELLOW, RED):
                    status[k_i] = v
            except Exception:
                pass

    out = render(status)
    if args.out == "-":
        print(out)
    else:
        with open(args.out, "w") as f:
            f.write(out)

    # If we printed to stdout and #18 changed, show the notes so you know why
    if sys.stdout and args.out == "-":
        print("\n[Edge Packaging & Perf Budgets]")
        for n in notes18:
            print(" -", n)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
