#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from typing import Optional

from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityNedYaw

# ------------ tiny helpers that work on Python 3.10 (no asyncio.timeout) ----------


async def wait_for(predicate_coro, timeout_s: float, poll_s: float = 0.2) -> bool:
    """
    Polls an async predicate() -> bool until it returns True or times out.
    Works on Python 3.10 where asyncio.timeout() doesn't exist.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if await predicate_coro():
                return True
        except Exception:
            pass
        await asyncio.sleep(poll_s)
    return False


# ---------------------------- MAVSDK control logic ---------------------------------


async def connect(system_url: str) -> System:
    print(f"[MAVSDK] Connecting to PX4 at {system_url}")
    drone = System()
    await drone.connect(system_address=system_url)

    # wait until connection_state.is_connected toggles True
    async def _connected():
        async for state in drone.core.connection_state():
            if state.is_connected:
                return True
            return False

    if not await wait_for(_connected, 10.0):
        raise RuntimeError("Timeout: PX4 connection_state did not become connected")
    print("[MAVSDK] Connected.")

    return drone


async def wait_local_position_ok(drone: System, timeout_s: float) -> None:
    print("[MAVSDK] Waiting for local position OK ...")

    async def _ok():
        async for h in drone.telemetry.health():
            # For multicopter we need local position & home
            if h.is_local_position_ok and h.is_home_position_ok:
                return True
            return False

    ok = await wait_for(_ok, timeout_s, 0.3)
    if not ok:
        raise RuntimeError("Timeout: EKF local position not ready")
    print("[MAVSDK] Local position OK.")


async def arm_and_takeoff(drone: System, takeoff_alt_m: float = 2.5) -> None:
    print("[MAVSDK] Arming ...")
    await drone.action.arm()

    print(f"[MAVSDK] Takeoff to ~{takeoff_alt_m:.1f} m ...")
    try:
        await drone.action.set_takeoff_altitude(takeoff_alt_m)
    except Exception:
        pass
    await drone.action.takeoff()

    # wait until we're in air and near target altitude
    async def _at_alt():
        last_rel_alt: Optional[float] = None
        async for pos in drone.telemetry.position():
            last_rel_alt = pos.relative_altitude_m
            break
        return (last_rel_alt is not None) and (last_rel_alt >= max(1.5, 0.6 * takeoff_alt_m))

    ok = await wait_for(_at_alt, 20.0, 0.2)
    if not ok:
        print("[MAVSDK] Didn't see altitude rise yet — continuing, Offboard will hold altitude.")
    print("[MAVSDK] Takeoff complete / proceeding to Offboard.")


async def start_offboard(drone: System) -> None:
    # PX4 requires a first setpoint before offboard start
    print("[MAVSDK] Priming Offboard ...")
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
    try:
        await drone.offboard.start()
    except OffboardError:
        # try once more after priming again
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
    print("[MAVSDK] Offboard started.")


async def fly_square(drone: System, side_m: float = 4.0, speed_mps: float = 1.0) -> None:
    print("[MAVSDK] Flying a small square ...")
    # duration = distance / speed
    dur_s = side_m / max(0.2, speed_mps)

    # N (+north), E (+east), S (-north), W (-east)
    legs = [
        VelocityNedYaw(speed_mps, 0.0, 0.0, 0.0),  # north
        VelocityNedYaw(0.0, speed_mps, 0.0, 90.0),  # east
        VelocityNedYaw(-speed_mps, 0.0, 0.0, 180.0),  # south
        VelocityNedYaw(0.0, -speed_mps, 0.0, -90.0),  # west
    ]

    for i, cmd in enumerate(legs, 1):
        print(f"[MAVSDK] Leg {i}/4 for {dur_s:.1f}s")
        await drone.offboard.set_velocity_ned(cmd)
        await asyncio.sleep(dur_s)

    # Stop movement (hold)
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
    print("[MAVSDK] Square complete.")


async def land_and_disarm(drone: System) -> None:
    print("[MAVSDK] Stopping Offboard ...")
    try:
        await drone.offboard.stop()
    except Exception:
        pass

    print("[MAVSDK] Landing ...")
    await drone.action.land()

    async def _on_ground():
        async for in_air in drone.telemetry.in_air():
            return not in_air

    await wait_for(_on_ground, 25.0, 0.3)

    print("[MAVSDK] Disarming ...")
    try:
        await drone.action.disarm()
    except Exception:
        pass

    print("[MAVSDK] Done.")


async def main():
    # PX4 SITL advertises "Onboard, udp port 14580 remote port 14540"
    # For MAVSDK, connect with UDPP-IN on all interfaces at 14540:
    system_url = "udpin://0.0.0.0:14540"

    drone = await connect(system_url)
    await wait_local_position_ok(drone, timeout_s=60.0)
    await arm_and_takeoff(drone, takeoff_alt_m=2.5)
    await start_offboard(drone)
    await fly_square(drone, side_m=4.0, speed_mps=1.0)
    await land_and_disarm(drone)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
