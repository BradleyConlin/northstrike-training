#!/usr/bin/env python3
from __future__ import annotations

from typing import Iterable, List, Tuple

Pt = Tuple[int, int]


def point_in_polygon(p: Pt, poly: Iterable[Pt]) -> bool:
    """Ray-cast test for 2D geofence polygons on grid coordinates."""
    x, y = p
    poly = list(poly)
    n = len(poly)
    inside = False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        # check edges that straddle the y of point
        if (y1 > y) != (y2 > y):
            # x of intersection of the edge with scanline at y
            xin = x1 + (x2 - x1) * (y - y1) / (y2 - y1)
            if xin >= x:
                inside = not inside
    return inside


def bresenham(a: Pt, b: Pt) -> List[Pt]:
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return pts


def line_of_sight_free(a: Pt, b: Pt, occ_grid) -> bool:
    """
    True if the straight line a->b is free of obstacles on a binary occupancy grid.
    occ_grid[y][x] == 1 means obstacle.
    """
    for x, y in bresenham(a, b):
        if occ_grid[y][x] == 1:
            return False
    return True
