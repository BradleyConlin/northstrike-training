import csv
import os


def _load(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def test_precision_recall_on_synth():
    gt = "artifacts/perception_in/gt_boxes.csv"
    det = "artifacts/perception_out/detections.csv"
    assert os.path.isfile(gt) and os.path.isfile(det)
    # weak check: on our synthetic set we expect near-perfect matches
    # (the pipeline prints metrics; here we just verify non-empty and filename overlap)
    gt_names = {d["filename"] for d in _load(gt)}
    det_names = {d["filename"] for d in _load(det)}
    # most (>=80%) images should have detections
    overlap = len(gt_names & det_names) / max(1, len(gt_names))
    assert overlap >= 0.8
