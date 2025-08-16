#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path
from typing import List, Tuple

from mavsdk import System
from mavsdk.mission import MissionError, MissionItem, MissionPlan
from mavsdk.telemetry import Position  # type: ignore

CSV_HEADER = "t,lat,lon,abs_alt_m,rel_alt_m,vn,ve,vd,battery_pct,in_air\n"
CONNECT_URL = "udpin://0.0.0.0:14540"  # bind on all interfaces


# -----------------------------
# Utilities
# -----------------------------
def parse_qgc_plan(path: Path) -> List[Tuple[float, float, float]]:
    j = json.loads(path.read_text())
    items = j.get("mission", {}).get("items", [])
    wps: List[Tuple[float, float, float]] = []
    for it in items:
        coord = it.get("coordinate") or it.get("params")
        if not coord or len(coord) < 3:
            continue
        lat, lon, alt = float(coord[0]), float(coord[1]), float(coord[2])
        wps.append((lat, lon, alt))
    if not wps:
        raise ValueError("No waypoints found in plan.")
    return wps


def _build_mission_items(waypoints: List[Tuple[float, float, float]]) -> List[MissionItem]:
    """
    Build MissionItem objects cross-version:
    - Only include camera_action / vehicle_action if the enum exists on MissionItem
      (older SDKs don't expose them; passing an int causes translate_to_rpc() crash).
    """
    has_cam = hasattr(MissionItem, "CameraAction")
    has_veh = hasattr(MissionItem, "VehicleAction")

    items: List[MissionItem] = []
    for lat, lon, rel_alt in waypoints:
        kwargs = dict(
            latitude_deg=float(lat),
            longitude_deg=float(lon),
            relative_altitude_m=float(rel_alt),
            speed_m_s=5.0,
            is_fly_through=False,
            gimbal_pitch_deg=float("nan"),
            gimbal_yaw_deg=float("nan"),
            loiter_time_s=0.0,
            camera_photo_interval_s=0.0,
            acceptance_radius_m=2.0,
            yaw_deg=float("nan"),
            camera_photo_distance_m=0.0,
        )
        if has_cam:
            kwargs["camera_action"] = MissionItem.CameraAction.NONE  # type: ignore[attr-defined]
        if has_veh:
            kwargs["vehicle_action"] = MissionItem.VehicleAction.NONE  # type: ignore[attr-defined]
        items.append(MissionItem(**kwargs))
    return items


async def upload_with_retry(drone: System, plan: MissionPlan, attempts: int = 3) -> None:
    for i in range(1, attempts + 1):
        try:
            await drone.mission.clear_mission()
            await asyncio.wait_for(drone.mission.upload_mission(plan), timeout=10)
            return
        except (MissionError, asyncio.TimeoutError) as e:
            print(f"⚠️  upload_mission failed (attempt {i}/{attempts}): {e}")
            if i == attempts:
                raise
            await asyncio.sleep(1.0)


async def wait_health(drone: System) -> None:
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok:
            print("✅ EKF healthy & home set")
            return


async def record_csv(drone: System, out: Path, hz: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    period = 1.0 / hz
    start = asyncio.get_running_loop().time()
    # Priming async generators
    pos_a = drone.telemetry.position()
    vel_a = drone.telemetry.velocity_ned()
    bat_a = drone.telemetry.battery()
    in_air_a = drone.telemetry.in_air()

    async with asyncio.TaskGroup() as tg:

        async def writer():
            with out.open("w") as f:
                f.write(CSV_HEADER)
                pos: Position | None = None
                vn = ve = vd = 0.0
                bat = 100.0
                in_air = 0

                # Fan-in tasks
                async def pull_pos():
                    nonlocal pos
                    async for p in pos_a:
                        pos = p

                async def pull_vel():
                    nonlocal vn, ve, vd
                    async for v in vel_a:
                        vn, ve, vd = v.north_m_s, v.east_m_s, v.down_m_s

                async def pull_bat():
                    nonlocal bat
                    async for b in bat_a:
                        bat = b.remaining_percent * 100.0

                async def pull_air():
                    nonlocal in_air
                    async for ia in in_air_a:
                        in_air = 1 if ia else 0

                tg.create_task(pull_pos())
                tg.create_task(pull_vel())
                tg.create_task(pull_bat())
                tg.create_task(pull_air())

                # Periodic sampler
                while True:
                    await asyncio.sleep(period)
                    t = asyncio.get_running_loop().time() - start
                    if pos is None:
                        continue
                    lat = pos.latitude_deg
                    lon = pos.longitude_deg
                    abs_alt = pos.absolute_altitude_m
                    rel_alt = pos.relative_altitude_m
                    f.write(
                        f"{t:.3f},{lat:.7f},{lon:.7f},{abs_alt},{rel_alt},{vn},{ve},{vd},{bat:.1f},{in_air}\n"
                    )
                    f.flush()

        tg.create_task(writer())


async def main(plan_path: Path, hz: int) -> None:
    print(f"📋 Loading plan: {plan_path}")
    wps = parse_qgc_plan(plan_path)
    print(f"📦 Parsed {len(wps)} waypoints")

    items = _build_mission_items(wps)
    print(f"🧱 Built {len(items)} MissionItems")

    drone = System()
    print(f"🔌 Connecting to PX4 ({CONNECT_URL})…")
    await drone.connect(system_address=CONNECT_URL)

    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected to PX4")
            break

    await wait_health(drone)

    # Start recorder
    ts = asyncio.get_running_loop().time()
    out = Path("datasets/flight_logs") / f"mission_{Path(plan_path).stem}_{int(ts)}.csv"
    rec_task = asyncio.create_task(record_csv(drone, out, hz))

    # Upload & fly
    plan = MissionPlan(items)
    print("⬆️  Uploading mission…")
    await upload_with_retry(drone, plan, attempts=3)
    print("✅ Mission upload OK")

    print("🔒 Arming…")
    await drone.action.arm()

    print("▶️  Starting mission…")
    await asyncio.sleep(0.3)
    await drone.mission.start_mission()
    print("⏯️  Mission started")

    # Wait until mission finished and vehicle landed
    async for prog in drone.mission.mission_progress():
        cur, tot = prog.current, prog.total
        print(f"… progress {cur}/{tot}")
        if tot > 0 and cur >= tot:
            print("✅ Mission complete")
            break

    print("🛬 Waiting to land/disarm…")
    async for ia in drone.telemetry.in_air():
        if not ia:
            print("✅ Landed & disarmed")
            break

    rec_task.cancel()
    try:
        await rec_task
    except asyncio.CancelledError:
        pass

    # Symlink latest
    latest = out.parent / "mission_latest.csv"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(out.name)
        print(f"🔗 Symlink: {latest} -> {out.name}")
    except Exception:
        pass

    print(f"🧾 Log: {out}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--hz", type=int, default=10)
    args = ap.parse_args()

    asyncio.run(main(args.plan, args.hz))
