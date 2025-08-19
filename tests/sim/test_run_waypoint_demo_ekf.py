import subprocess
import sys
from pathlib import Path


def test_waypoint_demo_ekf_smoke(tmp_path):
    """
    Runs the EKF waypoint demo briefly and checks that the CSV is produced
    with the expected columns. Keeps it very light so CI is fast.
    """
    artifacts = Path("artifacts")
    out_csv = artifacts / "waypoint_run_ekf.csv"

    # Clean prior output to avoid false positives
    try:
        out_csv.unlink()
    except FileNotFoundError:
        pass
    artifacts.mkdir(exist_ok=True)

    # Run the script for a tiny sim (2s) so CI stays quick
    cmd = [
        sys.executable,
        "-m",
        "scripts.run_waypoint_demo_ekf",
        "--sim-seconds",
        "2.0",
        "--dt",
        "0.02",
        "--wp-radius",
        "0.5",
    ]
    subprocess.run(cmd, check=True)

    assert out_csv.exists(), "EKF demo did not produce CSV output"
    header = out_csv.read_text().splitlines()[0].split(",")

    # Spot-check a few key columns (don't over-specify)
    for col in ["t", "px", "py", "vx", "vy", "ekf_px", "ekf_py", "wp_index"]:
        assert col in header, f"missing column: {col}"
