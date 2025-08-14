#!/usr/bin/env python3
import random

import mlflow

mlflow.set_tracking_uri("http://127.0.0.1:5000")
mlflow.set_experiment("sanity")
with mlflow.start_run(run_name="dummy"):
    for step in range(10):
        mlflow.log_metric("hover_rms_m", random.uniform(0.05, 0.25), step=step)
    mlflow.log_param("vehicle", "x500")
print("✅ logged")
