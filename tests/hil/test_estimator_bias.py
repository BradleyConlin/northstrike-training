import json
import os
import subprocess
import sys

MET = "artifacts/hil/session_metrics.json"


def _run(cmd):
    subprocess.run(cmd, check=True)


def test_hil_smoke_bias_and_latency():
    _run([sys.executable, "hil/scripts/start_hil_session.py"])
    assert os.path.isfile(MET)
    m = json.loads(open(MET).read())
    # Biases within 0.05 g (bench sanity)
    assert abs(m["imu_bias_g"]["x"]) <= 0.05
    assert abs(m["imu_bias_g"]["y"]) <= 0.05
    # Average GPS latency reasonable
    assert m["gps_latency_ms"] <= 25.0
    # Few drops allowed in short run
    assert m["dropped_gps"] <= 2
