#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
from typing import Any, Dict, List, Tuple

import yaml
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan


# ---------- utils ----------
def load_yaml(p: str):
    with open(p, "r") as f:
        return yaml.safe_load(f)


def meters_to_latlon(
    lat0: float, lon0: float, north_m: float, east_m: float
) -> Tuple[float, float]:
    dlat = north_m / 111_320.0
    dlon = east_m / (111_320.0 * math.cos(math.radians(lat0)) + 1e-9)
    return lat0 + dlat, lon0 + dlon


async def wait_local_ok(drone: System, timeout_s: float = 60.0):
    from time import time

    t0 = time()
    async for h in drone.telemetry.health():
        if h.is_local_position_ok:
            return
        if time() - t0 > timeout_s:
            raise TimeoutError("Timed out waiting for local position OK")


async def get_home(drone: System):
    async for home in drone.telemetry.home():
        return home


async def set_params(drone: System, params: Dict[str, Any] | None):
    if not params:
        return
    await asyncio.sleep(0.5)
    for k, v in params.items():
        # prefer float; fall back to int
        try:
            val = float(v)
            await drone.param.set_param_float(k, val)
            print(f"[params] set {k} (float) = {val}")
        except Exception:
            try:
                val = int(float(v))
                await drone.param.set_param_int(k, val)
                print(f"[params] set {k} (int) = {val}")
            except Exception as e:
                print(f"[params] WARN: could not set {k}={v}: {e}")
        await asyncio.sleep(0.05)


# ---------- MissionItem compatibility shim ----------
def make_mission_item(lat: float, lon: float, alt: float, speed: float) -> MissionItem:
    """
    Try several known MissionItem signatures and use the first that works.
    Your error shows acceptance_radius_m, yaw_deg, camera_photo_distance_m,
    and vehicle_action are required — so we try that 14-arg form first.
    """
    nan = float("nan")
    CA = MissionItem.CameraAction
    VA = MissionItem.VehicleAction
    candidates = [
        # 14 args (required set incl. vehicle_action)
        # lat, lon, rel_alt_m, speed_m_s, is_fly_through,
        # gimbal_pitch_deg, gimbal_yaw_deg, camera_action,
        # loiter_time_s, camera_photo_interval_s,
        # acceptance_radius_m, yaw_deg, camera_photo_distance_m, vehicle_action
        (lat, lon, alt, speed, True, nan, nan, CA.NONE, 0.0, 0.0, 2.0, nan, nan, VA.NONE),
        # 16 args (some newer builds)
        (lat, lon, alt, speed, True, nan, nan, CA.NONE, 0, 0, 2.0, nan, 0.0, 0.0, False, True),
        # 15 args (drop is_relative_altitude flag in some builds)
        (lat, lon, alt, speed, True, nan, nan, CA.NONE, 0, 0, 2.0, nan, 0.0, 0.0, False),
        # 12–13-ish older minimal
        (lat, lon, alt, speed, True, nan, nan, CA.NONE, 0, 0),
    ]
    last_err = None
    for args in candidates:
        try:
            return MissionItem(*args)
        except TypeError as e:
            last_err = e
            continue
    raise TypeError(f"MissionItem signature mismatch for this MAVSDK build: {last_err}")


def build_plan_from_home(mission: Dict[str, Any], home_lat: float, home_lon: float) -> MissionPlan:
    speed = float(mission.get("speed_m_s", 5.0))
    items: List[MissionItem] = []
    for wp in mission["waypoints"]:
        lat, lon = meters_to_latlon(home_lat, home_lon, float(wp["north_m"]), float(wp["east_m"]))
        alt = float(wp["alt_m"])
        items.append(make_mission_item(lat, lon, alt, speed))
    return MissionPlan(items)


# ---------- main flow ----------
async def run(bundle_dir: str, out_json: str):
    url = os.getenv("MAVSDK_URL", "udpin://127.0.0.1:14540")
    mission = load_yaml(os.path.join(bundle_dir, "mission.yaml"))
    params = None
    ppath = os.path.join(bundle_dir, "params.yaml")
    if os.path.exists(ppath):
        params = load_yaml(ppath)

    print("[apply] connecting to", url)
    drone = System()
    await drone.connect(system_address=url)
    async for cs in drone.core.connection_state():
        if cs.is_connected:
            break

    await wait_local_ok(drone, 60.0)
    home = await get_home(drone)
    print(f"[apply] home lat={home.latitude_deg:.6f} lon={home.longitude_deg:.6f}")

    await set_params(drone, params)

    plan = build_plan_from_home(mission, home.latitude_deg, home.longitude_deg)
    await drone.mission.clear_mission()
    await drone.mission.set_return_to_launch_after_mission(True)
    await drone.mission.upload_mission(plan)
    print(f"[apply] uploaded {len(plan.mission_items)} mission items")

    print("[apply] arming...")
    await drone.action.arm()
    print("[apply] starting mission...")
    await drone.mission.start_mission()

    async for pr in drone.mission.mission_progress():
        print(f"[progress] current={pr.current}/total={pr.total}")
        if pr.total > 0 and pr.current >= pr.total:
            break

    print("[apply] mission complete; waiting for disarm (RTL)...")
    async for armed in drone.telemetry.armed():
        if not armed:
            break

    res = {"ok": True, "bundle": bundle_dir, "mission": mission.get("name")}
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(res, f, indent=2)
    print("[apply] done.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default="mission/bundles/demo_square")
    ap.add_argument("--out-json", default="artifacts/mission_last_check.json")
    args = ap.parse_args()
    asyncio.run(run(args.bundle, args.out_json))


if __name__ == "__main__":
    main()
