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
