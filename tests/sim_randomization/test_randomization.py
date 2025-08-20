from __future__ import annotations

import json
import os
import subprocess

OUT = "artifacts/randomization/last_profile.json"
RUN = ["python", "simulation/domain_randomization/scripts/apply_randomization.py"]


def _run(args):
    subprocess.run(args, check=True)


def _load():
    assert os.path.isfile(OUT)
    return json.loads(open(OUT).read())


def test_values_within_bounds():
    _run(RUN + ["--seed", "123"])
    p = _load()
    assert 0.0 <= p["wind"]["wind_mps"] <= 12.0
    assert 0.0 <= p["wind"]["gust_mps"] <= 6.0
    assert 0.0 <= p["wind"]["direction_deg"] <= 359.0
    assert 0.001 <= p["sensor_noise"]["imu_gyro_std"] <= 0.01
    assert 0.002 <= p["sensor_noise"]["imu_accel_std"] <= 0.02
    assert 0.1 <= p["sensor_noise"]["gps_pos_std_m"] <= 1.5
    assert 0.8 <= p["sensor_noise"]["cam_brightness"] <= 1.2


def test_different_seeds_differ():
    _run(RUN + ["--seed", "111"])
    a = _load()
    _run(RUN + ["--seed", "222"])
    b = _load()
    # At least one field should differ with different seeds
    diffs = []
    for k in ("wind_mps", "gust_mps", "direction_deg"):
        diffs.append(a["wind"][k] != b["wind"][k])
    assert any(diffs)
