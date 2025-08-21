import asyncio
import time

from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityNedYaw

URL = "udpin://0.0.0.0:14540"  # IMPORTANT for UDP-in on PX4 SITL


async def wait_local_position(sys, timeout_s=60.0):
    """Wait until local position is OK (Python 3.10-safe, no asyncio.timeout)."""
    start = time.time()
    async for health in sys.telemetry.health():
        if health.is_local_position_ok:
            return True
        if time.time() - start > timeout_s:
            return False


async def main():
    print(f"Connecting to {URL} ...")
    drone = System()
    await drone.connect(system_address=URL)

    # Wait until connected
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Connected.")
            break

    print("Waiting (up to 60s) for local position OK ...")
    if not await wait_local_position(drone, timeout_s=60.0):
        raise RuntimeError("Local position never became OK.")

    print("Arming ...")
    await drone.action.arm()

    print("Priming Offboard with zero velocity ...")
    try:
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
        print("Offboard started.")
    except OffboardError as e:
        print(f"Offboard start failed: {e._result.result}. Retrying after zero cmd...")
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()
        print("Offboard started (retry).")

    print("Nudge north +0.2 m/s for 2s ...")
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0.2, 0.0, 0.0, 0.0))
    await asyncio.sleep(2.0)

    print("Stop + disarm ...")
    await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
    await drone.offboard.stop()
    await drone.action.disarm()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
