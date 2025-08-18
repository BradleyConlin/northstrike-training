from __future__ import annotations

from dataclasses import dataclass


def _clamp(v: float, lo: float, hi: float) -> float:
    return hi if v > hi else lo if v < lo else v


@dataclass
class QuadParams:
    mass: float = 1.0  # kg
    drag: float = 0.15  # linear drag coeff (1/s)
    accel_max: float = 3.0  # per-axis accel limit (m/s^2)


class Quad2D:
    """Point-mass planar model with linear drag and accel saturation."""

    def __init__(self, params: QuadParams | None = None) -> None:
        self.p = params or QuadParams()
        self.reset()

    def reset(self, px: float = 0.0, py: float = 0.0, vx: float = 0.0, vy: float = 0.0) -> None:
        self.px, self.py, self.vx, self.vy = px, py, vx, vy

    def state(self) -> tuple[float, float, float, float]:
        return self.px, self.py, self.vx, self.vy

    def step(self, dt: float, ax_cmd: float, ay_cmd: float) -> tuple[float, float, float, float]:
        ax_cmd = _clamp(ax_cmd, -self.p.accel_max, self.p.accel_max)
        ay_cmd = _clamp(ay_cmd, -self.p.accel_max, self.p.accel_max)
        # apply linear drag on velocity
        ax = ax_cmd - self.p.drag * self.vx
        ay = ay_cmd - self.p.drag * self.vy
        # integrate
        self.vx += ax * dt
        self.vy += ay * dt
        self.px += self.vx * dt
        self.py += self.vy * dt
        return self.state()
