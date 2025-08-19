#!/usr/bin/env python3
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple


@dataclass
class OUParams:
    tau_s: float = 5.0  # correlation time (s)
    sigma: float = 2.0  # steady-state std (m/s)
    mean: float = 0.0


class OUWind1D:
    """Ornstein–Uhlenbeck wind component with exact discretization."""

    def __init__(self, p: OUParams, seed: int | None = None):
        self.p = p
        self.state = p.mean
        self.rng = random.Random(seed)

    def step(self, dt: float) -> float:
        if dt <= 0:
            return self.state
        # exact OU update
        a = math.exp(-dt / self.p.tau_s)
        var = self.p.sigma**2 * (1.0 - a * a)
        noise = self.rng.gauss(0.0, math.sqrt(max(1e-12, var)))
        self.state = self.p.mean + a * (self.state - self.p.mean) + noise
        return self.state


class WindField:
    """Simple horizontally homogeneous wind field (x,y,z gust components)."""

    def __init__(
        self,
        p_xy: OUParams = OUParams(),
        p_z: OUParams = OUParams(tau_s=7.0, sigma=1.2),
        seed: int = 42,
    ):
        self.wx = OUWind1D(p_xy, seed=seed + 1)
        self.wy = OUWind1D(p_xy, seed=seed + 2)
        self.wz = OUWind1D(p_z, seed=seed + 3)

    def sample(self, dt: float) -> Tuple[float, float, float]:
        return (self.wx.step(dt), self.wy.step(dt), self.wz.step(dt))
