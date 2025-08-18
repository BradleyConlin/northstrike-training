#!/usr/bin/env python3
"""
Log a couple of dummy metrics to MLflow.

Safe for CI:
- Importing this module does not talk to MLflow.
- All MLflow usage is behind `main()` and the __main__ guard.
- If MLflow is missing or a tracking server is unavailable, we exit 0.
"""
from __future__ import annotations

import argparse
import os
import random

try:
    import mlflow  # type: ignore
except Exception:  # pragma: no cover - optional dep
    mlflow = None  # type: ignore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Log dummy metrics to MLflow.")
    parser.add_argument(
        "--runs", type=int, default=1, help="How many dummy runs to log (default: 1)"
    )
    parser.add_argument(
        "--tracking-uri",
        default=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"),
        help="MLflow tracking URI (default from $MLFLOW_TRACKING_URI or local MLflow)",
    )
    parser.add_argument(
        "--experiment",
        default="sanity",
        help='Experiment name to use (default: "sanity")',
    )
    args = parser.parse_args(argv)
    # If MLflow isn't available in CI, exit successfully.
    if mlflow is None:
        return 0

    try:
        mlflow.set_tracking_uri(args.tracking_uri)
        mlflow.set_experiment(args.experiment)
        for i in range(int(args.runs)):
            with mlflow.start_run(run_name=f"dummy-{i+1}"):
                mlflow.log_metric("accuracy", random.random())
                mlflow.log_metric("loss", random.random())
    except (Exception, KeyboardInterrupt):
        # In CI, we ignore MLflow errors (and Ctrl+C) to keep smoke tests green.
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
