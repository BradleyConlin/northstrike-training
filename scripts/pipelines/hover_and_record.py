#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import pathlib
import subprocess
import sys
import time

from mavsdk import System


# ---------- helpers ----------
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


# ---------- recorder (runs concurrently) ----------
async def recorder_task(
    drone: System, csv_path: pathlib.Path, hz: float, stop_evt: asyncio.Event
) -> None:
    period = 1.0 / hz
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # shared state updated by small subscriber coroutines
    state = {
        "t": 0.0,
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

    async def sub_position():
        async for p in drone.telemetry.position():
            state["lat"] = p.latitude_deg
            state["lon"] = p.longitude_deg
            state["abs_alt_m"] = p.absolute_altitude_m
            state["rel_alt_m"] = p.relative_altitude_m

    async def sub_vel():
        async for v in drone.telemetry.velocity_ned():
            state["vn"] = v.north_m_s
            state["ve"] = v.east_m_s
            state["vd"] = v.down_m_s

    async def sub_batt():
        async for b in drone.telemetry.battery():
            state["battery_pct"] = (b.remaining_percent or 0.0) * 100.0

    async def sub_air():
        async for ia in drone.telemetry.in_air():
            state["in_air"] = 1 if ia else 0

    subs = [asyncio.create_task(c()) for c in (sub_position, sub_vel, sub_batt, sub_air)]
    t0 = time.time()

    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["t", "lat", "lon", "abs_alt_m", "rel_alt_m", "vn", "ve", "vd", "battery_pct", "in_air"]
        )
        try:
            while not stop_evt.is_set():
                state["t"] = round(time.time() - t0, 3)
                # write last-known values (None -> 0.0)
                row = [
                    state["t"],
                    state["lat"] or 0.0,
                    state["lon"] or 0.0,
                    state["abs_alt_m"] or 0.0,
                    state["rel_alt_m"] or 0.0,
                    state["vn"] or 0.0,
                    state["ve"] or 0.0,
                    state["vd"] or 0.0,
                    state["battery_pct"] if state["battery_pct"] is not None else 0.0,
                    state["in_air"],
                ]
                w.writerow(row)
                await asyncio.sleep(period)
        finally:
            for s in subs:
                s.cancel()
            # give subscribers a moment to cancel cleanly
            await asyncio.gather(*subs, return_exceptions=True)
    print(f"📝 Telemetry saved -> {csv_path}")


# ---------- main ----------
async def main(alt: float, hold_s: float, hz: float) -> None:
    # One MAVSDK server/process only -> no UDP bind conflicts
    drone = System()
    # PX4 SITL SDK endpoint
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    await wait_connected(drone)
    await wait_ekf_ready(drone)

    log_dir = pathlib.Path("datasets/flight_logs")
    ts = time.strftime("%Y%m%d_%H%M%S")
    csv_path = log_dir / f"hover_{ts}.csv"

    stop_evt = asyncio.Event()
    rec_task = asyncio.create_task(recorder_task(drone, csv_path, hz, stop_evt))

    # Flight
    await drone.action.set_takeoff_altitude(alt)
    await drone.action.arm()
    print(f"🛫 Taking off to ~{alt} m…")
    await drone.action.takeoff()
    await asyncio.sleep(hold_s)
    print("🛬 Landing…")
    await drone.action.land()

    # Wait until disarmed on ground
    async for ia in drone.telemetry.in_air():
        if not ia:
            print("✅ Landed & disarmed")
            break

    # stop recorder after 2s extra
    await asyncio.sleep(2)
    stop_evt.set()
    await rec_task

    # Compute KPIs + MLflow logging (re-use existing CLI)
    print("📈 Computing KPIs + logging to MLflow…")
    cmd = [sys.executable, "scripts/evaluation/hover_kpi_report.py", "--csv", str(csv_path)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", type=float, default=6.0)
    ap.add_argument("--hold", type=float, default=8.0)
    ap.add_argument("--hz", type=float, default=20.0)
    a = ap.parse_args()
    asyncio.run(main(a.alt, a.hold, a.hz))
