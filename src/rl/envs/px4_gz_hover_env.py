from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class Px4GzHoverEnv(gym.Env):
    """Minimal Gymnasium env stub (no real sim calls yet)."""

    metadata = {"render.modes": []}

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32)
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(4,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        return obs, {}

    def step(self, action):
        obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        reward = 0.0
        terminated = False
        truncated = False
        info = {}
        return obs, reward, terminated, truncated, info
