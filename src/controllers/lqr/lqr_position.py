from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LQRGains:
    """Axis gains for position-velocity state feedback (x,v) with optional integral."""

    kx: float  # position gain
    kv: float  # velocity feedback gain (on -v)
    ki: float = 0.0  # integral on position error (optional)


@dataclass
class Limits:
    accel_max: float = 5.0
    i_limit: float = 1.0


class LQRPos2D:
    """
    2D LQR-like state feedback on (pos, vel) with optional integral on position error.
    Produces acceleration commands (ax, ay) clamped by Limits.accel_max.

    Typical usage:
        ctrl = LQRPos2D(LQRGains(2.0, 3.5, 0.1), limits=Limits(accel_max=3.0))
        ax, ay = ctrl.step(dt, pos=(x,y), vel=(vx,vy), target_pos=(tx,ty))
    """

    def __init__(
        self, gains_x: LQRGains, gains_y: LQRGains | None = None, limits: Limits | None = None
    ) -> None:
        self.gx = gains_x
        self.gy = gains_y or gains_x
        self.lim = limits or Limits()
        self.ix = 0.0
        self.iy = 0.0

    def reset(self) -> None:
        self.ix = 0.0
        self.iy = 0.0

    def _axis(
        self, e_pos: float, v_rel: float, i_prev: float, g: LQRGains, dt: float
    ) -> tuple[float, float]:
        if g.ki > 0.0:
            i_new = i_prev + e_pos * dt
            # clamp integrator
            if i_new > self.lim.i_limit:
                i_new = self.lim.i_limit
            elif i_new < -self.lim.i_limit:
                i_new = -self.lim.i_limit
        else:
            i_new = 0.0

        u = g.kx * e_pos + g.kv * (-v_rel) + g.ki * i_new

        # clamp accel
        if u > self.lim.accel_max:
            u = self.lim.accel_max
        elif u < -self.lim.accel_max:
            u = -self.lim.accel_max

        return u, i_new

    def step(
        self,
        dt: float,
        pos: tuple[float, float],
        vel: tuple[float, float],
        target_pos: tuple[float, float],
        target_vel: tuple[float, float] = (0.0, 0.0),
    ) -> tuple[float, float]:
        ex = target_pos[0] - pos[0]
        ey = target_pos[1] - pos[1]
        vx_rel = vel[0] - target_vel[0]
        vy_rel = vel[1] - target_vel[1]
        ax, self.ix = self._axis(ex, vx_rel, self.ix, self.gx, dt)
        ay, self.iy = self._axis(ey, vy_rel, self.iy, self.gy, dt)
        return ax, ay
