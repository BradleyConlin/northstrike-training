import json
import subprocess
import sys


def test_waypoint_kpis_from_demo(tmp_path):
    # Generate a very short run so CI stays quick
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.run_waypoint_demo",
            "--sim-seconds",
            "2.0",
            "--dt",
            "0.02",
            "--wp-radius",
            "0.5",
        ],
        check=True,
    )

    out = tmp_path / "kpis.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluation.waypoint_kpi_report",
            "--csv",
            "artifacts/waypoint_run.csv",
            "--json-out",
            str(out),
        ],
        check=True,
    )

    data = json.loads(out.read_text())
    for key in ["avg_err", "med_err", "rms_err", "max_err", "hits", "duration_s", "rating"]:
        assert key in data
    assert data["avg_err"] >= 0.0
