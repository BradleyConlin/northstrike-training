# Step 14 – Hardware‑in‑the‑Loop (HIL) Smoke

This is a **mock‑HIL** smoke to validate the estimator under simple sensor faults.

## Run
```bash
PYTHONPATH="$PWD" python hil/scripts/start_hil_session.py
PYTHONPATH="$PWD" python -m pytest -q tests/hil
Expected
Inject IMU bias ~±0.02 g and GPS latency ~10–20 ms.

Estimator bias KPI within threshold → test passes.

Store JSON + CSV in artifacts/hil/.
