#!/usr/bin/env python3
"""
Mission demo (MAVSDK + PX4 SITL, Gazebo):
- Connects using MAVSDK_URL (default udpin://127.0.0.1:14540)
- Waits for local-position + home-position OK
- Arms, takeoff to ~2.5m
- Enters Offboard, flies a small square using velocity-NED
- Stops Offboard, lands, disarms
"""

import asyncio
import os

from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityNedYaw

CONN_URL = os.getenv("MAVSDK_URL", "udpin://127.0.0.1:14540")


def log(msg: str):
    print(f"[MAVSDK] {msg}", flush=True)


async def wait_connected(drone: System, timeout_s: float = 60.0):
    log(f"Connecting to {CONN_URL}")
    await drone.connect(system_address=CONN_URL)
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    async for s in drone.core.connection_state():
        if s.is_connected:
            log("Connected.")
            return
        if loop.time() - t0 > timeout_s:
            raise TimeoutError("Timed out waiting for connection")


async def wait_local_position_ok(drone: System, timeout_s: float = 60.0):
    log("Waiting for local position OK ...")
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    async for h in drone.telemetry.health():
        # PX4 SITL typically needs a few seconds for EKF to initialize
        if h.is_local_position_ok and h.is_home_position_ok:
            log("Local position OK (and home position OK).")
            return
        if loop.time() - t0 > timeout_s:
            raise TimeoutError("Timed out waiting for local position health")


async def wait_altitude_reached(drone: System, rel_alt_m: float, timeout_s: float = 30.0):
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    async for pos in drone.telemetry.position():
        # relative_altitude_m is above home
        if pos.relative_altitude_m is not None and pos.relative_altitude_m >= rel_alt_m * 0.8:
            return
        if loop.time() - t0 > timeout_s:
            raise TimeoutError("Timed out waiting to reach takeoff altitude")


async def wait_in_air(drone: System, expected: bool, timeout_s: float = 60.0):
    loop = asyncio.get_event_loop()
    t0 = loop.time()
    async for ia in drone.telemetry.in_air():
        if ia == expected:
            return
        if loop.time() - t0 > timeout_s:
            raise TimeoutError(f"Timed out waiting in_air == {expected}")


async def takeoff(drone: System, alt_m: float = 2.5):
    log("Arming ...")
    await drone.action.arm()
    log(f"Takeoff to ~{alt_m} m ...")
    await drone.action.set_takeoff_altitude(alt_m)
    await drone.action.takeoff()
    # give it a moment then confirm climb
    await asyncio.sleep(2.0)
    await wait_altitude_reached(drone, alt_m, timeout_s=30.0)
    await wait_in_air(drone, expected=True, timeout_s=30.0)
    log("Takeoff complete.")


async def fly_square_offboard(drone: System, vel_mps: float = 0.7, leg_s: float = 4.0):
    # PX4 requires a setpoint before starting Offboard
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
    try:
        log("Starting Offboard ...")
        await drone.offboard.start()
    except OffboardError as e:
        log(f"Offboard start failed ({e}). Priming and retrying.")
        await asyncio.sleep(0.1)
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
        await drone.offboard.start()

    async def leg(n, e, d, yaw_deg, seconds):
        await drone.offboard.set_velocity_ned(VelocityNedYaw(n, e, d, yaw_deg))
        await asyncio.sleep(seconds)

    log("Flying a small square ...")
    # N, E, D are in meters/second (D positive = downward)
    await leg(vel_mps, 0.0, 0.0, 0.0, leg_s)  # north
    await leg(0.0, vel_mps, 0.0, 0.0, leg_s)  # east
    await leg(-vel_mps, 0.0, 0.0, 0.0, leg_s)  # south
    await leg(0.0, -vel_mps, 0.0, 0.0, leg_s)  # west

    # Stop safely
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
    log("Stopping Offboard ...")
    await drone.offboard.stop()


async def land_and_disarm(drone: System):
    log("Landing ...")
    await drone.action.land()
    await wait_in_air(drone, expected=False, timeout_s=45.0)
    # PX4 typically auto-disarms after landing; request disarm in case it stays armed
    try:
        await drone.action.disarm()
    except Exception:
        pass
    log("Done.")


async def main():
    drone = System()

    try:
        await wait_connected(drone, timeout_s=90.0)
        await wait_local_position_ok(drone, timeout_s=90.0)
        await takeoff(drone, alt_m=2.5)
        await fly_square_offboard(drone, vel_mps=0.7, leg_s=4.0)
        await land_and_disarm(drone)
    except Exception as e:
        log(f"ERROR: {e}. Attempting safe stop.")
        # Best-effort safe stop/land
        try:
            await drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0))
            await drone.offboard.stop()
        except Exception:
            pass
        try:
            await drone.action.land()
        except Exception:
            pass
        raise
    finally:
        # small pause to flush any pending MAVLink messages
        await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
