#!/usr/bin/env python3
import os
import random

try:
    import mlflow
except Exception:
    mlflow = None  # optional for --help/import in CI
if mlflow is not None:
    try:
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    except Exception:
        pass
if mlflow is not None:
    try:
        mlflow.set_experiment("sanity")
    except Exception:
        pass
with mlflow.start_run(run_name="dummy"):
    for step in range(10):
        mlflow.log_metric("hover_rms_m", random.uniform(0.05, 0.25), step=step)
    mlflow.log_param("vehicle", "x500")
print("✅ logged")
