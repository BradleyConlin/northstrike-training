# Step 4 — Sensor Fusion & State Estimation

- Implemented: `src/estimators/ekf_cv.py` (constant-velocity EKF)
- Pipeline: `scripts/pipelines/estimator_offline.py` → writes `artifacts/waypoint_run_ekf.csv` and `artifacts/waypoint_plot_ekf.png`
- Tests (3 passing): 
  - `tests/estimators/test_ekf_smoke.py`
  - `tests/estimators/test_ekf_artifacts_contract.py` (adaptive KPI: motion or stability)
- Dashboard globs updated in `monitoring.yaml` (id: 4)
- Snapshot now shows Step 4: 🟢
