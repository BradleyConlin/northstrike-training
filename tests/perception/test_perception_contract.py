import csv
import glob
import os


def test_artifacts_exist_after_pipeline():
    assert os.path.isdir("artifacts/perception_in")
    assert os.path.isdir("artifacts/perception_out")
    det = "artifacts/perception_out/detections.csv"
    assert os.path.isfile(det), "run detection pipeline first"
    with open(det) as f:
        r = csv.DictReader(f)
        rows = list(r)
    assert len(rows) >= 1
    # annotated images exist
    anns = glob.glob("artifacts/perception_out/ann_*.png")
    assert len(anns) >= 1
