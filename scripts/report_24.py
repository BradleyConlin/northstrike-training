#!/usr/bin/env python3
"""Generate a markdown snapshot for the 24-point plan.

- Reads monitoring.yaml
- Calculates status using simple globs (green/yellow/red)
- Writes to STDOUT and (if set) $GITHUB_STEP_SUMMARY
- Also writes reports/24-point-status.md

Exit code is always 0 to avoid failing CI on reporting.
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from glob import glob as _glob
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # noqa: N816

EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


@dataclass
class Item:
    id: int
    name: str
    seed: str = "red"
    green_globs: List[str] | None = None
    yellow_globs: List[str] | None = None

    def compute_status(self, root: Path) -> str:
        # Count files (not dirs) matching patterns
        def count_files(patterns):
            if not patterns:
                return 0
            n = 0
            for pat in patterns:
                for m in _glob(str((root / pat)), recursive=True):
                    if Path(m).is_file():
                        n += 1
            return n

        g = count_files(self.green_globs)
        y = count_files(self.yellow_globs)

        # Per-area green thresholds (default 2); tighten for big buckets
        min_g_map = {
            "Path-Planning Algorithms": 5,
            "Flight-Control Algorithms": 5,
        }
        title = getattr(self, "title", getattr(self, "name", ""))
        min_g = min_g_map.get(title, 2)
        if g >= min_g:
            return "green"
        if g >= 1 or y >= 1:
            return "yellow"
        return self.seed


def load_items(cfg_path: Path) -> List[Item]:
    if yaml is None:
        raise SystemExit("PyYAML is required. Add 'pyyaml' to requirements if missing.")
    data: Dict[str, Any] = yaml.safe_load(cfg_path.read_text())
    items: List[Item] = []
    for row in data.get("items", []):
        items.append(
            Item(
                id=int(row["id"]),
                name=str(row["name"]),
                seed=str(row.get("seed", "red")),
                green_globs=list(row.get("green_globs", []) or []),
                yellow_globs=list(row.get("yellow_globs", []) or []),
            )
        )
    return items


def render_markdown(rows: List[tuple[int, str, str]]) -> str:
    g = sum(1 for _, _, s in rows if s == "green")
    y = sum(1 for _, _, s in rows if s == "yellow")
    r = sum(1 for _, _, s in rows if s == "red")
    lines = []
    lines.append("# 24-Point Status Snapshot")
    lines.append("")
    lines.append(f"**Totals:** {EMOJI['green']} {g} · {EMOJI['yellow']} {y} · {EMOJI['red']} {r}")
    lines.append("")
    lines.append("| # | Area | Status |")
    lines.append("|---:|------|:------:|")
    for i, name, status in rows:
        lines.append(f"| {i} | {name} | {EMOJI[status]} |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="monitoring.yaml")
    p.add_argument("--out", default="reports/24-point-status.md")
    p.add_argument("--ci", action="store_true", help="Also write to $GITHUB_STEP_SUMMARY if set")
    args = p.parse_args()

    root = Path(".").resolve()
    cfg = Path(args.config)
    items = load_items(cfg)
    rows = []
    for it in items:
        status = it.compute_status(root)
        rows.append((it.id, it.name, status))
    rows.sort(key=lambda t: t[0])

    md = render_markdown(rows)
    print(md)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md + "\n")

    step_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if args.ci and step_summary:
        Path(step_summary).write_text(md + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
