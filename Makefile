.PHONY: sim_hover_bench rl_train_hover sysid_run bench_waypoints promote \
        sitl_x500 sitl_plane qgc sitl_qgc

sim_hover_bench:
	python scripts/evaluation/eval_perception.py --scenario hover_wind

rl_train_hover:
	python scripts/training/rl_train.py --config configs/training/rl_hover.yaml

sysid_run:
	python scripts/sysid/run_sysid.py

bench_waypoints:
	python scripts/evaluation/eval_perception.py --scenario waypoint_obstacles

promote:
	python mlops/scripts/promote_model.py $${MODEL:+--model $(MODEL)}

sitl_x500:
	@[ -n "$$PX4_FIRMWARE" ] || (echo "Set PX4_FIRMWARE first"; exit 1)
	cd $$PX4_FIRMWARE && PX4_SIM_MODEL=x500 make px4_sitl gz_x500

sitl_plane:
	@[ -n "$$PX4_FIRMWARE" ] || (echo "Set PX4_FIRMWARE first"; exit 1)
	cd $$PX4_FIRMWARE && PX4_SIM_MODEL=plane make px4_sitl gz_plane

qgc:
	@~/Downloads/QGroundControl.AppImage || true

sitl_qgc:
	./scripts/dev_run_sitl_qgc.sh

.PHONY: sdk_smoke
sdk_smoke:
	python3 scripts/control/mavsdk_takeoff_land.py --alt 6 --hold 8

.PHONY: stop_sitl
stop_sitl:
	- pkill -f px4_sitl_default || true
	- pkill -f "gz sim" || pkill -f gazebo || true

.PHONY: log_hover
log_hover:
	python3 scripts/logging/mavsdk_telemetry_record.py --out datasets/flight_logs/hover.csv --hz 20

.PHONY: hover_kpi
hover_kpi:
	python3 scripts/evaluation/hover_kpi_report.py --csv datasets/flight_logs/test_hover.csv

.PHONY: mlflow_up mlflow_dummy
mlflow_up:
	./mlops/scripts/start_mlflow.sh

mlflow_dummy:
	python3 scripts/evaluation/log_dummy_metrics.py

.PHONY: hover_pipeline
hover_pipeline:
	python3 scripts/pipelines/hover_and_record.py

.PHONY: mission_pipeline waypoint_kpi
mission_pipeline:
	python3 scripts/pipelines/mission_run_and_record.py --plan simulation/missions/v1.0/waypoints_demo.plan


.PHONY: waypoint_kpi
waypoint_kpi:
	@f=$$(ls -t datasets/flight_logs/mission_*.csv 2>/dev/null | head -n1); \
	test -n "$$f" || { echo "No mission_*.csv found. Run make mission_pipeline first."; exit 1; }; \
	python3 scripts/evaluation/waypoint_kpi_report.py --csv "$$f" --plan simulation/missions/v1.0/waypoints_demo.plan

.PHONY: stop_sdk
stop_sdk:
	- pkill -f mavsdk_server || true
	- pkill -f mission_run_and_record.py || true
	- pkill -f mavsdk_takeoff_land.py || true

.PHONY: mlflow_up_bg mlflow_down
mlflow_up_bg:
	@nohup ./mlops/scripts/start_mlflow.sh > .mlflow.log 2>&1 &
	@echo $$! > .mlflow.pid
	@echo "MLflow started (PID $$(cat .mlflow.pid)) → http://127.0.0.1:5000"

mlflow_down:
	-@[ -f .mlflow.pid ] && kill "$$(cat .mlflow.pid)" 2>/dev/null || true
	-@rm -f .mlflow.pid
	@echo "MLflow stopped."

.PHONY: smoke_hover smoke_mission smoke
smoke_hover:
	$(MAKE) hover_pipeline
	python3 scripts/evaluation/assert_hover_kpis.py \
		--csv $$(ls -t datasets/flight_logs/hover_*.csv | head -n1) \
		--min-samples 250 --max-hover-rms 1.6 --max-xy-rms 0.05

smoke_mission:
	$(MAKE) mission_pipeline
	python3 scripts/evaluation/assert_mission_kpis.py \
		--csv datasets/flight_logs/mission_latest.csv \
		--plan simulation/missions/v1.0/waypoints_demo.plan \
		--require-visited 5 --max-mean 12 --max-max 25

smoke: smoke_hover smoke_mission

.PHONY: plan_demo
plan_demo:
	python3 scripts/tools/gen_demo_plan.py --write-sha

.PHONY: precommit
precommit:
	pre-commit run --all-files

.PHONY: test ci_local
test:
	python -m pytest -q

ci_local: precommit test

test-unit:
\tpytest -q tests/unit --maxfail=1 --disable-warnings

test-sim:
\tpytest -q tests/simulation --maxfail=1 --disable-warnings

bench:
	python -m scripts.evaluation.compare_planners_sweep --seeds 3 --sim-seconds 2.0
	python -m scripts.evaluation.run_waypoint_controller_bench --controller lqr --seeds 3 --sim-seconds 1.5 && python -m scripts.evaluation.run_waypoint_controller_bench --controller pp --seeds 3 --sim-seconds 1.5
