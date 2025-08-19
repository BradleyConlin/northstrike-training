#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from src.estimators.ekf_cv import EKFCV, geodetic_to_local_xy

"""
Input: artifacts/waypoint_run.csv (expected columns)
  t,lat,lon,rel_alt_m,vn,ve,vd  (others allowed)
Output:
  artifacts/waypoint_run_ekf.csv
  artifacts/waypoint_plot_ekf.png
Note:
  If lat/lon are (nearly) constant (common in local-NED sims), we
  reconstruct x/y by integrating ve/vn. Otherwise we use lat/lon->x/y.
"""


def read_rows(p: Path):
    with open(p, newline="") as f:
        r = csv.DictReader(f)
        rows = list(r)
    return rows, r.fieldnames


def fnum(d, k, default=0.0):
    try:
        return float(d.get(k, default))
    except (TypeError, ValueError):
        return default


def main(in_path: str):
    in_csv = Path(in_path)
    out_csv = in_csv.parent / "waypoint_run_ekf.csv"
    rows, cols = read_rows(in_csv)
    if not rows:
        print("No rows in input CSV")
        return

    # detect whether lat/lon move
    lats = [fnum(d, "lat", 0.0) for d in rows]
    lons = [fnum(d, "lon", 0.0) for d in rows]
    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)

    use_geo = (lat_span > 1e-6) or (lon_span > 1e-6)  # ~0.1 m threshold
    have_local_cols = "x_m" in cols and "y_m" in cols

    # origin / init
    lat0 = lats[0]
    lon0 = lons[0]
    z0 = fnum(rows[0], "rel_alt_m", 0.0)

    # build raw measurement trajectory (x_meas,y_meas)
    x_meas = []
    y_meas = []
    z_meas = []
    if have_local_cols:
        for d in rows:
            x_meas.append(fnum(d, "x_m", 0.0))
            y_meas.append(fnum(d, "y_m", 0.0))
            z_meas.append(fnum(d, "rel_alt_m", 0.0))
        mode = "local_xy_columns"
    elif use_geo:
        for d in rows:
            x, y = geodetic_to_local_xy(lat0, lon0, fnum(d, "lat", 0.0), fnum(d, "lon", 0.0))
            x_meas.append(x)
            y_meas.append(y)
            z_meas.append(fnum(d, "rel_alt_m", 0.0))
        mode = "geodetic"
    else:
        # integrate velocities (east=ve, north=vn)
        x = 0.0
        y = 0.0
        t_prev = fnum(rows[0], "t", 0.0)
        for d in rows:
            t = fnum(d, "t", 0.0)
            dt = max(1e-3, t - t_prev)
            t_prev = t
            ve = fnum(d, "ve", 0.0)
            vn = fnum(d, "vn", 0.0)
            x += ve * dt
            y += vn * dt
            x_meas.append(x)
            y_meas.append(y)
            z_meas.append(fnum(d, "rel_alt_m", 0.0))
        mode = "integrated_vn_ve"

    # EKF pass
    ekf = EKFCV(q_pos=0.5, q_vel=0.8, r_pos=2.0)
    st = ekf.init(x_meas[0], y_meas[0], z0)
    t_prev = fnum(rows[0], "t", 0.0)

    out = []
    xs = []
    ys = []
    zs = []
    for d, xm, ym, zm in zip(rows, x_meas, y_meas, z_meas):
        t = fnum(d, "t", 0.0)
        dt = max(1e-3, t - t_prev)
        t_prev = t
        st = ekf.predict(st, dt)
        st = ekf.update_pos(st, xm, ym, zm)
        xs.append(float(st.x[0, 0]))
        ys.append(float(st.x[1, 0]))
        zs.append(float(st.x[2, 0]))
        out.append(
            {
                "t": t,
                "x": st.x[0, 0],
                "y": st.x[1, 0],
                "z": st.x[2, 0],
                "vx": st.x[3, 0],
                "vy": st.x[4, 0],
                "vz": st.x[5, 0],
                "x_meas": xm,
                "y_meas": ym,
                "z_meas": zm,
                "lat": fnum(d, "lat", 0.0),
                "lon": fnum(d, "lon", 0.0),
                "rel_alt_m": zm,
                "mode": mode,
            }
        )

    # write output
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    # quick plot
    png = in_csv.parent / "waypoint_plot_ekf.png"
    plt.figure()
    plt.plot([o["x_meas"] for o in out], [o["y_meas"] for o in out], label="meas", linestyle="--")
    plt.plot(xs, ys, label="EKF")
    plt.xlabel("x [m]")
    plt.ylabel("y [m]")
    plt.title(f"EKF CV path ({mode})")
    plt.legend()
    plt.tight_layout()
    plt.savefig(png, dpi=120)

    # movement summary
    dist = float(np.sum(np.hypot(np.diff(xs), np.diff(ys))))
    print(f"Mode: {mode} | Move: {dist:.2f} m")
    print(f"Wrote: {out_csv} and {png}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: estimator_offline.py artifacts/waypoint_run.csv")
        sys.exit(1)
    main(sys.argv[1])
