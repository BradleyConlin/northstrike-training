#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mission runner (PX4 SITL + MAVSDK) for Python 3.10.

- Mission upload + start (Navigator)
- If no XY motion after start, fallback to action.goto_location() per waypoint
- No asyncio.TaskGroup (Py3.10 friendly)
- Tight acceptance (NAV_ACC_RAD) + start-at-first (MIS_DIST_1WP)
- Records CSV to datasets/flight_logs/mission_*.csv and updates mission_latest.csv
- Forces RTL at the end so we don't hang waiting for disarm
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from dataclasses import dataclass
from math import cos, radians, sqrt
from pathlib import Path
from time import time

from mavsdk import System
from mavsdk.mission import MissionError, MissionItem, MissionPlan

# --------------------------- Plan parsing ---------------------------


@dataclass
class Waypoint:
    lat: float
    lon: float
    alt_rel: float  # meters AGL (relative to home)


def parse_qgc_plan(path: Path) -> list[Waypoint]:
    d = json.loads(path.read_text())
    items = d.get("mission", {}).get("items", [])
    wps: list[Waypoint] = []
    for it in items:
        if "coordinate" in it and isinstance(it["coordinate"], list) and len(it["coordinate"]) >= 3:
            lat, lon, alt = it["coordinate"][:3]
            wps.append(Waypoint(float(lat), float(lon), float(alt)))
            continue
        params = it.get("params", [])
        if isinstance(params, list) and len(params) >= 7:
            lat, lon, alt = params[4:7]
            wps.append(Waypoint(float(lat), float(lon), float(alt)))
    if not wps:
        raise ValueError("No waypoints found in plan.")
    return wps


# ----------------------- MissionItem builder ------------------------


def build_item(wp: Waypoint) -> MissionItem:
    """Explicit fields so PX4 must actually reach each item."""
    return MissionItem(
        latitude_deg=wp.lat,
        longitude_deg=wp.lon,
        relative_altitude_m=wp.alt_rel,
        speed_m_s=0.0,  # 0 = default
        is_fly_through=False,  # must reach the point
        gimbal_pitch_deg=float("nan"),
        gimbal_yaw_deg=float("nan"),
        camera_action=MissionItem.CameraAction.NONE,
        loiter_time_s=0.0,
        camera_photo_interval_s=0.0,
        acceptance_radius_m=0.5,
        yaw_deg=float("nan"),
        camera_photo_distance_m=0.0,
        vehicle_action=MissionItem.VehicleAction.NONE,
    )


# ---------------------------- Telemetry CSV -------------------------

CSV_HDR = [
    "t",
    "lat",
    "lon",
    "abs_alt_m",
    "rel_alt_m",
    "vn",
    "ve",
    "vd",
    "battery_pct",
    "in_air",
]


