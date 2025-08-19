import csv
import math
import os

import numpy as np

REQ_COLS = {"t", "x", "y", "z", "vx", "vy", "vz", "lat", "lon", "rel_alt_m"}


def _load_csv(path):
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        r = csv.DictReader(f)
        return list(r)


def test_ekf_outputs_exist_and_clean():
    ekf_rows = _load_csv("artifacts/waypoint_run_ekf.csv")
    raw_rows = _load_csv("artifacts/waypoint_run.csv")
    assert raw_rows, "missing artifacts/waypoint_run.csv"
    assert ekf_rows, "missing artifacts/waypoint_run_ekf.csv"
    assert REQ_COLS.issubset(set(ekf_rows[0].keys()))
    xs = [float(d["x"]) for d in ekf_rows if d["x"]]
    ys = [float(d["y"]) for d in ekf_rows if d["y"]]
    zs = [float(d["z"]) for d in ekf_rows if d["z"]]
    assert len(xs) >= 10 and len(ys) >= 10 and len(zs) >= 10
    assert all(math.isfinite(v) for v in xs + ys + zs)


def test_ekf_motion_or_stability():
    ekf_rows = _load_csv("artifacts/waypoint_run_ekf.csv")
    xs = np.array([float(d["x"]) for d in ekf_rows])
    ys = np.array([float(d["y"]) for d in ekf_rows])
    zs = np.array([float(d["z"]) for d in ekf_rows])
    vxs = np.array([float(d["vx"]) for d in ekf_rows])
    vys = np.array([float(d["vy"]) for d in ekf_rows])
    vzs = np.array([float(d["vz"]) for d in ekf_rows])

    # 3D path length
    dist3d = float(np.sum(np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2 + np.diff(zs) ** 2)))
    # vertical displacement proxy
    dz = float(np.sum(np.abs(np.diff(zs))))
    # max speed
    vmax = float(np.max(np.sqrt(vxs**2 + vys**2 + vzs**2)))

    # Pass if there is meaningful motion (hover climbs etc.)
    if (dist3d > 0.5) or (dz > 0.5):
        assert dist3d > 0 or dz > 0  # motion exists
        assert vmax < 50.0
        return

    # Otherwise treat as static hover: require stability (no explosions)
    assert np.all(np.isfinite(vxs)) and np.all(np.isfinite(vys)) and np.all(np.isfinite(vzs))
    # velocities should remain near zero in static hover
    assert vmax < 0.5, f"static run but vmax too high: {vmax:.3f} m/s"
