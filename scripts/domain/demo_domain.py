#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from src.domain.geo import line_of_sight_free, point_in_polygon
from src.domain.wind import OUParams, WindField

OUT = Path("artifacts/domain")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    wf = WindField(OUParams(tau_s=5.0, sigma=2.0), OUParams(tau_s=7.0, sigma=1.2), seed=123)
    T, dt = 60.0, 0.1
    with (OUT / "wind_log.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "wx", "wy", "wz"])
        t = 0.0
        for _ in range(int(T / dt)):
            wx, wy, wz = wf.sample(dt)
            w.writerow([round(t, 3), wx, wy, wz])
            t += dt

    grid = np.zeros((40, 40), dtype=int)
    grid[20, 10:30] = 1  # wall at y=20
    poly = [(5, 5), (35, 5), (35, 35), (5, 35)]

    a = (8, 8)
    b = (32, 8)  # free
    c = (8, 20)
    d = (32, 20)  # blocked

    with (OUT / "domain_checks.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "value"])
        w.writerow(["a_in_fence", point_in_polygon(a, poly)])
        w.writerow(["b_in_fence", point_in_polygon(b, poly)])
        w.writerow(["los_ab", line_of_sight_free(a, b, grid)])
        w.writerow(["los_cd", line_of_sight_free(c, d, grid)])

    print("Wrote:", OUT / "wind_log.csv", "and", OUT / "domain_checks.csv")


if __name__ == "__main__":
    main()
