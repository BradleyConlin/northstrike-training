import pandas as pd

from scripts.evaluation.hover_kpi_report import compute_hover_kpis


def test_hover_kpi_basics():
    n = 100
    t = pd.Series([i / 20 for i in range(n)])  # 5s @20Hz
    rel = 1.3 + 0.05 * ((-1) ** t.index) / 20  # tiny ± noise
    df = pd.DataFrame(
        {
            "t": t,
            "lat": 47.0,
            "lon": 8.0,
            "abs_alt_m": 500 + 1.3,
            "rel_alt_m": rel,
            "vn": 0.0,
            "ve": 0.0,
            "vd": 0.0,
            "battery_pct": 100.0,
            "in_air": 1,
        }
    )
    k = compute_hover_kpis(df)
    assert k["samples"] == n
    assert k["hover_rms_m"] < 0.2
    assert k["xy_rms_m"] < 0.01
