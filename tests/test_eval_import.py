from eval.core import compute_hover_kpis


def test_eval_import_smoke():
    assert callable(compute_hover_kpis)
