import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts/tools/gen_demo_plan.py"
PLAN = ROOT / "simulation/missions/v1.0/waypoints_demo.plan"


def test_gen_demo_plan_structure():
    # regenerate to ensure deterministic output
    subprocess.check_call(["python3", str(GEN), "--write-sha"])
    d = json.loads(PLAN.read_text())
    assert d["fileType"] == "Plan"
    assert d["mission"]["version"] >= 2
    items = d["mission"]["items"]
    assert isinstance(items, list) and len(items) >= 4
    for it in items:
        assert it["type"] == "SimpleItem"
        assert it["command"] == 16  # MAV_CMD_NAV_WAYPOINT
        assert it["frame"] == 3  # MAV_FRAME_GLOBAL_RELATIVE_ALT
        la, lo, al = it["coordinate"]
        assert isinstance(la, float) and isinstance(lo, float)
        assert isinstance(al, (int, float))
