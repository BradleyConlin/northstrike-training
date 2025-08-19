import subprocess
import sys
from pathlib import Path


def test_compare_planners_sweep_smoke(tmp_path):
    out = Path("artifacts") / "compare_planners_sweep.md"
    try:
        out.unlink()
    except FileNotFoundError:
        pass
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.compare_planners_sweep",
            "--seeds",
            "2",
            "--sim-seconds",
            "1.5",
        ],
        check=True,
    )
    assert out.exists(), "compare_planners_sweep.md was not created"
    txt = out.read_text()
    assert "Planner KPI Seed Sweep" in txt and "RRT (across seeds)" in txt
