from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

# Frames & units: ENU (x=east, y=north), meters, seconds.
# See docs/adrs/ADR-0003-frames-and-units.md


@dataclass
class State2D:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    yaw: float = 0.0  # rad (unused in this 2D slice)


@dataclass
class Control2D:
    vx: float  # desired body/world velocity x [m/s] (simplified)
    vy: float  # desired body/world velocity y [m/s]


Path2D = List[Tuple[int, int]]  # grid cells (x, y)
