from __future__ import annotations

import numpy as np

from observability.drift_detection.drift_ks import compare_csvs


def _write_csv(path, cols):
    keys = list(cols)
    with open(path, "w") as f:
        f.write(",".join(keys) + "\n")
        n = min(len(cols[k]) for k in keys)
        for i in range(n):
            f.write(",".join(str(cols[k][i]) for k in keys) + "\n")


def test_ks_detects_distribution_shift(tmp_path):
    base = tmp_path / "base.csv"
    cur = tmp_path / "cur.csv"
    np.random.seed(0)
    _write_csv(base, {"a": np.random.normal(0, 1, 500), "b": np.random.uniform(0, 1, 500)})
    _write_csv(cur, {"a": np.random.normal(0.6, 1, 500), "b": np.random.uniform(0, 1, 500)})
    p95, per_col = compare_csvs(str(base), str(cur), max_p95=0.20)
    assert "a" in per_col and "b" in per_col
    assert p95 > 0.20  # drift should trigger due to mean shift on a
