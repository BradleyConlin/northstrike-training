#!/usr/bin/env python3
"""
Single-process mission pipeline:
 - Connect to PX4 (udpin://0.0.0.0:14540)
 - Parse a QGC .plan (waypoints)
 - Convert to MAVSDK MissionItems
 - Upload with retries + timeouts (instrumented prints)
 - Start and monitor mission
 - Record telemetry to CSV (same System instance)
 - Symlink mission_latest.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

from mavsdk import System
from mavsdk.mission import MissionError, MissionItem, MissionPlan

# ----------------------------- plan parsing ---------------------------------


@dataclass
class Wp:
    lat: float
    lon: float
    rel_alt_m: float


def parse_qgc_plan(plan_path: Path) -> List[Wp]:
    data = json.loads(plan_path.read_text())
    mission = data.get("mission", {})
    items = mission.get("items", [])
    wps: List[Wp] = []

    for it in items:
        # QGC "SimpleItem" usually has "coordinate": [lat, lon, rel_alt]
        coord = it.get("coordinate")
        if isinstance(coord, list) and len(coord) >= 3:
            lat, lon, rel = float(coord[0]), float(coord[1]), float(coord[2])
            wps.append(Wp(lat=lat, lon=lon, rel_alt_m=rel))
            continue

        # Some plans stick it under "params" (rare in our use)
        params = it.get("params")
        if isinstance(params, list) and len(params) >= 8:
            # QGC PARAM mapping (approx): [cmd, p1, p2, p3, p4, lat, lon, alt]
            lat, lon, rel = float(params[5]), float(params[6]), float(params[7])
            wps.append(Wp(lat=lat, lon=lon, rel_alt_m=rel))

    if not wps:
        raise ValueError("No waypoints found in plan.")
    return wps


def to_mavsdk_items(wps: List[Wp]) -> List[MissionItem]:
    """Build MissionItems, handling different MAVSDK signatures gracefully."""
    items: List[MissionItem] = []

    # Try to discover nested CameraAction enum if present (older/newer API diff)
    cam_enum = getattr(MissionItem, "CameraAction", None)
    cam_none = cam_enum.NONE if cam_enum else None

    for w in wps:
        # Try the fullest signature available
        try:
            kwargs = dict(
                latitude_deg=w.lat,
                longitude_deg=w.lon,
                relative_altitude_m=w.rel_alt_m,
                speed_m_s=5.0,
                is_fly_through=False,
                gimbal_pitch_deg=0.0,
                gimbal_yaw_deg=0.0,
                loiter_time_s=0.0,
                camera_photo_interval_s=0.0,
                acceptance_radius_m=2.0,
                yaw_deg=float("nan"),
                camera_photo_distance_m=0.0,
            )
            if cam_enum:
                kwargs["camera_action"] = cam_none
            item = MissionItem(**kwargs)
        except TypeError:
            # Try a mid-level signature (no acceptance/yaw/photo_distance)
            try:
                kwargs = dict(
                    latitude_deg=w.lat,
                    longitude_deg=w.lon,
                    relative_altitude_m=w.rel_alt_m,
                    speed_m_s=5.0,
                    is_fly_through=False,
                    gimbal_pitch_deg=0.0,
                    gimbal_yaw_deg=0.0,
                    loiter_time_s=0.0,
                    camera_photo_interval_s=0.0,
                )
                if cam_enum:
                    kwargs["camera_action"] = cam_none
                item = MissionItem(**kwargs)
            except TypeError:
                # Oldest minimal signature
                item = MissionItem(
                    latitude_deg=w.lat,
                    longitude_deg=w.lon,
                    relative_altitude_m=w.rel_alt_m,
                    speed_m_s=5.0,
                    is_fly_through=False,
                    gimbal_pitch_deg=0.0,
                    gimbal_yaw_deg=0.0,
                )
        items.append(item)

    return items


# ------------------------------ telemetry -----------------------------------


async def record_csv(drone: System, out_csv: Path, hz: float, stop: asyncio.Event) -> None:
    dt = max(1.0 / float(hz), 0.02)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    pos_a = drone.telemetry.position()
    vel_a = drone.telemetry.velocity_ned()
    bat_a = drone.telemetry.battery()
    air_a = drone.telemetry.in_air()

    async def _next(aiter):
        return await aiter.__anext__()

    t0 = asyncio.get_event_loop().time()
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
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
        )

        while not stop.is_set():
            pos = await _next(pos_a)
            vel = await _next(vel_a)
            bat = await _next(bat_a)
            in_air = await _next(air_a)

            t_now = asyncio.get_event_loop().time() - t0
            w.writerow(
                [
                    round(t_now, 3),
                    getattr(pos, "latitude_deg", 0.0),
                    getattr(pos, "longitude_deg", 0.0),
                    getattr(pos, "absolute_altitude_m", 0.0),
                    getattr(pos, "relative_altitude_m", 0.0),
                    getattr(vel, "north_m_s", 0.0),
                    getattr(vel, "east_m_s", 0.0),
                    getattr(vel, "down_m_s", 0.0),
                    round(getattr(bat, "remaining_percent", 1.0) * 100.0, 1),
                    1 if in_air else 0,
                ]
            )
            await asyncio.sleep(dt)


# ------------------------------ mission ops ---------------------------------


async def wait_ekf_ok(drone: System) -> None:
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok and h.is_local_position_ok:
            break
        await asyncio.sleep(0.2)


async def upload_with_retry2(drone: System, plan: MissionPlan, attempts: int = 3) -> None:
    """Clear existing mission and upload with retries + timeouts + prints."""
    for i in range(1, attempts + 1):
        try:
            print(f"🧹 Clearing mission (attempt {i}/{attempts})")
            await asyncio.wait_for(drone.mission.clear_mission(), timeout=5)
            await asyncio.sleep(0.2)

            print("⬆️  Uploading mission...")
            await asyncio.wait_for(drone.mission.upload_mission(plan), timeout=10)
            print("✅ Mission upload OK")
            return
        except MissionError as e:
            print(f"⚠️  MissionError during upload: {e}")
        except asyncio.TimeoutError:
            print("⏳ Upload/clear timed out")
        if i == attempts:
            raise
        await asyncio.sleep(1.0)


async def fly_mission(drone: System, items: List[MissionItem]) -> None:
    plan = MissionPlan(items)

    await upload_with_retry2(drone, plan, attempts=3)

    print("▶️  Starting mission...")
    await asyncio.sleep(0.3)
    await drone.mission.start_mission()
    print("⏯️  Mission started")

    got_total = 0
    async for prog in drone.mission.mission_progress():
        total = prog.total_mission_items
        cur = prog.current
        if total != got_total and total > 0:
            print(f"▶️  Mission started ({total} items)")
            got_total = total
        if total > 0 and cur >= total:
            print("✅ Mission complete")
            break


# --------------------------------- main -------------------------------------


async def connect_drone() -> System:
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    async for state in drone.core.connection_state():
        if state.is_connected:
            break
    print("✅ Connected to PX4")
    return drone


def out_csv_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("datasets/flight_logs") / f"mission_{ts}.csv"


async def main(plan_path: Path, hz: int) -> None:
    print(f"📋 Loading plan: {plan_path}")
    wps = parse_qgc_plan(plan_path)
    print(f"📦 Parsed {len(wps)} waypoints")

    print("🧱 Converting waypoints → MissionItems")
    items = to_mavsdk_items(wps)
    print(f"🧱 Built {len(items)} MissionItems")

    drone = await connect_drone()
    print("✅ EKF healthy & home set (waiting)...")
    await wait_ekf_ok(drone)
    print("✅ EKF healthy & home set")

    out_csv = out_csv_path()
    stop_evt = asyncio.Event()
    rec_task = asyncio.create_task(record_csv(drone, out_csv, float(hz), stop_evt))

    try:
        await fly_mission(drone, items)

        async for in_air in drone.telemetry.in_air():
            if not in_air:
                print("✅ Landed & disarmed")
                break
    finally:
        stop_evt.set()
        await asyncio.wait_for(rec_task, timeout=5)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    latest = out_csv.parent / "mission_latest.csv"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(out_csv.name)
    except Exception:
        pass

    print(f"🧾 Log: {out_csv}")
    print(f"🔗 Symlink: {latest} -> {out_csv.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, required=True, help="Path to QGC .plan file")
    ap.add_argument("--hz", type=int, default=20, help="Telemetry sampling rate")
    args = ap.parse_args()

    asyncio.run(main(args.plan, args.hz))
