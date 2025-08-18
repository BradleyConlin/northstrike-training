from __future__ import annotations

from dataclasses import dataclass


def _clamp(v: float, lo: float, hi: float) -> float:
    return hi if v > hi else lo if v < lo else v


@dataclass
class PIDGains:
    kp: float
    ki: float
    kd: float


@dataclass
class Limits:
    accel_max: float = 5.0  # |a_cmd| per axis (m/s^2)
    i_limit: float = 1.0  # |integrator| bound


class PIDPos2D:
    """2-axis position PID producing acceleration commands.

    D is taken on measurement (vel error) for noise robustness.
    Simple anti-windup via conditional integration + integrator clamp.
    """

    def __init__(
        self,
        gains_x: PIDGains,
        gains_y: PIDGains | None = None,
        limits: Limits | None = None,
    ) -> None:
        self.gx = gains_x
        self.gy = gains_y or gains_x
        self.lim = limits or Limits()
        self.ix = 0.0
        self.iy = 0.0

    def reset(self) -> None:
        self.ix = 0.0
        self.iy = 0.0

    def _axis_step(
        self, e: float, d: float, i_prev: float, g: PIDGains, dt: float
    ) -> tuple[float, float]:
        """One PID axis with conditional integration and output clamp."""
        # Candidate integrator (clamped)
        if g.ki > 0.0:
            i_cand = _clamp(i_prev + e * dt, -self.lim.i_limit, self.lim.i_limit)
        else:
            i_cand = 0.0

        u_unsat = g.kp * e + g.ki * i_cand + g.kd * d
        u_sat = _clamp(u_unsat, -self.lim.accel_max, self.lim.accel_max)

        # If saturated, only integrate when it helps drive us out of saturation.
        if u_unsat != u_sat and g.ki > 0.0:
            # keep previous integrator this step (conditional integration)
            i_new = i_prev
            u_unsat = g.kp * e + g.ki * i_new + g.kd * d
            u_sat = _clamp(u_unsat, -self.lim.accel_max, self.lim.accel_max)
        else:
            i_new = i_cand

        return u_sat, i_new

    def step(
        self,
        dt: float,
        pos: tuple[float, float],
        vel: tuple[float, float],
        target_pos: tuple[float, float],
        target_vel: tuple[float, float] = (0.0, 0.0),
    ) -> tuple[float, float]:
        """Compute accel command (ax, ay)."""
        ex = target_pos[0] - pos[0]
        ey = target_pos[1] - pos[1]
        # D on measurement: velocity error (target_vel - current_vel)
        dx = target_vel[0] - vel[0]
        dy = target_vel[1] - vel[1]

        ax, self.ix = self._axis_step(ex, dx, self.ix, self.gx, dt)
        ay, self.iy = self._axis_step(ey, dy, self.iy, self.gy, dt)
        return ax, ay

    def state(self) -> dict[str, float]:
        return {"ix": self.ix, "iy": self.iy}
