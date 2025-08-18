import pandas as pd

from scripts.evaluation.hover_kpi_report import compute_hover_kpis


def test_hover_kpi_contract_stationary_xy():
    n = 100
    t = [i / 20 for i in range(n)]  # ~5s @20Hz
    rel = [1.3 + (0.005 if i % 2 else -0.005) for i in range(n)]  # ±5mm around 1.3 m

    df = pd.DataFrame(
        {
            "t": t,
            "rel_alt_m": rel,
            # XY intentionally missing -> xy_rms_m should default to 0.0 (stationary)
        }
    )

    k = compute_hover_kpis(df=df)

    # Required keys (hard contract)
    for key in [
        "samples",
        "duration_s",
        "alt_mean",
        "alt_std",
        "alt_rmse",
        "hover_rms_m",
        "max_alt_dev",
        "xy_std",
        "xy_rms_m",
        "hover_score",
    ]:
        assert key in k, f"missing key: {key}"

    assert k["samples"] == n
    assert 4.9 <= k["duration_s"] <= 5.1
    assert 1.2 <= k["alt_mean"] <= 1.4
    assert k["hover_rms_m"] is None or k["hover_rms_m"] >= 0.0
    assert 0.0 <= k["xy_rms_m"] < 0.01  # stationary XY
    assert 0.0 <= k["hover_score"] <= 1.0
