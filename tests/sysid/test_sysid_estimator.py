import json
import os
import subprocess
import sys

OUT_JSON = "artifacts/sysid/est_params.json"


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def test_sysid_recovers_params_reasonably():
    # deterministic seed / fewer seconds for CI speed
    _run(
        [
            sys.executable,
            "scripts/sysid/estimate_quad2d.py",
            "--T",
            "10.0",
            "--dt",
            "0.02",
            "--seed",
            "11",
        ]
    )
    assert os.path.isfile(OUT_JSON)
    p = json.loads(open(OUT_JSON).read())
    m_true = p["true"]["m"]
    kx_true = p["true"]["kx"]
    ky_true = p["true"]["ky"]
    # relative errors within 15%
    assert abs(p["m_est"] - m_true) / m_true <= 0.15
    assert abs(p["kx_est"] - kx_true) / kx_true <= 0.15
    assert abs(p["ky_est"] - ky_true) / ky_true <= 0.15
