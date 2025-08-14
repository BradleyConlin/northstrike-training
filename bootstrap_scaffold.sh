#!/usr/bin/env bash
set -euo pipefail

# sanity: run from repo root
test -d .git || { echo "Run from the repo root (a .git directory must exist)"; exit 1; }

# helper
mk() { mkdir -p "$@"; }
stub() { mkdir -p "$(dirname "$1")"; [ -e "$1" ] || printf "%s\n" "${2:-}" > "$1"; }

echo "Creating directories..."
mk docs docs/adr docs/compatibility
mk data/{raw,processed,synthetic,external,logs}
mk datasets/{flight_logs,vision_datasets,models_metadata}
mk models/{checkpoints,exported,configs}
mk simulation/{gazebo/{worlds,models,plugins},px4/{sitl_params,launch},ros2/packages,missions/v1.0,domain_randomization/{textures,scripts},scripts}
mk src/{planners/{global,local,hybrid,utils},controllers/{pid,lqr,mpc,nonlinear,fixed_wing,utils},estimators/{ekf,vio,slam},perception/{detect,segment,track,sfm},multi_agent/{formation,coverage,allocation,marl},rl/{algos,envs,rewards,curriculum,callbacks},sysid/{estimators,pipelines,tecs_l1},interfaces/{mavlink,ros2},utils}
mk scripts/{data_preprocessing,training,evaluation,visualization,deployment,sysid}
mk benchmarks/{scenarios/{hover_wind,waypoint_obstacles},metrics,reports}
mk mlops/{mlflow,registry,reports/{templates,examples},scripts}
mk hil/{wiring_diagrams,test_plans,scripts}
mk observability/{telemetry_schema,exporters,dashboards/grafana,drift_detection}
mk deployment/{edge_builds/{toolchains,jetson,rpi},docker,inference,pipelines}
mk configs/{training,environment,simulation,hardware,evaluation,params/{px4/v1.0,ardupilot/v1.0}}
mk data_governance safety/{sora,sop,geofencing} secrets tests/{unit,integration,simulation,hil} .github/{workflows,templates}

echo "Placing .gitkeep files in data-like folders..."
for d in data datasets models/{checkpoints,exported,configs} benchmarks/reports; do
  find "$d" -type d -empty -exec bash -c 'touch "$0/.gitkeep"' {} \;
done

echo "Top-level project files..."
stub .gitignore \
"# Python
__pycache__/
*.pyc
.env
.venv/
# Data & artifacts
data/*/
datasets/*/
models/checkpoints/
models/exported/
mlruns/
# OS / IDE
.DS_Store
.idea/
.vscode/
"

stub .pre-commit-config.yaml \
"repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks: [{id: black}]
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks: [{id: isort}]
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks: [{id: flake8}]
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks: [{id: detect-secrets}]
"

stub Makefile \
'.PHONY: sim_hover_bench rl_train_hover sysid_run bench_waypoints promote

sim_hover_bench:
\tpython scripts/evaluation/eval_perception.py --scenario hover_wind

rl_train_hover:
\tpython scripts/training/rl_train.py --config configs/training/rl_hover.yaml

sysid_run:
\tpython scripts/sysid/run_sysid.py

bench_waypoints:
\tpython scripts/evaluation/eval_perception.py --scenario waypoint_obstacles

promote:
\tpython mlops/scripts/promote_model.py $${MODEL:+--model $(MODEL)}
'

stub requirements.txt \
"numpy
scipy
pandas
matplotlib
pyyaml
opencv-python
torch
torchvision
onnx
onnxruntime
albumentations
mlflow
jinja2
gymnasium
stable-baselines3
networkx
shapely
pymavlink
mavsdk
prometheus-client
paho-mqtt
"

stub pyproject.toml \
"[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = 'black'
"

stub README.md \
"# Northstrike Training & Deployment

