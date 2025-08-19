from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, sin, sqrt


@dataclass
class PPConfig:
    lookahead: float = 2.0  # meters
    desired_speed: float = 4.0  # m/s
    accel_limit: float = 3.0  # m/s^2
    vel_p: float = 1.5  # gains mapping desired vel -> accel
    vel_d: float = 0.3


class PurePursuit2D:
    """
    Simple 2D pure-pursuit target generator.
    Given current pos and next waypoint, compute desired velocity vector pointing
    toward a lookahead point; then convert to an acceleration using PD on velocity.
    """

    def __init__(self, cfg: PPConfig | None = None):
        self.cfg = cfg or PPConfig()

    @staticmethod
    def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        dx = a[0] - b[0]
        dy = a[1] - b[1]
        return sqrt(dx * dx + dy * dy)

    def desired_velocity(
        self, pos: tuple[float, float], next_wp: tuple[float, float]
    ) -> tuple[float, float]:
        dx = next_wp[0] - pos[0]
        dy = next_wp[1] - pos[1]
        ang = atan2(dy, dx)
        return (self.cfg.desired_speed * cos(ang), self.cfg.desired_speed * sin(ang))

    def accel_cmd(
        self, pos: tuple[float, float], vel: tuple[float, float], next_wp: tuple[float, float]
    ) -> tuple[float, float]:
        dvx, dvy = self.desired_velocity(pos, next_wp)
        ex_vx = dvx - vel[0]
        ex_vy = dvy - vel[1]
        ax = (
            self.cfg.vel_p * ex_vx - self.cfg.vel_d * 0.0
        )  # no vel-derivative here (we don't keep a history)
        ay = self.cfg.vel_p * ex_vy - self.cfg.vel_d * 0.0
        # clamp accel
        mag = sqrt(ax * ax + ay * ay)
        if mag > self.cfg.accel_limit and mag > 1e-6:
            scale = self.cfg.accel_limit / mag
            ax *= scale
            ay *= scale
        return ax, ay
