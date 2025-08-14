#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from mavsdk import System


async def run(alt: float, hold_s: float) -> None:
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")  # PX4 SITL SDK port

    # Wait for connection
    async for s in drone.core.connection_state():
        if s.is_connected:
            print("✅ Connected to PX4")
            break

    # Wait until EKF is ready and home is set
    async for h in drone.telemetry.health():
        if h.is_global_position_ok and h.is_home_position_ok:
            print("✅ EKF healthy & home set")
            break

    await drone.action.set_takeoff_altitude(alt)
    await drone.action.arm()
    print(f"🛫 Taking off to ~{alt} m…")
    await drone.action.takeoff()

    await asyncio.sleep(hold_s)
    print("🛬 Landing…")
    await drone.action.land()

    # Wait until disarmed
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("✅ Landed & disarmed")
            break


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--alt", type=float, default=5.0, help="Takeoff altitude (m)")
    p.add_argument("--hold", type=float, default=5.0, help="Hover hold time (s)")
    args = p.parse_args()
    asyncio.run(run(args.alt, args.hold))


if __name__ == "__main__":
    main()
