import asyncio
import threading
from typing import Optional, Tuple

import numpy as np
from mavsdk import System
from mavsdk.offboard import OffboardError, VelocityNedYaw
from mavsdk.telemetry import PositionVelocityNed


def _clip(v, lo, hi):
    return float(np.clip(v, lo, hi))


class _MavsdkClient:
    """
    Python 3.10-safe MAVSDK client:
    - connects using udpin://0.0.0.0:14540
    - waits for connection + local position
    - arms, primes offboard, starts offboard
    - background keepalive (zero velocity) to avoid failsafe
    - thread-safe velocity setter
    """

    def __init__(
        self, udp_url: str = "udpin://0.0.0.0:14540", keepalive_hz: float = 5.0, debug: bool = True
    ):
        self._udp_url = udp_url
        self._keepalive_hz = float(keepalive_hz)
        self._debug = debug

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._sys: Optional[System] = None
        self._connected = False
        self._offboard = False
        self._keepalive_task = None

        self._last_pvn: Optional[PositionVelocityNed] = None
        self._lock = threading.Lock()

    async def _wait_for(self, coro, timeout_s: float, what: str):
        """Python 3.10-safe wait with asyncio.wait_for."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout_s)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timeout while waiting for {what} ({timeout_s}s)")

    async def _connect(self, connect_timeout_s: float, local_ready_timeout_s: float):
        if self._debug:
            print(f"[MAVSDK] Connecting to PX4 at {self._udp_url}")

        self._sys = System(mavsdk_server_address=None, port=None)
        await self._sys.connect(system_address=self._udp_url)

        # Wait for base connection
        async def _await_connected():
            async for state in self._sys.core.connection_state():
                if state.is_connected:
                    return

        await self._wait_for(_await_connected(), connect_timeout_s, "connection")

        # Spawn telemetry cacher
        async def _telemetry_cache():
            async for pvn in self._sys.telemetry.position_velocity_ned():
                with self._lock:
                    self._last_pvn = pvn

        asyncio.create_task(_telemetry_cache())

        # Wait until local position OK (EKF ready)
        async def _await_local_pos_ok():
            async for h in self._sys.telemetry.health():
                if h.is_local_position_ok:
                    return

        if self._debug:
            print("Waiting for local position OK ...")
        await self._wait_for(_await_local_pos_ok(), local_ready_timeout_s, "local position")

        # Arm + prime offboard (PX4 requires a setpoint before start)
        if self._debug:
            print("Arming ...")
        await self._sys.action.arm()

        if self._debug:
            print("Priming Offboard (zero velocity) ...")
        try:
            await self._sys.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
            await self._sys.offboard.start()
        except OffboardError:
            # Retry once in case prime wasn’t yet accepted
            await asyncio.sleep(0.1)
            await self._sys.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
            await self._sys.offboard.start()

        self._connected = True
        self._offboard = True

        # Keepalive: send zero velocity at low rate so offboard doesn’t die
        async def _keepalive():
            period = 1.0 / max(1.0, self._keepalive_hz)
            while self._offboard:
                try:
                    await self._sys.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
                except Exception:
                    pass
                await asyncio.sleep(period)

        self._keepalive_task = asyncio.create_task(_keepalive())

        if self._debug:
            print("Offboard started.")

    async def _shutdown(self):
        try:
            if self._sys and self._offboard:
                await self._sys.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
                await self._sys.offboard.stop()
        except Exception:
            pass
        finally:
            self._offboard = False

        try:
            if self._keepalive_task:
                self._keepalive_task.cancel()
        except Exception:
            pass

        try:
            if self._sys:
                await self._sys.action.disarm()
        except Exception:
            pass

    def start(self, connect_timeout_s: float = 90.0, local_ready_timeout_s: float = 60.0):
        """Start background loop + connect/arm/offboard."""
        if self._loop_thread is not None:
            return

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

        fut = asyncio.run_coroutine_threadsafe(
            self._connect(
                connect_timeout_s=connect_timeout_s, local_ready_timeout_s=local_ready_timeout_s
            ),
            self._loop,
        )
        # Give a little buffer for any last await
        fut.result(timeout=connect_timeout_s + local_ready_timeout_s + 10.0)

    def stop(self):
        if self._loop:
            fut = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
            try:
                fut.result(timeout=10.0)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread:
            self._loop_thread.join(timeout=5.0)
        self._loop = None
        self._loop_thread = None

    def set_velocity(self, vx: float, vy: float, vz: float, yaw_deg: float = 0.0):
        """NED velocity (m/s), vz positive-down."""
        if not (self._loop and self._sys and self._offboard):
            return
        cmd = VelocityNedYaw(
            _clip(vx, -3.0, 3.0),
            _clip(vy, -3.0, 3.0),
            _clip(vz, -2.0, 2.0),
            _clip(yaw_deg, -180.0, 180.0),
        )
        fut = asyncio.run_coroutine_threadsafe(self._sys.offboard.set_velocity_ned(cmd), self._loop)
        fut.result(timeout=1.0)

    def get_state(self) -> Tuple[np.ndarray, np.ndarray]:
        with self._lock:
            pvn = self._last_pvn
        if pvn is None:
            return np.zeros(3, dtype=np.float32), np.zeros(3, dtype=np.float32)
        p = pvn.position
        v = pvn.velocity
        pos = np.array([p.north_m, p.east_m, p.down_m], dtype=np.float32)
        vel = np.array([v.north_m_s, v.east_m_s, v.down_m_s], dtype=np.float32)
        return pos, vel
