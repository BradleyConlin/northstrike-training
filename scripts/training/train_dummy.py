#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import yaml


# MLflow is optional: if not installed, we just skip logging to it.
def try_mlflow_log(cfg: dict, artifacts: list[Path], final_metrics: dict):
    try:
        import mlflow
    except Exception:
        print("MLflow not available; skipping MLflow logging.")
        return
    try:
        mlflow.set_tracking_uri(cfg.get("tracking_uri", "file:./mlruns"))
        mlflow.set_experiment(cfg.get("experiment_name", "northstrike"))
        with mlflow.start_run(run_name=cfg.get("run_name", "dummy")):
            mlflow.log_params(
                {
                    "epochs": cfg.get("epochs"),
                    "lr": cfg.get("lr"),
                    "seed": cfg.get("seed"),
                    "n_samples": cfg.get("n_samples"),
                }
            )
            mlflow.log_metrics(final_metrics)
            for p in artifacts:
                if p.is_file():
                    mlflow.log_artifact(str(p))
        print("Logged to MLflow.")
    except Exception as e:
        print(f"MLflow logging failed: {e}")


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def make_data(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    # linearly separable with mild noise
    w_true = np.array([1.5, -0.8], dtype=float)
    b_true = 0.3
    X = rng.normal(0, 1, size=(n, 2))
    logits = X @ w_true + b_true + rng.normal(0, 0.2, size=n)
    y = (logits > 0).astype(int)
    return X, y


def train_logreg(X: np.ndarray, y: np.ndarray, epochs: int, lr: float, seed: int):
    rng = np.random.default_rng(seed)
    n, d = X.shape
    # add bias column
    Xb = np.hstack([X, np.ones((n, 1))])
    w = rng.normal(0, 0.1, size=(d + 1,))
    history = []
    for ep in range(1, epochs + 1):
        z = Xb @ w
        p = sigmoid(z)
        # loss: mean BCE
        eps = 1e-9
        loss = -np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))
        pred = (p >= 0.5).astype(int)
        acc = float(np.mean(pred == y))
        # gradient
        grad = (Xb.T @ (p - y)) / n
        w -= lr * grad
        history.append({"epoch": ep, "loss": float(loss), "acc": acc})
    return w, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/training/dummy.yaml")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    out_dir = Path(cfg.get("output_dir", "artifacts/training"))
    out_dir.mkdir(parents=True, exist_ok=True)

    X, y = make_data(int(cfg.get("n_samples", 400)), int(cfg.get("seed", 7)))
    w, hist = train_logreg(
        X, y, int(cfg.get("epochs", 25)), float(cfg.get("lr", 0.2)), int(cfg.get("seed", 7))
    )

    # save artifacts
    metrics_csv = out_dir / "metrics.csv"
    with metrics_csv.open("w", newline="") as f:
        wri = csv.DictWriter(f, fieldnames=["epoch", "loss", "acc"])
        wri.writeheader()
        wri.writerows(hist)

    model_npz = out_dir / "model_dummy.npz"
    np.savez(model_npz, w=w)

    summary_json = out_dir / "summary.json"
    final = {"final_loss": hist[-1]["loss"], "final_acc": hist[-1]["acc"]}
    summary_json.write_text(json.dumps(final, indent=2))

    print(f"Wrote: {metrics_csv}, {model_npz}, {summary_json}")

    # optional MLflow logging
    try_mlflow_log(cfg, [metrics_csv, model_npz, summary_json], final)


if __name__ == "__main__":
    main()
