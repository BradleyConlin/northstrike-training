#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Tuple

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def point_in_bbox(lat: float, lon: float, poly: List[Dict[str, float]]) -> bool:
    if not poly:
        return True  # no geofence configured -> skip
    lats = [p["lat"] for p in poly]
    lons = [p["lon"] for p in poly]
    return (min(lats) <= lat <= max(lats)) and (min(lons) <= lon <= max(lons))


def check(plan: dict, limits: dict) -> Tuple[bool, List[str], List[str]]:
    issues, warns = [], []
    alt_max = float(limits.get("altitude_max_m", 120))
    wind_max = float(limits.get("wind_max_mps", 10))
    allow_night = bool(limits.get("allow_night", False))
    geofence_poly = (limits.get("geofence") or {}).get("polygon") or []

    name = plan.get("name")
    loc = plan.get("location") or {}
    lat, lon = float(loc.get("lat", 0.0)), float(loc.get("lon", 0.0))
    takeoff_agl = float((plan.get("timeline") or {}).get("takeoff_agl_m", 0.0))
    wind = plan.get("expected_wind_mps", None)
    night = bool(plan.get("night", False))

    if not name:
        issues.append("plan.name missing")
    if "location" not in plan:
        issues.append("plan.location missing")
    if "timeline" not in plan:
        issues.append("plan.timeline missing")
    if takeoff_agl > alt_max:
        issues.append(f"AGL {takeoff_agl} m exceeds limit {alt_max} m")
    if wind is not None and float(wind) > wind_max:
        issues.append(f"Wind {wind} m/s exceeds limit {wind_max} m/s")
    if night and not allow_night:
        issues.append("Night flag true but allow_night=false in limits")
    if not point_in_bbox(lat, lon, geofence_poly):
        issues.append("Location outside geofence polygon (bbox check)")

    if wind is None:
        warns.append("expected_wind_mps missing (set in plan)")
    if not geofence_poly:
        warns.append("No geofence polygon configured in limits; skipping geo check")

    return (len(issues) == 0), issues, warns


def main():
    ap = argparse.ArgumentParser(description="Validate flight plan against safety limits")
    ap.add_argument("--plan", default="mission/flight_plan.yaml")
    ap.add_argument("--limits", default="configs/safety/limits.yaml")
    ap.add_argument("--out-json", default="artifacts/safety_last_check.json")
    args = ap.parse_args()

    if not os.path.exists(args.plan):
        print(f"[safety] no plan at {args.plan}, skipping (OK)", file=sys.stderr)
        data = {"ok": True, "skipped": True, "issues": [], "warnings": ["no plan file"]}
        os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
        with open(args.out_json, "w") as f:
            json.dump(data, f, indent=2)
        return 0

    plan = load_yaml(args.plan)
    limits = load_yaml(args.limits)
    ok, issues, warns = check(plan, limits)
    out = {"ok": ok, "issues": issues, "warnings": warns, "plan": plan.get("name")}
    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with open(args.out_json, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[safety] ok={ok} issues={len(issues)} warnings={len(warns)}")
    if not ok:
        for i in issues:
            print(" -", i, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
