from __future__ import annotations

import argparse
import heapq
from typing import Iterable, List, Tuple

Grid = List[List[int]]  # 0 = free, 1 = obstacle


def _neighbors(x: int, y: int, w: int, h: int) -> Iterable[Tuple[int, int]]:
    if x > 0:
        yield x - 1, y
    if x + 1 < w:
        yield x + 1, y
    if y > 0:
        yield x, y - 1
    if y + 1 < h:
        yield x, y + 1


def plan_on_grid(
    grid: Grid, start: Tuple[int, int], goal: Tuple[int, int]
) -> List[Tuple[int, int]]:
    """A* on a 4-connected grid."""
    sx, sy = start
    gx, gy = goal
    h = len(grid)
    w = len(grid[0]) if h else 0
    if not (0 <= sx < w and 0 <= sy < h and 0 <= gx < w and 0 <= gy < h):
        raise ValueError("start/goal out of bounds")
    if grid[sy][sx] or grid[gy][gx]:
        raise ValueError("start/goal on obstacle")

    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])  # Manhattan

    openq: List[Tuple[int, Tuple[int, int]]] = []
    heapq.heappush(openq, (0, start))
    came_from: dict[Tuple[int, int], Tuple[int, int] | None] = {start: None}
    g_cost = {start: 0}

    while openq:
        _, cur = heapq.heappop(openq)
        if cur == goal:
            path = []
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            return list(reversed(path))

        cx, cy = cur
        for nx, ny in _neighbors(cx, cy, w, h):
            if grid[ny][nx]:
                continue
            tentative = g_cost[cur] + 1
            if tentative < g_cost.get((nx, ny), 1_000_000_000):
                came_from[(nx, ny)] = cur
                g_cost[(nx, ny)] = tentative
                f = tentative + heuristic((nx, ny), goal)
                heapq.heappush(openq, (f, (nx, ny)))

    raise ValueError("no path found")


def _demo_grid() -> Grid:
    # 20x10 with a small wall
    w, h = 20, 10
    g = [[0 for _ in range(w)] for _ in range(h)]
    for x in range(5, 15):
        g[5][x] = 1
    return g


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="A* on a small demo grid.")
    p.add_argument("--start", default="0,0")
    p.add_argument("--goal", default="19,9")
    args = p.parse_args(argv)

    sx, sy = (int(s) for s in args.start.split(","))
    gx, gy = (int(s) for s in args.goal.split(","))
    grid = _demo_grid()
    path = plan_on_grid(grid, (sx, sy), (gx, gy))
    print(f"path length: {len(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
