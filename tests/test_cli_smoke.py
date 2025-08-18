import importlib
import runpy
import sys

import pytest

SCRIPTS = [
    "scripts.evaluation.assert_hover_kpis",
    "scripts.evaluation.assert_mission_kpis",
    "scripts.evaluation.eval_perception",
    "scripts.evaluation.hover_kpi_report",
    "scripts.evaluation.log_dummy_metrics",
    "scripts.evaluation.waypoint_kpi_report",
]


@pytest.mark.parametrize("mod", SCRIPTS)
def test_imports(mod):
    importlib.import_module(mod)


@pytest.mark.parametrize("mod", SCRIPTS)
def test_help_runs(mod, monkeypatch):
    # Run the module as a script with --help; argparse should exit cleanly.
    monkeypatch.setattr(sys, "argv", [mod.rsplit(".", 1)[-1], "--help"])
    with pytest.raises(SystemExit):
        runpy.run_module(mod, run_name="__main__")
