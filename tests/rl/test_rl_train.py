import json
import os
import subprocess
import sys

ART = "artifacts/rl/summary.json"


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def test_training_produces_safe_and_efficient_policy():
    # run with fewer episodes for CI speed, but still converges
    _run([sys.executable, "scripts/rl/train_grid.py", "--episodes", "250"])
    assert os.path.isfile(ART)
    s = json.loads(open(ART).read())
    assert s["train_success_rate"] >= 0.8
    # should take close to shortest path (allow slack)
    assert s["eval_steps"] <= s["optimal_steps"] + 10
    # the safety wrapper should discourage risky cells
    assert s["eval_unsafe_steps"] <= 2
