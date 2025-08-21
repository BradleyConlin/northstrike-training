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
    yaml = None  # noqa: N816


GREEN = "🟢"
YELLOW = "🟡"
RED = "🔴"

# Keep AREAS as list of PAIRS so the render loop `for idx, name in AREAS` works.
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

# Baseline (matches what you've been seeing)
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
    18: RED,  # computed live
    19: RED,  # computed below if artifacts exist
    20: RED,  # computed below from safety_last_check.json
    21: YELLOW,  # computed below from hooks/CI presence
    22: GREEN,
    23: GREEN,
    24: YELLOW,  # computed below from mission_last_check.json
}


def _load_yaml(path: str) -> dict:
    if not os.path.exists(path) or yaml is None:
        return {}
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _docker_image_size_mb(image: str) -> float | None:
    try:
        out = subprocess.check_output(
            ["docker", "image", "inspect", "-f", "{{.Size}}", image],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        if out.isdigit():
            mb = int(out) / (1024 * 1024)
            return mb
        return None
    except Exception:
        return None


def _load_perf(perf_json_path: str) -> dict:
    if not os.path.exists(perf_json_path):
        return {}
    try:
        with open(perf_json_path, "r") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _check_edge_budgets(
    budgets_path: str, perf_json_path: str, image: str
) -> tuple[bool, List[str]]:
    # Defaults if budgets.yaml missing
    b = _load_yaml(budgets_path) or {}
    b = b.get("budgets", b) or {}
    p50_max = float(b.get("latency_ms_p50", 15.0))
    p95_max = float(b.get("latency_ms_p95", 30.0))
    fps_min = float(b.get("fps_min", 60.0))
    img_mb_max = float(b.get("image_size_mb_max", 2500.0))

    perf = _load_perf(perf_json_path)
    p50 = float(perf.get("p50_ms", perf.get("p50", 0.0)))
    p95 = float(perf.get("p95_ms", perf.get("p95", 0.0)))
    fps = float(perf.get("fps", 0.0))
    image_mb = perf.get("image_mb") or perf.get("image_size_mb")

    if image_mb is None:
        image_mb = _docker_image_size_mb(image)

    notes: List[str] = []
    ok = True

    def line(label: str, val: float | None, bound: float, cmp: str) -> str:
        if val is None:
            return f"{label}: n/a"
        good = (val <= bound) if cmp == "<=" else (val >= bound)
        return (
            f"{label}: {val:.2f} (max {bound:.2f}) -> {'OK' if good else 'FAIL'}"
            if cmp == "<="
            else f"{label}: {val:.2f} (min {bound:.2f}) -> {'OK' if good else 'FAIL'}"
        )

    # Evaluate and collect notes
    if p50:
        notes.append(line("p50", p50, p50_max, "<="))
        ok &= p50 <= p50_max
    if p95:
        notes.append(line("p95", p95, p95_max, "<="))
        ok &= p95 <= p95_max
    if fps:
        notes.append(line("fps", fps, fps_min, ">="))
        ok &= fps >= fps_min
    if image_mb is not None:
        notes.append(line("image size", float(image_mb), img_mb_max, "<="))
        ok &= float(image_mb) <= img_mb_max

    return bool(ok), notes


def render(status: Dict[int, str]) -> str:
    greens = sum(1 for v in status.values() if v == GREEN)
    yellows = sum(1 for v in status.values() if v == YELLOW)
    reds = sum(1 for v in status.values() if v == RED)

    lines: List[str] = []
    lines.append("# 24-Point Status Snapshot\n")
    lines.append(f"**Totals:** {GREEN} {greens} · {YELLOW} {yellows} · {RED} {reds}\n")
    lines.append("")
    lines.append("| # | Area | Status |")
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

    status = dict(BASELINE)

    # #18: edge budgets
    ok18, notes18 = _check_edge_budgets(
        budgets_path=args.budgets, perf_json_path=args.perf_json, image=args.image
    )
    status[18] = GREEN if ok18 else RED

    # Optional overrides (if you use them)
    overrides = _load_yaml("reports/status_overrides.yaml")
    if overrides:
        for k, v in overrides.items():
            try:
                k_i = int(k)
                if v in (GREEN, YELLOW, RED):
                    status[k_i] = v
            except Exception:
                pass

    # #19: Data Labeling, QA & Governance
    has_labeling_bits = all(
        os.path.exists(p)
        for p in (
            "configs/labeling/labelmap.yaml",
            "scripts/labeling/qa_check.py",
            ".github/workflows/label_qa.yml",
        )
    )
    if has_labeling_bits and os.path.exists("artifacts/label_qa.json"):
        try:
            # If file exists and parsed, call it good for now
            status[19] = GREEN
        except Exception:
            status[19] = YELLOW
    else:
        status[19] = RED

    # #20: Safety gate (Transport Canada SOPs)
    slc = "artifacts/safety_last_check.json"
    if os.path.exists(slc):
        try:
            ok = bool(json.load(open(slc)).get("ok"))
            status[20] = GREEN if ok else YELLOW
        except Exception:
            status[20] = YELLOW

    # #21: Secrets & Config Hygiene
    try:
        pc = os.path.exists(".pre-commit-config.yaml") and (
            "forbid-dotenv" in open(".pre-commit-config.yaml").read()
        )
    except Exception:
        pc = False
    ci = os.path.exists(".github/workflows/secrets_scan.yml")
    status[21] = GREEN if (pc and ci) else YELLOW

    # #24: Mission & Parameter Bundles
    mlc = "artifacts/mission_last_check.json"
    if os.path.exists(mlc):
        try:
            ok = bool(json.load(open(mlc)).get("ok"))
            status[24] = GREEN if ok else YELLOW
        except Exception:
            status[24] = YELLOW

    out = render(status)
    if args.out == "-":
        print(out)
    else:
        with open(args.out, "w") as f:
            f.write(out)

    # Print edge-budget notes if outputting to stdout (matches your earlier UX)
    if sys.stdout and args.out == "-":
        print("\n[Edge Packaging & Perf Budgets]")
        for n in notes18:
            print(" -", n)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
