#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import yaml


def _sample_range(r):  # [lo, hi]
    lo, hi = float(r[0]), float(r[1])
    return lo + random.random() * (hi - lo)


def _choose(profile_name, cfg):
    return cfg["profiles"][profile_name]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wind", default="simulation/domain_randomization/wind_profiles.yaml")
    ap.add_argument("--noise", default="simulation/domain_randomization/sensor_noise.yaml")
    ap.add_argument("--profile_wind", default="default")
    ap.add_argument("--profile_noise", default="default")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is None:
        args.seed = int(time.time()) & 0xFFFF
    random.seed(args.seed)

    wind_cfg = yaml.safe_load(open(args.wind))
    noise_cfg = yaml.safe_load(open(args.noise))
    w = _choose(args.profile_wind, wind_cfg)
    n = _choose(args.profile_noise, noise_cfg)

    out = {
        "seed": args.seed,
        "wind": {
            "wind_mps": _sample_range(w["wind_mps"]),
            "gust_mps": _sample_range(w["gust_mps"]),
            "direction_deg": _sample_range(w["direction_deg"]),
        },
        "sensor_noise": {
            "imu_gyro_std": _sample_range(n["imu_gyro_std"]),
            "imu_accel_std": _sample_range(n["imu_accel_std"]),
            "gps_pos_std_m": _sample_range(n["gps_pos_std_m"]),
            "cam_brightness": _sample_range(n["cam_brightness"]),
        },
    }

    Path("artifacts/randomization").mkdir(parents=True, exist_ok=True)
    j = Path("artifacts/randomization/last_profile.json")
    j.write_text(json.dumps(out, indent=2))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
