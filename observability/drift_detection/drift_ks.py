from __future__ import annotations

import math
from typing import Dict, List, Tuple

import numpy as np


def _load_numeric_table(csv_path: str) -> Dict[str, np.ndarray]:
    rows = []
    with open(csv_path, "r") as f:
        hdr = f.readline().strip().split(",")
        for line in f:
            parts = line.strip().split(",")
            if len(parts) != len(hdr):
                continue
            rows.append(parts)
    if not rows:
        return {}
    cols: Dict[str, List[float]] = {h: [] for h in hdr}
    for r in rows:
        for h, v in zip(hdr, r):
            try:
                cols[h].append(float(v))
            except ValueError:
                # skip non-numeric
                pass
    return {k: np.array(v, dtype=float) for k, v in cols.items() if len(v) > 0}


def ks_stat(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0 or len(b) == 0:
        return math.inf
    a = np.sort(a)
    b = np.sort(b)
    # empirical CDF difference (two-sample KS)
    ia = ib = 0
    da = db = 0.0
    n, m = len(a), len(b)
    d = 0.0
    while ia < n and ib < m:
        if a[ia] <= b[ib]:
            ia += 1
            da = ia / n
        else:
            ib += 1
            db = ib / m
        d = max(d, abs(da - db))
    return float(d)


def compare_csvs(
    baseline_csv: str, current_csv: str, max_p95: float = 0.20
) -> Tuple[float, Dict[str, float]]:
    base = _load_numeric_table(baseline_csv)
    curr = _load_numeric_table(current_csv)
    keys = sorted(set(base) & set(curr))
    per_col = {}
    vals = []
    for k in keys:
        d = ks_stat(base[k], curr[k])
        per_col[k] = d
        vals.append(d)
    p95 = float(np.percentile(vals, 95)) if vals else math.inf
    return (p95, per_col)  # caller decides pass/fail
