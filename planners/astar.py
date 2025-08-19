from __future__ import annotations

import heapq
import math
from typing import Iterable, List, Tuple

Grid = List[List[int]]  # 0 = free, 1 = obstacle


def _neighbors(x: int, y: int, w: int, h: int, allow_diag: bool) -> Iterable[Tuple[int, int]]:
    if x > 0:
        yield x - 1, y
    if x + 1 < w:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y + 1 < h:
        yield x, y + 1
    if not allow_diag:
        return
    if x > 0 and y > 0:
        yield x - 1, y - 1
    if x + 1 < w and y > 0:
        yield x + 1, y - 1
    if x > 0 and y + 1 < h:
        yield x - 1, y + 1
    if x + 1 < w and y + 1 < h:
        yield x + 1, y + 1


def _octile(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
    return dx + dy + (math.sqrt(2.0) - 2.0) * min(dx, dy)


def _manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _line_clear(grid: Grid, a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    # Bresenham LOS between cells a->b (inclusive)
    (x0, y0), (x1, y1) = a, b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        if grid[y][x]:
            return False
        if x == x1 and y == y1:
            return True
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _simplify_path(grid: Grid, path: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if len(path) <= 2:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = i + 1
        while j + 1 < len(path) and _line_clear(grid, out[-1], path[j + 1]):
            j += 1
        out.append(path[j])
        i = j
    return out


def plan_on_grid(
    grid: Grid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    *,
    allow_diag: bool = False,
    simplify: bool = False,
) -> List[Tuple[int, int]]:
    """A* on a grid; optional 8-connected neighbors and LOS smoothing."""
    sx, sy = start
    gx, gy = goal
    h = len(grid)
    w = len(grid[0]) if h else 0
    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        raise ValueError("start/goal out of bounds")
    if grid[sy][sx] or grid[gy][gx]:
        raise ValueError("start/goal on obstacle")

    heuristic = _octile if allow_diag else _manhattan
    openq: list[tuple[float, tuple[int, int]]] = []
    heapq.heappush(openq, (0.0, start))
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g_cost: dict[tuple[int, int], float] = {start: 0.0}

    while openq:
        _, cur = heapq.heappop(openq)
        if cur == goal:
            path: list[tuple[int, int]] = []
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            path = list(reversed(path))
            return _simplify_path(grid, path) if simplify else path

        cx, cy = cur
        for nx, ny in _neighbors(cx, cy, w, h, allow_diag):
            if grid[ny][nx]:
                continue
            diag = (nx != cx) and (ny != cy)
            step = math.sqrt(2.0) if (allow_diag and diag) else 1.0
            tentative = g_cost[(cx, cy)] + step
            nkey = (nx, ny)
            if tentative + 1e-12 < g_cost.get(nkey, float("inf")):
                came_from[nkey] = (cx, cy)
                g_cost[nkey] = tentative
                f = tentative + heuristic(nkey, goal)
                heapq.heappush(openq, (f, nkey))
    raise ValueError("no path found")
