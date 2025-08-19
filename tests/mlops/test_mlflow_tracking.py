import os
import subprocess

import mlflow


def _run(cmd: list[str]):
    res = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return res.stdout.strip()


def test_mlflow_logging_roundtrip():
    # 1) ensure training artifacts exist (fast)
    _run(["python", "scripts/training/train_dummy.py", "--config", "configs/training/dummy.yaml"])
    assert os.path.isfile("artifacts/training/summary.json")

    # 2) log them to MLflow
    out = _run(
        [
            "python",
            "scripts/mlops/log_last_training.py",
            "--config",
            "configs/mlops/experiment.yaml",
        ]
    )
    assert "logged run_id=" in out

    # 3) query MLflow and assert we can see at least one run
    mlflow.set_tracking_uri("file:./mlruns")
    exps = {e.name: e.experiment_id for e in mlflow.search_experiments()}
    assert "northstrike" in exps
    runs = mlflow.search_runs(experiment_ids=[exps["northstrike"]])
    assert len(runs) >= 1
