#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mission pipeline (single process): load QGC .plan → connect to PX4 (SITL) →
upload + start mission → record telemetry CSV → update mission_latest.csv.

- Uses udpin:// (correct endpoint for MAVSDK)
- Explicit arm() before start (helps SITL)
- Robust MissionItem builder across MAVSDK versions (signature introspection)
- Timeouts + clear progress prints so you always know what’s happening

CSV schema (matches datasets/schema_v1.json):
t,lat,lon,abs_alt_m,rel_alt_m,vn,ve,vd,battery_pct,in_air
"""

import argparse
import asyncio
import csv
import inspect
import json
from math import nan
from pathlib import Path
from time import monotonic

from mavsdk import System
from mavsdk.mission import MissionError, MissionItem, MissionPlan

# ---------------------------- Utilities -------------------------------------


def parse_qgc_plan(path: Path):
    """Return list of (lat, lon, rel_alt_m) from a QGC .plan file."""
    data = json.loads(path.read_text())
    items = data.get("mission", {}).get("items", [])
    if not items:
        raise ValueError("No waypoints found in plan.")

    wps = []
    for it in items:
        # Prefer "coordinate": [lat, lon, alt]
        coord = it.get("coordinate")
        if isinstance(coord, list) and len(coord) >= 3:
            lat, lon, alt = float(coord[0]), float(coord[1]), float(coord[2])
            wps.append((lat, lon, alt))
            continue
        # Fallback: QGC "params" (index 4..6) when present
        params = it.get("params", [])
        if isinstance(params, list) and len(params) >= 7:
            lat, lon, alt = float(params[4]), float(params[5]), float(params[6])
            wps.append((lat, lon, alt))

    if not wps:
        raise ValueError("No usable waypoint coordinates in plan.")
    return wps


def to_mavsdk_items(waypoints):
    """
    Convert simple (lat, lon, rel_alt) tuples to a MAVSDK MissionItem list.
    Cross-version safe: we introspect MissionItem signature and pass only
    supported kwargs; missing enum fields default to 0.
    """
    sig = inspect.signature(MissionItem)
    accepted = set(sig.parameters.keys())

    # Some SDK builds expect enum values; treat 0 as "NONE".
    CAM_NONE = 0
    VEH_NONE = 0

    out = []
    for lat, lon, rel_alt in waypoints:
        base = dict(
            latitude_deg=lat,
            longitude_deg=lon,
            relative_altitude_m=rel_alt,
            speed_m_s=5.0,
            is_fly_through=False,
            gimbal_pitch_deg=nan,
            gimbal_yaw_deg=nan,
            loiter_time_s=0.0,
            camera_action=CAM_NONE,
            camera_photo_interval_s=0.0,
            acceptance_radius_m=2.0,
            yaw_deg=nan,
            camera_photo_distance_m=0.0,
            vehicle_action=VEH_NONE,
        )
        # keep only keys supported by the installed MAVSDK
        filtered = {k: v for k, v in base.items() if k in accepted}
        out.append(MissionItem(**filtered))
    return out


async def connect_px4() -> System:
    print("🔌 Connecting to PX4 (udpin://0.0.0.0:14540)…")
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    # Wait until MAVSDK reports a system is discovered
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected to PX4")
            break

    # Wait for EKF/home ok
    async for health in drone.telemetry.health():
        if health.is_home_position_ok and health.is_global_position_ok:
            print("✅ EKF healthy & home set")
            break
    return drone


async def upload_with_retry(drone: System, plan: MissionPlan, attempts: int = 3):
    for i in range(1, attempts + 1):
        try:
            # Clearing first helps avoid PROTOCOL_ERROR across runs
            try:
                await drone.mission.clear_mission()
                await asyncio.sleep(0.3)
            except Exception:
                pass
            print("⬆️  Uploading mission…")
            await asyncio.wait_for(drone.mission.upload_mission(plan), timeout=10)
            print("✅ Mission upload OK")
            return
        except (MissionError, asyncio.TimeoutError) as e:
            print(f"⚠️  upload_mission attempt {i}/{attempts} failed: {e}")
            if i == attempts:
                raise
            await asyncio.sleep(1.0)


async def run_mission(drone: System):
    # Explicit arm helps SITL; if it’s already armed, that’s fine.
    try:
        print("🔓 Arming…")
        await asyncio.wait_for(drone.action.arm(), timeout=5)
        print("✅ Armed")
    except Exception as e:
        print(f"ℹ️  arm() skipped/failed ({e}); mission may auto-arm.")

    print("▶️  Starting mission…")
    await asyncio.sleep(0.3)
    await drone.mission.start_mission()
    print("⏯️  Mission start requested")

    # Quick confirmation of airborne
    async def _wait_airborne():
        async for ia in drone.telemetry.in_air():
            if ia:
                return

    try:
        await asyncio.wait_for(_wait_airborne(), timeout=10)
        print("🛫 Airborne")
    except asyncio.TimeoutError:
        print("⚠️  Not airborne after 10s; continuing anyway…")

    # Progress watcher (with timeout in case something stalls)
    async def _wait_progress():
        last_print = monotonic()
        async for prog in drone.mission.mission_progress():
            if prog.total > 0:
                now = monotonic()
                if now - last_print > 0.5:
                    print(f"… progress {prog.current}/{prog.total}")
                    last_print = now
            if prog.total > 0 and prog.current >= prog.total:
                return

    try:
        await asyncio.wait_for(_wait_progress(), timeout=300)
        print("✅ Mission complete")
    except asyncio.TimeoutError:
        print("⚠️  Mission progress timeout (5 min). Requesting RTL.")
        try:
            await drone.action.return_to_launch()
        except Exception:
            pass

    # Ensure landed
    async def _wait_landed():
        async for ia in drone.telemetry.in_air():
            if not ia:
                return

    try:
        await asyncio.wait_for(_wait_landed(), timeout=120)
        print("✅ Landed & disarmed")
    except asyncio.TimeoutError:
        print("⚠️  Landed wait timeout")


async def record_csv(drone: System, out_csv: Path, hz: int, stop_evt: asyncio.Event):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    period = 1.0 / max(1, hz)

    # async generators
    pos_a = drone.telemetry.position()
    vel_a = drone.telemetry.velocity_ned()
    bat_a = drone.telemetry.battery()
    in_air_a = drone.telemetry.in_air()

    # prime streams
    pos = await pos_a.__anext__()
    vel = await vel_a.__anext__()
    bat = await bat_a.__anext__()
    in_air = await in_air_a.__anext__()

    t0 = monotonic()
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["t", "lat", "lon", "abs_alt_m", "rel_alt_m", "vn", "ve", "vd", "battery_pct", "in_air"]
        )
        while not stop_evt.is_set():
            # sample latest
            try:
                pos = await asyncio.wait_for(pos_a.__anext__(), timeout=0.0)
            except Exception:
                pass
            try:
                vel = await asyncio.wait_for(vel_a.__anext__(), timeout=0.0)
            except Exception:
                pass
            try:
                bat = await asyncio.wait_for(bat_a.__anext__(), timeout=0.0)
            except Exception:
                pass
            try:
                in_air = await asyncio.wait_for(in_air_a.__anext__(), timeout=0.0)
            except Exception:
                pass

            t = monotonic() - t0
            w.writerow(
                [
                    f"{t:.3f}",
                    getattr(pos, "latitude_deg", float("nan")),
                    getattr(pos, "longitude_deg", float("nan")),
                    getattr(pos, "absolute_altitude_m", float("nan")),
                    getattr(pos, "relative_altitude_m", float("nan")),
                    getattr(vel, "north_m_s", float("nan")),
                    getattr(vel, "east_m_s", float("nan")),
                    getattr(vel, "down_m_s", float("nan")),
                    (
                        round(getattr(bat, "remaining_percent", 1.0) * 100.0, 1)
                        if hasattr(bat, "remaining_percent")
                        else float("nan")
                    ),
                    1 if bool(in_air) else 0,
                ]
            )
            await asyncio.sleep(period)
    print(f"🧾 Log: {out_csv}")


# ---------------------------- Main ------------------------------------------


async def main(plan_path: Path, hz: int):
    print(f"📋 Loading plan: {plan_path}")
    wps = parse_qgc_plan(plan_path)
    print(f"📦 Parsed {len(wps)} waypoints")

    items = to_mavsdk_items(wps)
    print(f"🧱 Built {len(items)} MissionItems")

    drone = await connect_px4()

    plan = MissionPlan(items)
    await upload_with_retry(drone, plan, attempts=3)

    # start recorder
    from datetime import datetime

    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path("datasets/flight_logs") / f"mission_{ts_str}.csv"
    stop_evt = asyncio.Event()
    rec_task = asyncio.create_task(record_csv(drone, out, hz, stop_evt))

    try:
        await run_mission(drone)
    finally:
        stop_evt.set()
        with contextlib.suppress(Exception):
            await rec_task

    # Update "latest" symlink for convenience
    latest = out.parent / "mission_latest.csv"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(out.name)
        print(f"🔗 Symlink: {latest} -> {out.name}")
    except Exception:
        pass


if __name__ == "__main__":
    import contextlib

    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, required=True, help="Path to QGC .plan")
    ap.add_argument("--hz", type=int, default=20, help="Telemetry sampling Hz")
    args = ap.parse_args()

    asyncio.run(main(args.plan, args.hz))
