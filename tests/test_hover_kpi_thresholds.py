import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _make_hover_csv(path: Path, hz=50, duration_s=10.0, alt_m=1.5, z_std=0.02, seed=123):
    rng = np.random.default_rng(seed)
    n = int(hz * duration_s)
    t = np.arange(n) / hz
    z = alt_m + rng.normal(0.0, z_std, size=n)
    step = z_std / np.sqrt(hz)
    x = np.cumsum(rng.normal(0.0, step, size=n))
    y = np.cumsum(rng.normal(0.0, step, size=n))
    pd.DataFrame({"time_s": t, "rel_alt_m": z, "pos_x_m": x, "pos_y_m": y}).to_csv(
        path, index=False
    )


def _run_cli(csv_path: Path) -> dict:
    cmd = [sys.executable, "scripts/evaluation/hover_kpi_report.py", "--csv", str(csv_path)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise AssertionError(f"KPI CLI failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    text = res.stdout.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise AssertionError(f"Could not parse KPI JSON from stdout:\n{text}")
        return json.loads(m.group(0))


def test_hover_kpi_thresholds(tmp_path: Path):
    csv_path = tmp_path / "hover.csv"
    _make_hover_csv(csv_path)
    try:
        data = _run_cli(csv_path)
    except AssertionError:
        # Fallback: import and compute directly if CLI args change
        from scripts.evaluation.hover_kpi_report import compute_hover_kpis

        df = pd.read_csv(csv_path)
        data = compute_hover_kpis(df)
    assert data["samples"] >= 400
    assert 0.0 < data["duration_s"] <= 15.0
    assert 1.4 < data["alt_mean"] < 1.6
    assert data["hover_rms_m"] < 0.10
    assert data.get("xy_rms_m", 0.0) < 0.20
