import csv
import os

METRICS = "artifacts/training/metrics.csv"
MODEL = "artifacts/training/model_dummy.npz"
SUMMARY = "artifacts/training/summary.json"


def _rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def test_outputs_exist_and_nonempty():
    assert os.path.isfile(MODEL), "run trainer first"
    assert os.path.isfile(METRICS), "run trainer first"
    rows = _rows(METRICS)
    assert len(rows) >= 5
    assert all("loss" in r and "acc" in r for r in rows)


def test_loss_decreases_and_acc_is_reasonable():
    rows = _rows(METRICS)
    losses = [float(r["loss"]) for r in rows]
    accs = [float(r["acc"]) for r in rows]
    assert losses[-1] < losses[0] * 0.9  # at least 10% better
    assert accs[-1] >= 0.80  # linearly separable -> should be high
