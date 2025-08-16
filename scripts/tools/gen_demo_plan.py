#!/usr/bin/env python3
"""
gen_demo_plan.py — deterministic QGroundControl .plan generator

Creates a rectangular mission around a given lat/lon at a fixed relative
altitude. Output is a QGC .plan JSON file compatible with PX4.

Usage (defaults are fine for our SITL world):
  python3 scripts/tools/gen_demo_plan.py --write-sha
"""

import argparse
import hashlib
import json
import math
from pathlib import Path


def meters_to_deg(lat_deg: float, east_m: float, north_m: float):
    """
    Convert local ENU meters (east, north) near lat_deg to degrees (dlat, dlon).
    Rough Earth radius approximation is sufficient for small rectangles.
    """
    lat_rad = math.radians(lat_deg)
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * math.cos(lat_rad) + 1e-12)
    return dlat, dlon


def make_rect(lat0: float, lon0: float, leg_x_m: float, leg_y_m: float):
    """
    Rectangle with corners:
      N of home, then NW, then W of home, then back to home.
    leg_x_m ~ east-west length, leg_y_m ~ north-south length.
    """
    dlat_n, dlon_e = meters_to_deg(lat0, east_m=leg_x_m, north_m=leg_y_m)
    # Start north of home so we visibly translate
    p1 = (lat0 + dlat_n, lon0)  # north
    p2 = (lat0 + dlat_n, lon0 - dlon_e)  # west
    p3 = (lat0, lon0 - dlon_e)  # south
    p4 = (lat0, lon0)  # back home
    return [p1, p2, p3, p4]


def build_qgc_plan(points, alt_m: float, lat0: float, lon0: float):
    """
    Build a QGC .plan dict with NAV_WAYPOINT (command=16), rel-alt frame (3).
    """
    items = []
    for i, (la, lo) in enumerate(points, start=1):
        items.append(
            {
                "type": "SimpleItem",
                "command": 16,  # MAV_CMD_NAV_WAYPOINT
                "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
                "doJumpId": i,
                "autoContinue": True,
                "params": [0, 0, 0, 0, la, lo, alt_m],
                "coordinate": [la, lo, alt_m],
            }
        )

    return {
        "fileType": "Plan",
        "groundStation": "QGroundControl",
        "version": 1,
        "geoFence": {"polygons": [], "circles": [], "version": 2},
        "rallyPoints": {"points": [], "version": 2},
        "mission": {
            "firmwareType": 12,  # PX4
            "vehicleType": 2,  # Multicopter
            "cruiseSpeed": 15,
            "hoverSpeed": 5,
            "plannedHomePosition": [lat0, lon0, 488.0],
            "version": 2,
            "items": items,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=47.397971, help="center lat (deg)")
    ap.add_argument("--lon", type=float, default=8.546164, help="center lon (deg)")
    ap.add_argument("--alt", type=float, default=10.0, help="relative altitude (m)")
    ap.add_argument("--leg-x", type=float, default=190.0, help="E-W leg length (m)")
    ap.add_argument("--leg-y", type=float, default=135.0, help="N-S leg length (m)")
    ap.add_argument(
        "--out",
        default="simulation/missions/v1.0/waypoints_demo.plan",
        help="output .plan path",
    )
    ap.add_argument(
        "--write-sha",
        action="store_true",
        help="also write sha256 file next to the plan",
    )
    args = ap.parse_args()

    pts = make_rect(args.lat, args.lon, args.leg_x, args.leg_y)
    plan = build_qgc_plan(pts, args.alt, args.lat, args.lon)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"✅ wrote {out} with {len(plan['mission']['items'])} items")

    if args.write_sha:
        sha = hashlib.sha256(out.read_bytes()).hexdigest()
        (out.with_suffix(out.suffix + ".sha256")).write_text(f"{sha}  {out.name}\n")
        print(f"🔐 sha256: {sha}")


if __name__ == "__main__":
    main()
