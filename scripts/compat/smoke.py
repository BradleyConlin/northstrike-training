#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

import numpy as np
from planners.astar import plan_on_grid as astar_plan

from src.perception.color_target import detect_color_targets

VERS: dict[str, str] = {}


def _v(modname: str) -> str:
    try:
        m = __import__(modname)
        return getattr(m, "__version__", "n/a")
    except Exception:
        return "missing"


# versions
VERS["python"] = sys.version.split()[0]
for m in ["numpy", "scipy", "cv2", "mlflow", "pytest"]:
    VERS[m] = _v(m)

# A* sanity on empty grid
g = np.zeros((10, 10), dtype=int)
p = astar_plan(g, (0, 0), (9, 9))
assert p and p[0] == (0, 0) and p[-1] == (9, 9), "A* failed on empty grid"

# CV sanity (green box detection)
img = np.zeros((60, 60, 3), dtype=np.uint8)
img[20:40, 20:40] = (0, 255, 0)  # green in BGR
boxes = detect_color_targets(img)
assert boxes, "Perception detector failed to find green box"

print(json.dumps({"compat_smoke": "ok", "versions": VERS}, indent=2))
