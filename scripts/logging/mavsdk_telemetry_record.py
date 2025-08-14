#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import time
from pathlib import Path

from mavsdk import System


async def recorder(path: Path, hz: float) -> None:
    """Record telemetry to CSV at a fixed rate."""
    drone = System()
    # PX4 SITL SDK endpoint (bind to all interfaces)
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    # Wait for MAVLink connection
    async for s in drone.core.connection_state():
        if s.is_connected:
            break

    # Async generators for streams
    pos_a = drone.telemetry.position()
    vel_a = drone.telemetry.velocity_ned()
    bat_a = drone.telemetry.battery()
    air_a = drone.telemetry.in_air()

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
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
        t0 = time.time()
        dt = 1.0 / hz
        try:
            while True:
                t = time.time() - t0
                pos = await pos_a.__anext__()
                vel = await vel_a.__anext__()
                bat = await bat_a.__anext__()
                ia = await air_a.__anext__()
                writer.writerow(
                    [
                        f"{t:.3f}",
                        pos.latitude_deg,
                        pos.longitude_deg,
                        pos.absolute_altitude_m,
                        pos.relative_altitude_m,
                        vel.north_m_s,
                        vel.east_m_s,
                        vel.down_m_s,
                        bat.remaining_percent,
                        int(ia),
                    ]
                )
                await asyncio.sleep(dt)
        except asyncio.CancelledError:
            pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="datasets/flight_logs/telemetry.csv")
    ap.add_argument("--hz", type=float, default=10.0)
    args = ap.parse_args()
    try:
        asyncio.run(recorder(Path(args.out), args.hz))
    except KeyboardInterrupt:
        print("\n✅ Stopped recording")


if __name__ == "__main__":
    main()
