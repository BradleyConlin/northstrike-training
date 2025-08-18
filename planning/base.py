from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


def plan(
    start: Point, goal: Point, *, step: float = 1.0, max_points: int = 200
) -> List[Point]:
    """
    Returns a straight-line path from start to goal sampled every ~step meters.
    Obstacles ignored for now (placeholder API).
    """
    import math

    dx, dy, dz = goal.x - start.x, goal.y - start.y, goal.z - start.z
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist == 0.0:
        return [start, goal]
    n = max(2, min(max_points, int(dist / max(step, 1e-6)) + 1))
    pts: List[Point] = []
    for i in range(n):
        t = i / (n - 1)
        pts.append(Point(start.x + t * dx, start.y + t * dy, start.z + t * dz))
    return pts
