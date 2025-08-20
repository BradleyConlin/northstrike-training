import json
import os
import subprocess
import sys

MET = "artifacts/fixedwing/fw_metrics.json"


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def test_l1_tecs_demo_meets_basic_kpis():
    _run([sys.executable, "scripts/fixedwing/run_fw_demo.py"])
    assert os.path.isfile(MET)
    m = json.loads(open(MET).read())
    # reasonable bounds for this toy sim
    assert m["rmse_xtrack_m"] <= 35.0
    assert m["alt_final_err_m"] <= 12.0
