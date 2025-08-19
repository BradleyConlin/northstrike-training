#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import mlflow
import yaml

CFG = "configs/mlops/experiment.yaml"
ART_DIR = Path("artifacts/training")
METRICS = ART_DIR / "metrics.csv"
MODEL = ART_DIR / "model_dummy.npz"
SUMMARY = ART_DIR / "summary.json"


def load_cfg(path: str) -> dict:
    return yaml.safe_load(open(path))


def read_metrics_csv(p: Path) -> list[dict]:
    with p.open() as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=CFG)
    args = ap.parse_args()
    cfg = load_cfg(args.config)

    # basic checks
    assert METRICS.is_file(), f"missing {METRICS}, run training first"
    assert SUMMARY.is_file(), f"missing {SUMMARY}, run training first"

    rows = read_metrics_csv(METRICS)
    best_acc = max(float(r["acc"]) for r in rows)
    last = json.loads(SUMMARY.read_text())
    final_loss = float(last.get("final_loss", 0.0))
    final_acc = float(last.get("final_acc", 0.0))

    # log to MLflow
    mlflow.set_tracking_uri(cfg.get("tracking_uri", "file:./mlruns"))
    mlflow.set_experiment(cfg.get("experiment_name", "northstrike"))
    with mlflow.start_run(run_name=cfg.get("run_name", "log-last-training")) as run:
        mlflow.log_params(
            {
                "source": "artifacts/training",
                "epochs": len(rows),
            }
        )
        mlflow.log_metrics(
            {
                "final_loss": final_loss,
                "final_acc": final_acc,
                "best_acc": best_acc,
            }
        )
        for p in [METRICS, MODEL, SUMMARY]:
            if p.is_file():
                mlflow.log_artifact(str(p))
        print(f"OK: logged run_id={run.info.run_id}")


if __name__ == "__main__":
    main()
