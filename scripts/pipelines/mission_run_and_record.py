#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import csv
import json
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Tuple

from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan


# ---------- QGC .plan parsing (supports coordinate[] and params[4..6]) ----------
def parse_qgc_plan(plan_path: Path) -> List[Tuple[float, float, float]]:
    """Return [(lat, lon, rel_alt_m), ...] from a QGC .plan file."""
    data = json.loads(plan_path.read_text())
    items = data.get("mission", {}).get("items", [])
    wps: List[Tuple[float, float, float]] = []

    for it in items:
        if not isinstance(it, dict):
            continue

        # Preferred: explicit coordinate [lat, lon, alt]
        coord = it.get("coordinate")
        if isinstance(coord, list) and len(coord) >= 3:
            lat, lon, alt = coord[:3]
            wps.append((float(lat), float(lon), float(alt)))
            continue

        # Fallback: QGC params array (idx 4..6 = lat, lon, alt)
        params = it.get("params")
        if isinstance(params, list) and len(params) >= 7:
            lat, lon, alt = params[4], params[5], params[6]
            if None not in (lat, lon, alt):
                wps.append((float(lat), float(lon), float(alt)))
                continue

        # Last-ditch fallback: loose fields some exports include
        lat = it.get("latitude") or it.get("Latitude") or it.get("param5")
        lon = it.get("longitude") or it.get("Longitude") or it.get("param6")
        alt = it.get("altitude") or it.get("Altitude") or it.get("param7")
        if all(v is not None for v in (lat, lon, alt)):
            wps.append((float(lat), float(lon), float(alt)))

    if not wps:
        raise ValueError(f"No waypoints found in plan: {plan_path}")
    return wps


# ---------- Mission item creation (adaptive across MAVSDK versions) ----------
def _mk_item(lat: float, lon: float, alt: float) -> MissionItem:
    """Create a MissionItem that works across old/new MAVSDK signatures."""
    base = dict(
        latitude_deg=lat,
        longitude_deg=lon,
        relative_altitude_m=alt,
        speed_m_s=5.0,
        is_fly_through=True,
        gimbal_pitch_deg=0.0,
        gimbal_yaw_deg=0.0,
        camera_action=MissionItem.CameraAction.NONE,
    )
    # Newer MAVSDK requires vehicle_action + several additional fields
    try:
        return MissionItem(
            **base,
            vehicle_action=MissionItem.VehicleAction.NONE,
            loiter_time_s=0.0,
            camera_photo_interval_s=0.0,
            acceptance_radius_m=5.0,
            yaw_deg=float("nan"),
            camera_photo_distance_m=0.0,
        )
    except TypeError:
        # Older: needs vehicle_action only
        try:
            return MissionItem(
                **base,
                vehicle_action=MissionItem.VehicleAction.NONE,
            )
        except TypeError:
            # Oldest: no vehicle_action supported
            return MissionItem(**base)


def to_mavsdk_items(wps: Iterable[Tuple[float, float, float]]) -> List[MissionItem]:
    return [_mk_item(lat, lon, alt) for (lat, lon, alt) in wps]


# ---------- Connection helpers ----------
async def wait_connected(drone: System) -> None:
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("✅ Connected to PX4")
            break


async def wait_ekf_ready(drone: System) -> None:
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok:
            print("✅ EKF healthy & home set")
            break


# ---------- Telemetry recording (Python 3.10 friendly) ----------
async def record_telemetry(drone: System, csv_path: Path, hz: float = 10.0) -> None:
    """Record basic telemetry at ~hz into CSV (single-process, no UDP conflicts)."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    period = 1.0 / max(hz, 0.1)

    pos_gen = drone.telemetry.position()
    batt_gen = drone.telemetry.battery()
    in_air_gen = drone.telemetry.in_air()

    latest = {
        "lat": None,
        "lon": None,
        "rel_alt": None,
        "batt": None,
        "in_air": 0,
    }

    async def _pos_task():
        async for p in pos_gen:
            latest["lat"] = p.latitude_deg
            latest["lon"] = p.longitude_deg
            latest["rel_alt"] = p.relative_altitude_m

    async def _batt_task():
        async for b in batt_gen:
            latest["batt"] = (b.remaining_percent or 0.0) * 100.0

    async def _air_task():
        async for ia in in_air_gen:
            latest["in_air"] = 1 if ia else 0

    t_pos = asyncio.create_task(_pos_task())
    t_bat = asyncio.create_task(_batt_task())
    t_air = asyncio.create_task(_air_task())

    try:
        loop = asyncio.get_event_loop()
        t0 = loop.time()
        with csv_path.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "lat", "lon", "rel_alt_m", "battery_pct", "in_air"])
            while True:
                await asyncio.sleep(period)
                if latest["lat"] is None:
                    continue
                t = loop.time() - t0
                w.writerow(
                    [
                        f"{t:.3f}",
                        f"{latest['lat']:.7f}",
                        f"{latest['lon']:.7f}",
                        f"{(latest['rel_alt'] or 0.0):.3f}",
                        f"{(latest['batt'] or 0.0):.1f}",
                        latest["in_air"],
                    ]
                )
                f.flush()
    finally:
        for task in (t_pos, t_bat, t_air):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


# ---------- Mission execution ----------
async def fly_mission(drone: System, items: List[MissionItem]) -> None:
    plan = MissionPlan(items)
    await drone.mission.clear_mission()
    await drone.mission.upload_mission(plan)
    await drone.action.arm()
    await drone.mission.start_mission()

    total = None
    async for p in drone.mission.mission_progress():
        if total is None:
            total = p.total
            print(f"▶️  Mission started ({total} items)")
        if p.current == p.total and p.total > 0:
            print("✅ Mission complete")
            break

    await drone.action.land()
    async for ia in drone.telemetry.in_air():
        if not ia:
            print("✅ Landed & disarmed")
            break


# ---------- Main ----------
async def main(plan_path: Path, hz: float) -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = Path("datasets/flight_logs") / f"mission_{ts}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    wps = parse_qgc_plan(plan_path)
    items = to_mavsdk_items(wps)

    drone = System()
    # Single process: one mavsdk_server → no "Address in use"
    await drone.connect(system_address="udpin://0.0.0.0:14540")
    await wait_connected(drone)
    await wait_ekf_ready(drone)

    rec_task = asyncio.create_task(record_telemetry(drone, out_csv, hz))
    try:
        await fly_mission(drone, items)
    finally:
        rec_task.cancel()
        try:
            await rec_task
        except asyncio.CancelledError:
            pass

    latest = out_csv.parent / "mission_latest.csv"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_csv.name)
    print(f"🧾 Log: {out_csv}")
    print(f"🔗 Symlink: {latest} -> {out_csv.name}")


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--plan", type=Path, required=True, help="Path to QGC .plan")
    ap.add_argument("--hz", type=float, default=10.0, help="Telemetry rate (Hz)")
    args = ap.parse_args()
    asyncio.run(main(args.plan, args.hz))
