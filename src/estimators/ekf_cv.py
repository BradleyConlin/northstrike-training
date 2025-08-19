#!/usr/bin/env python3
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class EKFState:
    x: np.ndarray  # [x y z vx vy vz]^T
    P: np.ndarray


class EKFCV:
    def __init__(self, q_pos=0.5, q_vel=0.8, r_pos=2.0):
        self.q_pos, self.q_vel, self.r_pos = q_pos, q_vel, r_pos
        self._I = np.eye(6)

    def init(self, x0: float, y0: float, z0: float) -> EKFState:
        x = np.zeros((6, 1))
        x[0, 0], x[1, 0], x[2, 0] = x0, y0, z0
        P = np.diag([10, 10, 10, 5, 5, 5]).astype(float)
        return EKFState(x=x, P=P)

    def _F(self, dt: float) -> np.ndarray:
        F = np.eye(6)
        F[0, 3] = dt
        F[1, 4] = dt
        F[2, 5] = dt
        return F

    def _Q(self, dt: float) -> np.ndarray:
        return np.diag([self.q_pos * dt] * 3 + [self.q_vel * dt] * 3).astype(float)

    def predict(self, st: EKFState, dt: float) -> EKFState:
        F = self._F(dt)
        st.x = F @ st.x
        st.P = F @ st.P @ F.T + self._Q(dt)
        return st

    def update_pos(self, st: EKFState, zx: float, zy: float, zz: float) -> EKFState:
        H = np.zeros((3, 6))
        H[0, 0] = H[1, 1] = H[2, 2] = 1
        R = np.diag([self.r_pos] * 3).astype(float)
        z = np.array([[zx], [zy], [zz]])
        y = z - (H @ st.x)
        S = H @ st.P @ H.T + R
        K = st.P @ H.T @ np.linalg.inv(S)
        st.x = st.x + K @ y
        st.P = (self._I - K @ H) @ st.P
        return st


def geodetic_to_local_xy(lat0, lon0, lat, lon):
    R = 6378137.0
    dlat = math.radians(lat - lat0)
    dlon = math.radians(lon - lon0)
    x = R * dlon * math.cos(math.radians((lat + lat0) / 2.0))
    y = R * dlat
    return x, y
