from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Tuple

Grid = List[List[int]]  # 0 = free, 1 = obstacle
Pt = Tuple[int, int]


def _neighbors8(x: int, y: int, w: int, h: int) -> Iterable[Pt]:
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h:
                yield nx, ny


def _los_clear(grid: Grid, a: Pt, b: Pt) -> bool:
    """Bresenham LOS on a grid: return True if all crossed cells are free."""
    (x0, y0), (x1, y1) = a, b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    w = len(grid[0])
    h = len(grid)
    while True:
        if not (0 <= x < w and 0 <= y < h) or grid[y][x]:
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


def _simplify(grid: Grid, path: List[Pt]) -> List[Pt]:
    if len(path) < 3:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        # farthest j with clear LOS
        while j > i + 1 and not _los_clear(grid, path[i], path[j]):
            j -= 1
        out.append(path[j])
        i = j
    return out


@dataclass
class _Node:
    x: int
    y: int
    parent: int | None


def _nearest(nodes: List[_Node], q: Pt) -> int:
    qx, qy = q
    best_i = 0
    best_d = 1e9
    for i, n in enumerate(nodes):
        d = (n.x - qx) ** 2 + (n.y - qy) ** 2
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def plan_on_grid_rrt(
    grid: Grid,
    start: Pt,
    goal: Pt,
    *,
    max_iters: int = 20000,
    goal_bias: float = 0.07,
    allow_diag: bool = True,
    simplify: bool = True,
    seed: int | None = None,
) -> List[Pt]:
    """Very small RRT on a grid (8-connected step), with optional LOS simplify."""
    w = len(grid[0])
    h = len(grid)
    sx, sy = start
    gx, gy = goal
    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        raise ValueError("start/goal out of bounds")
    if grid[sy][sx] or grid[gy][gx]:
        raise ValueError("start/goal on obstacle")

    rng = random.Random(seed)
    nodes: List[_Node] = [_Node(sx, sy, None)]

    for _ in range(max_iters):
        if rng.random() < goal_bias:
            q_rand = (gx, gy)
        else:
            q_rand = (rng.randrange(w), rng.randrange(h))
            if grid[q_rand[1]][q_rand[0]]:
                continue

        ni = _nearest(nodes, q_rand)
        nx, ny = nodes[ni].x, nodes[ni].y

        # steer one 8-connected step toward q_rand (or 4-connected if disabled)
        dx = 0 if q_rand[0] == nx else (1 if q_rand[0] > nx else -1)
        dy = 0 if q_rand[1] == ny else (1 if q_rand[1] > ny else -1)
        if not allow_diag and dx != 0 and dy != 0:
            # prefer the axis with larger delta
            if abs(q_rand[0] - nx) >= abs(q_rand[1] - ny):
                dy = 0
            else:
                dx = 0
        cx, cy = nx + dx, ny + dy

        if not (0 <= cx < w and 0 <= cy < h) or grid[cy][cx]:
            continue

        nodes.append(_Node(cx, cy, ni))

        if (cx, cy) == (gx, gy):
            # backtrack
            path: List[Pt] = []
            k = len(nodes) - 1
            while k is not None:
                n = nodes[k]
                path.append((n.x, n.y))
                k = nodes[k].parent
            path.reverse()
            return _simplify(grid, path) if simplify else path

    raise ValueError("no path found (RRT ran out of iterations)")
