.PHONY: sim_hover_bench rl_train_hover sysid_run bench_waypoints promote

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

