from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class EKFParams:
    # Process noise (per-axis) for position/velocity, and measurement noise for position
    q_pos: float = 1e-3
    q_vel: float = 1e-2
    r_pos: float = 0.3**2  # (meters)^2


class EKF2D:
    """Constant-acceleration EKF on (px, py, vx, vy) with accel input u=(ax, ay).
    Measurements are noisy positions z=(px, py)."""

    def __init__(self, dt: float, params: EKFParams | None = None) -> None:
        self.dt = float(dt)
        self.p = params or EKFParams()
        self.x = np.zeros((4, 1))  # [px, py, vx, vy]^T
        self.P = np.eye(4) * 1.0

        dt = self.dt
        self.F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)
        self.B = np.array([[0.5 * dt * dt, 0], [0, 0.5 * dt * dt], [dt, 0], [0, dt]], dtype=float)
        self.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=float)

        self.Q = np.diag([self.p.q_pos, self.p.q_pos, self.p.q_vel, self.p.q_vel])
        self.R = np.eye(2) * self.p.r_pos

    def reset(self, px: float = 0.0, py: float = 0.0, vx: float = 0.0, vy: float = 0.0) -> None:
        self.x[:] = np.array([[px], [py], [vx], [vy]], dtype=float)
        self.P[:] = np.eye(4) * 1.0

    def predict(self, ax: float, ay: float) -> None:
        u = np.array([[ax], [ay]], dtype=float)
        self.x = self.F @ self.x + self.B @ u
        self.P = self.F @ self.P @ self.F.T + self.Q

    def update(self, zpx: float, zpy: float) -> None:
        z = np.array([[zpx], [zpy]], dtype=float)
        y = z - (self.H @ self.x)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        I_k = np.eye(4)
        self.P = (I_k - K @ self.H) @ self.P

    def step(
        self, ax: float, ay: float, zpx: float | None, zpy: float | None
    ) -> tuple[float, float, float, float]:
        self.predict(ax, ay)
        if zpx is not None and zpy is not None:
            self.update(zpx, zpy)
        px, py, vx, vy = (
            float(self.x[0, 0]),
            float(self.x[1, 0]),
            float(self.x[2, 0]),
            float(self.x[3, 0]),
        )
        return px, py, vx, vy