async def telemetry_recorder(drone: System, out_path: Path, hz: int) -> None:
    """Py3.10-friendly recorder (no TaskGroup)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    latest = {
        "lat": None,
        "lon": None,
        "abs_alt_m": None,
        "rel_alt_m": None,
        "vn": None,
        "ve": None,
        "vd": None,
        "battery_pct": None,
        "in_air": 0,
    }
    stop = asyncio.Event()

    async def sub_position():
        try:
            async for p in drone.telemetry.position():
                latest["lat"] = p.latitude_deg
                latest["lon"] = p.longitude_deg
                latest["abs_alt_m"] = p.absolute_altitude_m
                latest["rel_alt_m"] = p.relative_altitude_m
                if stop.is_set():
                    break
        except Exception:
            pass

    async def sub_velocity():
        try:
            async for v in drone.telemetry.velocity_ned():
                latest["vn"] = v.north_m_s
                latest["ve"] = v.east_m_s
                latest["vd"] = v.down_m_s
                if stop.is_set():
                    break
        except Exception:
            pass

    async def sub_battery():
        try:
            async for b in drone.telemetry.battery():
                latest["battery_pct"] = b.remaining_percent * 100.0
                if stop.is_set():
                    break
        except Exception:
            pass

    async def sub_in_air():
        try:
            async for ia in drone.telemetry.in_air():
                latest["in_air"] = 1 if ia else 0
                if stop.is_set():
                    break
        except Exception:
            pass

    tasks = [
        asyncio.create_task(sub_position(), name="sub_position"),
        asyncio.create_task(sub_velocity(), name="sub_velocity"),
        asyncio.create_task(sub_battery(), name="sub_battery"),
        asyncio.create_task(sub_in_air(), name="sub_in_air"),
    ]

    period = 1.0 / float(hz)
    start = time()

    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HDR)
        try:
            while not stop.is_set():
                t_rel = time() - start
                row = [
                    f"{t_rel:.3f}",
                    _fmt(latest["lat"]),
                    _fmt(latest["lon"]),
                    _fmt(latest["abs_alt_m"]),
                    _fmt(latest["rel_alt_m"]),
                    _fmt(latest["vn"]),
                    _fmt(latest["ve"]),
                    _fmt(latest["vd"]),
                    _fmt(latest["battery_pct"]),
                    latest["in_air"],
                ]
                w.writerow(row)
                await asyncio.sleep(period)
        finally:
            stop.set()
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def _fmt(x):
    return "" if x is None else (f"{x:.9f}" if isinstance(x, float) else str(x))


# ----------------------------- Helpers ------------------------------


async def wait_connected(drone: System) -> None:
    async for cs in drone.core.connection_state():
        if cs.is_connected:
            break


async def wait_ekf_ready(drone: System) -> None:
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok:
            break


async def set_param_float(drone: System, name: str, val: float) -> None:
    try:
        await drone.param.set_param_float(name, float(val))
        print(f"  • {name} <- {val}")
    except Exception as e:
        print(f"  • {name} not set: {e}")


async def first(ait):
    async for x in ait:
        return x
    raise RuntimeError("no items")


def meters_xy_from(lat0, lon0, lat1, lon1) -> float:
    k_lat = 111_320.0
    k_lon = k_lat * cos(radians(lat0 if lat0 is not None else 0.0))
    dx = (lat1 - lat0) * k_lat
    dy = (lon1 - lon0) * k_lon
    return sqrt(dx * dx + dy * dy)


# ----------------------------- Fallback (Goto) -----------------------


async def fly_goto_fallback(drone: System, wps: list[Waypoint]) -> None:
    print("⚠️  Fallback: using action.goto_location() for each waypoint")
    # Arm if needed
    try:
        await drone.action.arm()
    except Exception:
        pass

    # Estimate home AMSL to convert rel->amsl
    pos = await first(drone.telemetry.position())
    home_amsl = pos.absolute_altitude_m - pos.relative_altitude_m

    # Visit each waypoint
    for i, wp in enumerate(wps, 1):
        tgt_amsl = home_amsl + wp.alt_rel
        print(
            f"  → GOTO {i}/{len(wps)}: lat={wp.lat:.6f}, lon={wp.lon:.6f}, alt_amsl={tgt_amsl:.1f}"
        )
        try:
            await drone.action.goto_location(wp.lat, wp.lon, tgt_amsl, float("nan"))
        except Exception as e:
            print(f"    goto failed: {e}")
            continue

        # Wait until within ~1.5 m (or timeout)
        ok = False
        t0 = time()
        while time() - t0 < 90:
            p = await first(drone.telemetry.position())
            d = meters_xy_from(wp.lat, wp.lon, p.latitude_deg, p.longitude_deg)
            if d <= 1.5:
                ok = True
                break
            await asyncio.sleep(0.3)
        print("    ✓ reached" if ok else "    ✖ timeout, continuing")

    # Finish with RTL
    print("🏁 Fallback complete → RTL")
    try:
        await drone.action.return_to_launch()
    except Exception:
        pass

    # Wait until landed/disarmed
    async for ia in drone.telemetry.in_air():
        if not ia:
            break


# ----------------------------- Main mission --------------------------


async def fly_mission(
    drone: System, items: list[MissionItem], wps_for_fallback: list[Waypoint]
) -> None:
    plan = MissionPlan(items)
    print("⬆️  Uploading mission…")
    await asyncio.wait_for(drone.mission.upload_mission(plan), timeout=10)
    print("✅ Mission upload OK")

    print("🔒 Arming…")
    await asyncio.wait_for(drone.action.arm(), timeout=10)

    print("▶️  Starting mission…")
    await asyncio.wait_for(drone.mission.start_mission(), timeout=10)
    print("⏯️  Mission started")

    # Check early motion
    try:
        p0 = await asyncio.wait_for(first(drone.telemetry.position()), 5)
        lat0, lon0 = p0.latitude_deg, p0.longitude_deg
        await asyncio.sleep(8.0)
        p1 = await asyncio.wait_for(first(drone.telemetry.position()), 5)
        moved_m = meters_xy_from(lat0, lon0, p1.latitude_deg, p1.longitude_deg)
    except Exception:
        moved_m = 0.0

    if moved_m < 5.0:
        print(f"⚠️  Little/no XY motion after start (~{moved_m:.1f} m) — switching to fallback.")
        await fly_goto_fallback(drone, wps_for_fallback)
        return

    # Otherwise, monitor progress to completion
    async for prog in drone.mission.mission_progress():
        print(f"… progress {prog.current}/{prog.total}")
        if prog.current == prog.total and prog.total > 0:
            break

    print("✅ Mission complete")
    print("🛬 RTL + wait for disarm…")
    try:
        await drone.action.return_to_launch()
    except Exception:
        pass
    async for ia in drone.telemetry.in_air():
        if not ia:
            break


# ----------------------------- Orchestrator --------------------------


async def main(plan_path: Path, hz: int) -> None:
    print(f"📋 Loading plan: {plan_path}")
    wps = parse_qgc_plan(plan_path)
    print(f"📦 Parsed {len(wps)} waypoints")

    items = [build_item(w) for w in wps]
    print(f"🧱 Built {len(items)} MissionItems")

    # Connect (udp://:14540 = broadest compatibility with PX4 SITL)
    conn = "udp://:14540"
    print(f"🔌 Connecting to PX4 ({conn})…")
    drone = System()
    await drone.connect(system_address=conn)
    await wait_connected(drone)
    print("✅ Connected to PX4")
    await wait_ekf_ready(drone)
    print("✅ EKF healthy & home set")

    # Tighten mission acceptance & start-at-first
    print("🧰 Setting PX4 mission params:")
    await set_param_float(drone, "NAV_ACC_RAD", 0.5)  # meters
    await set_param_float(drone, "MIS_DIST_1WP", 1.0)  # meters
    await set_param_float(drone, "MIS_TAKEOFF_ALT", 10.0)

    # Start recorder
    out_dir = Path("datasets/flight_logs")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"mission_{_ts()}.csv"
    rec_task = asyncio.create_task(telemetry_recorder(drone, csv_path, hz), name="recorder")

    # Fly (mission → fallback if needed)
    try:
        await fly_mission(drone, items, wps)
    except MissionError as e:
        print(f"❌ Mission error: {e}")
        raise
    finally:
        rec_task.cancel()
        await asyncio.gather(rec_task, return_exceptions=True)

    # Symlink "latest"
    latest = out_dir / "mission_latest.csv"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(csv_path.name)
    except Exception:
        pass

    print(f"🧾 Log: {csv_path}")
    print(f"🔗 Symlink: {latest} -> {csv_path.name}")


def _ts() -> str:
    import datetime as _dt

    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


# ------------------------------- CLI --------------------------------


def cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, required=True, help="QGC .plan file")
    ap.add_argument("--hz", type=int, default=20, help="telemetry record rate")
    return ap.parse_args()


if __name__ == "__main__":
    args = cli()
    asyncio.run(main(args.plan, args.hz))
