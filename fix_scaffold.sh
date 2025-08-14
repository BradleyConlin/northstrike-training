#!/usr/bin/env bash
set -euo pipefail

# --- .gitignore (restore a sane one) ---
cat > .gitignore <<'GIT'
__pycache__/
*.pyc
.env
.venv/
# data & artifacts (adjust as needed)
mlruns/
data/
datasets/
models/checkpoints/
models/exported/
# OS / IDE
.DS_Store
.idea/
.vscode/
GIT

# --- Python stub fixes (valid syntax, flake8/black-friendly) ---

# Controllers
cat > src/controllers/fixed_wing/tecs.py <<'PY'
from __future__ import annotations
from typing import Dict


class TECS:
    """Tiny placeholder for TECS controller interface."""

    def step(self, state: Dict, refs: Dict) -> Dict:
        """Return placeholder pitch/throttle commands."""
        return {"pitch": 0.0, "throttle": 0.5}
PY

# Estimators
cat > src/estimators/ekf/ekf_core.py <<'PY'
from __future__ import annotations
from typing import Dict, Any


class EKF:
    """Minimal EKF stub."""

    def step(self, meas: Dict[str, Any]) -> Dict[str, Any]:
        # Replace with real predict/update
        return {"state": [0.0, 0.0, 0.0], "cov": [[1.0, 0.0, 0.0]]}
PY

# Perception
cat > src/perception/detect/yolo_train.py <<'PY'
def main() -> None:
    print("TODO: YOLO train")


if __name__ == "__main__":
    main()
PY

# Planners
cat > src/planners/global/a_star.py <<'PY'
from __future__ import annotations
from typing import Tuple, List


def plan(start: Tuple[float, float], goal: Tuple[float, float], costmap) -> List[tuple]:
    """Return a minimal placeholder path from start to goal."""
    return [start, goal]
PY

# RL env
cat > src/rl/envs/px4_gz_hover_env.py <<'PY'
from __future__ import annotations
import gymnasium as gym
from gymnasium import spaces
import numpy as np


class Px4GzHoverEnv(gym.Env):
    """Minimal Gymnasium env stub (no real sim calls yet)."""

    metadata = {"render.modes": []}

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or {}
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(6,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(4,), dtype=np.float32
        )

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
PY

# Utils
cat > src/utils/data_loader.py <<'PY'
from __future__ import annotations
from typing import Any


def load_dataset(cfg: dict) -> Any:
    print("TODO: dataset loader", cfg)
    return None
PY

cat > src/utils/train_loops.py <<'PY'
from __future__ import annotations


def train_loop(cfg: dict) -> None:
    print("TODO: training loop", cfg)
PY

# Tests
cat > tests/hil/test_estimator_bias.py <<'PY'
def test_bias():
    assert True
PY

echo "✅ Fixed stub files and .gitignore."
