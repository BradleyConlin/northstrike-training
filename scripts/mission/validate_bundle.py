#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import yaml


def load_yaml(path: str) -> Any:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def basic_validate(
    mission: Dict[str, Any], params: Dict[str, Any] | None
) -> tuple[bool, list[str], list[str]]:
    issues, warnings = [], []
    need = ["name", "frame", "takeoff_alt_m", "waypoints"]
    for k in need:
        if k not in mission:
            issues.append(f"mission.{k} missing")
    if mission.get("frame") != "home_relative":
        issues.append("mission.frame must be 'home_relative'")
    for i, wp in enumerate(mission.get("waypoints", [])):
        for k in ("north_m", "east_m", "alt_m"):
            if k not in wp:
                issues.append(f"waypoint[{i}].{k} missing")
        if wp.get("alt_m", 0) < 2:
            issues.append(f"waypoint[{i}].alt_m < 2 m")
    if params:
        for k, v in params.items():
            if not isinstance(k, str) or not k.isupper():
                warnings.append(f"param key looks odd: {k}")
            if not isinstance(v, (int, float)):
                issues.append(f"param {k} must be number")
    return (len(issues) == 0, issues, warnings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default="mission/bundles/demo_square", help="bundle directory")
    ap.add_argument("--schema", default="schemas/mission_bundle.schema.json")
    ap.add_argument("--out-json", default="artifacts/mission_last_check.json")
    args = ap.parse_args()

    mission = load_yaml(os.path.join(args.bundle, "mission.yaml"))
    params_path = os.path.join(args.bundle, "params.yaml")
    params = load_yaml(params_path) if os.path.exists(params_path) else None

    ok, issues, warnings = basic_validate(mission, params)
    out = {
        "ok": ok,
        "issues": issues,
        "warnings": warnings,
        "bundle": args.bundle,
        "mission": mission.get("name"),
    }
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[bundle-validate] ok={ok} issues={len(issues)} warnings={len(warnings)}")
    if not ok:
        for e in issues:
            print(" -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