This repo contains the full scaffold for simulation → training → evaluation → deployment → observability.
See \`docs/architecture_overview.md\` and the per-module READMEs. Fill in code where marked TODO.

## Quickstart
- \`make rl_train_hover\` (after setting up Python env)
- \`make bench_waypoints\` to run a sample benchmark

## Structure
See the repository tree and \`docs/\` for details."

echo "Docs..."
stub docs/architecture_overview.md "# Architecture Overview\n\n(High-level diagrams and data flow go here.)"
stub docs/usage_instructions.md "# Usage Instructions\n\n(Env setup, running sims, training, deployment.)"
stub docs/data_schema.md "# Data Schema\n\n(Define dataset manifests, fields, and metadata.)"
stub docs/algorithms_overview.md "# Algorithms Overview\n\n(Path planning, control, estimation, perception.)"
stub docs/dependencies.md "# Dependencies\n\n(List versions; CUDA/cuDNN; ROS2; PX4/ArduPilot.)"

stub docs/compatibility/airframe_matrix.md "# Airframe Matrix\n\n(List supported airframes vs features.)"
stub docs/compatibility/autopilot_apis.md "# Autopilot APIs\n\n(MAVLink/MAVSDK endpoints used.)"
stub docs/compatibility/sensor_sync.md "# Sensor Sync\n\n(Time sync strategy, latency budgets.)"

stub docs/adr/0001-mlflow-vs-wandb.md "Status: Proposed\nContext: Tracking choice.\nDecision: TBD\nConsequences: TBD\n"
stub docs/adr/0002-fixed-wing-tecs-l1.md "Status: Proposed\nContext: Guidance/energy control.\nDecision: TBD\nConsequences: TBD\n"
stub docs/adr/0003-rl-safety-shields.md "Status: Proposed\nContext: RL safety.\nDecision: TBD\nConsequences: TBD\n"

echo "Simulation seeds..."
stub simulation/gazebo/worlds/airfield_day.world "<world/>"
stub simulation/gazebo/worlds/waypoint_obstacles.world "<world/>"
stub simulation/px4/sitl_params/default.params "# PX4 params go here"
stub simulation/px4/launch/start_sitl.launch.py "print('TODO: launch PX4 SITL')"
stub simulation/scripts/start_sitl.py "print('TODO: Start SITL with args')"
stub simulation/scripts/record_bag.py "print('TODO: rosbag record script')"

echo "Domain randomization..."
stub simulation/domain_randomization/wind_profiles.yaml \
"default:\n  wind_mps: [0,10]\n  gust_mps: [0,4]\n"
stub simulation/domain_randomization/sensor_noise.yaml \
"default:\n  imu_std: [0.001, 0.02]\n  baro_std: [0.2, 1.5]\n  gps_hdop: [0.5, 2.0]\n"
stub simulation/domain_randomization/scripts/apply_randomization.py "print('TODO: apply sim randomization')"

echo "Benchmarks..."
stub benchmarks/scenarios/hover_wind/scenario.yaml \
"name: hover_wind\nseeds: 10\nworld: airfield_day.world\n"
stub benchmarks/scenarios/hover_wind/world.sdf "<sdf/>"
stub benchmarks/scenarios/waypoint_obstacles/scenario.yaml \
"name: waypoint_obstacles\nseeds: 10\nworld: waypoint_obstacles.world\n"
stub benchmarks/scenarios/waypoint_obstacles/world.sdf "<sdf/>"
stub benchmarks/metrics/kpis.yaml \
"hover:\n  max_rms_pos_m: 0.25\n  success_rate: 0.98\nwaypoint:\n  max_cross_track_m: 1.0\n  collision_rate: 0.0\n"

echo "Configs..."
stub configs/training/perception_default.yaml "model: yolov8n\nimg_size: 640\nepochs: 100\n"
stub configs/training/mpc_position.yaml "horizon: 20\ndt: 0.05\nweights: {pos: 1.0, vel: 0.2, effort: 0.05}\n"
stub configs/training/rl_hover.yaml \
"algo: PPO\nenv: Px4GzHoverEnv-v0\nreward: {hover_pos_w: 1.0, vel_pen: 0.2, crash_pen: 10.0}\nsafety:\n  geofence: {x: [-50,50], y: [-50,50], z: [1,30]}\ncurriculum:\n  wind_mps: [0,8]\n"
stub configs/environment/.env.example "MLFLOW_TRACKING_URI=http://127.0.0.1:5000\n"
stub configs/simulation/randomization_profiles.yaml "use: default\n"
stub configs/hardware/fixed_wing_tecs.yaml "tas_min: 14\ntas_max: 32\ntime_const: 5\nl1_period_s: 12\n"
stub configs/evaluation/default_kpis.yaml "latency_ms_max: 50\nsuccess_rate_min: 0.95\n"
stub configs/params/px4/v1.0/airframe_x500.params "# PX4 param pack"
stub configs/params/px4/v1.0/fixed_wing_tecs.params "# PX4 TECS pack"
stub configs/params/ardupilot/v1.0/plane_tecs.param "# ArduPilot TECS pack"

echo "ML Ops..."
stub mlops/mlflow/config.yaml \
"tracking_uri: http://127.0.0.1:5000\nartifact_location: ./mlruns\nexperiments:\n  perception: perception-exp\n  control: control-exp\n  rl: rl-exp\npromotion_gates:\n  min_success_rate: 0.95\n  max_latency_ms: 50\n"
stub mlops/registry/policies.md "# Promotion Policies\n\n(Define gates and approval process.)\n"
stub mlops/reports/templates/eval_report.jinja2 "<html><body><h1>{{ title }}</h1></body></html>\n"
stub mlops/reports/examples/eval_report_example.html "<html><body>Example</body></html>\n"
stub mlops/scripts/start_mlflow.py "print('TODO: start MLflow server/container')"
stub mlops/scripts/gen_report.py "print('TODO: render Jinja2 eval report')"
stub mlops/scripts/register_model.py "print('TODO: register model in MLflow')"
stub mlops/scripts/promote_model.py "print('TODO: apply gates and tag model')"

echo "Source stubs (key files only)..."
stub src/utils/train_loops.py "def train_loop(cfg):\n    print('TODO: training loop')\n"
stub src/utils/data_loader.py "def load_dataset(cfg):\n    print('TODO: dataset loader')\n"
stub src/rl/envs/px4_gz_hover_env.py "class Px4GzHoverEnv:\n    def __init__(self, cfg):\n        pass\n"
stub src/controllers/fixed_wing/tecs.py "class TECS:\n    def step(self, state, refs):\n        pass\n"
stub src/planners/global/a_star.py "def plan(start, goal, costmap):\n    return []\n"
stub src/estimators/ekf/ekf_core.py "class EKF:\n    def step(self, meas):\n        pass\n"
stub src/perception/detect/yolo_train.py "def main():\n    print('TODO: YOLO train')\n\nif __name__=='__main__': main()\n"

echo "Scripts..."
stub scripts/training/train_generic.py "print('TODO: generic trainer')"
stub scripts/training/rl_train.py "print('TODO: RL train entrypoint')"
stub scripts/evaluation/eval_perception.py "print('TODO: perception eval runner')"
stub scripts/sysid/run_sysid.py "print('TODO: run SysID pipeline')"
stub scripts/deployment/export_to_onnx.py "print('TODO: export model to ONNX')"
stub scripts/deployment/calibrate_tensorrt.py "print('TODO: build TensorRT engine')"

echo "HIL / Observability..."
stub hil/test_plans/estimator_bias_check.md "# Estimator Bias Check\n\n(Procedure here.)"
stub observability/telemetry_schema/flight_telemetry.proto "syntax = \"proto3\";\nmessage FlightTelemetry { double ts=1; }\n"
stub observability/exporters/prometheus_exporter.py "print('TODO: expose Prometheus metrics')"
stub observability/exporters/mqtt_exporter.py "print('TODO: publish to MQTT')"
stub observability/dashboards/grafana/perception.json "{}"
stub observability/dashboards/grafana/control.json "{}"
stub observability/drift_detection/data_drift.py "print('TODO: data drift check')"
stub observability/drift_detection/model_drift.py "print('TODO: model drift check')"

echo "Governance & Safety..."
stub data_governance/labeling_sop.md "# Labeling SOP\n\n(Classes, rules, edge cases.)"
stub data_governance/qc_checklists.md "# QC Checklist\n\n(Blur, dupes, distro, coverage.)"
stub data_governance/dataset_versioning.md "# Dataset Versioning\n\n(Manifests + hashes.)"
stub data_governance/licenses_third_party.md "# Third-Party Licenses\n"
stub safety/sora/risk_assessment_template.md "# SORA Template\n"
stub safety/sop/preflight_checklist.md "- Batteries checked\n- GPS fix\n- Geofence loaded\n- RTL configured\n"
stub safety/sop/emergency_procedures.md "- Loss of link: RTL\n- Low battery: land\n"
stub safety/geofencing/nfz_layers.geojson "{ \"type\": \"FeatureCollection\", \"features\": [] }"

echo "Tests & GitHub Actions..."
stub tests/hil/test_estimator_bias.py "def test_bias():\n    assert True\n"
stub .github/workflows/lint_test.yml \
"name: Lint & Unit\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: {python-version: '3.10'}\n      - run: pip install -r requirements.txt\n      - run: pip install pre-commit\n      - run: pre-commit run --all-files\n      - run: pytest -q\n"
stub .github/workflows/bench_and_report.yml \
"name: Bench & Report\non:\n  workflow_dispatch:\njobs:\n  bench:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: {python-version: '3.10'}\n      - run: pip install -r requirements.txt\n      - run: python scripts/evaluation/eval_perception.py --scenario hover_wind\n      - run: python mlops/scripts/gen_report.py\n"

echo "Done. ✅"
