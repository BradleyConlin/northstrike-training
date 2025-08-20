#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import time
from pathlib import Path

# Mock HIL: generate IMU @400 Hz, GPS @10 Hz, with small biases and jitter.
# Outputs:
# - artifacts/hil/hil_log.csv         (timestamp, ax, ay, az, gps_fix, gps_ts)
# - artifacts/hil/session_metrics.json (imu_bias_g, gps_latency_ms, dropped_gps, secs)

OUT_DIR = Path("artifacts/hil")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_mock(secs: float = 6.0, imu_hz: int = 400, gps_hz: int = 10, seed: int = 7):
    random.seed(seed)
    start = time.time()
    t_imu = 1.0 / imu_hz
    t_gps = 1.0 / gps_hz
    next_gps = start
    # biases: ~0.02 g on X/Y, +1g on Z (gravity), tiny noise
    bx = 0.02 * (1 if random.random() < 0.5 else -1)
    by = -0.02
    bz = 1.0  # include gravity magnitude as "accel z"
    gps_latency_ms = []
    dropped_gps = 0

    with open(OUT_DIR / "hil_log.csv", "w") as f:
        f.write("t,ax,ay,az,gps_fix,gps_ts\n")
        t = start
        while t - start < secs:
            # IMU sample
            n = 0.005
            ax = bx + random.uniform(-n, n)
            ay = by + random.uniform(-n, n)
            az = bz + random.uniform(-n, n)
            gps_fix = 0
            gps_ts = ""

            # GPS tick?
            if t >= next_gps:
                # 2% drop
                if random.random() < 0.02:
                    dropped_gps += 1
                else:
                    # latency ~ 5–20 ms
                    lat_ms = random.uniform(5.0, 20.0)
                    gps_latency_ms.append(lat_ms)
                    gps_fix = 1
                    gps_ts = f"{(t + lat_ms/1000.0):.6f}"
                next_gps += t_gps

            f.write(f"{t:.6f},{ax:.5f},{ay:.5f},{az:.5f},{gps_fix},{gps_ts}\n")
            t += t_imu

    # KPIs
    kpis = {
        "imu_bias_g": {"x": round(bx, 4), "y": round(by, 4)},  # estimate truth we injected
        "gps_latency_ms": round(sum(gps_latency_ms) / max(1, len(gps_latency_ms)), 2),
        "dropped_gps": dropped_gps,
        "secs": secs,
    }
    (OUT_DIR / "session_metrics.json").write_text(json.dumps(kpis))
    print(json.dumps(kpis))


if __name__ == "__main__":
    run_mock()
