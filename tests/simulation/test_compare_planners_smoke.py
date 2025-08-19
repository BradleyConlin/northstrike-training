import subprocess
import sys
from pathlib import Path


def test_compare_planners_smoke(tmp_path):
    out = Path("artifacts") / "compare_planners.md"
    try:
        out.unlink()
    except FileNotFoundError:
        pass

    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.compare_planners",
            "--sim-seconds",
            "1.5",
            "--rrt-seed",
            "123",
        ],
        check=True,
    )
    assert out.exists(), "compare_planners.md was not created"
    txt = out.read_text()
    assert "Planner KPI Compare" in txt
    assert "| A*" in txt and "| RRT" in txt
