#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import cv2

from src.perception.color_target import detect_color_targets, draw_boxes

IN_DIR = Path("artifacts/perception_in")
OUT_DIR = Path("artifacts/perception_out")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def iou(a, b):
    xa1, ya1, xa2, ya2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    xb1, yb1, xb2, yb2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    xi1, yi1 = max(xa1, xb1), max(ya1, yb1)
    xi2, yi2 = min(xa2, xb2), min(ya2, yb2)
    iw, ih = max(0, xi2 - xi1), max(0, yi2 - yi1)
    inter = iw * ih
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def main():
    # load GT if present
    gt = {}
    gt_csv = IN_DIR / "gt_boxes.csv"
    if gt_csv.exists():
        with open(gt_csv) as f:
            r = csv.DictReader(f)
            for d in r:
                gt[d["filename"]] = (int(d["x"]), int(d["y"]), int(d["w"]), int(d["h"]))

    det_rows = []
    tp = fp = fn = 0
    for img_path in sorted(IN_DIR.glob("*.png")):
        img = cv2.imread(str(img_path))
        boxes = detect_color_targets(img)
        det_rows.extend(
            {"filename": img_path.name, "x": b.x, "y": b.y, "w": b.w, "h": b.h} for b in boxes
        )
        # annotate
        ann = draw_boxes(img, boxes)
        cv2.imwrite(str(OUT_DIR / f"ann_{img_path.name}"), ann)

        if img_path.name in gt:
            # pick best iou
            g = gt[img_path.name]
            best = max([iou((b.x, b.y, b.w, b.h), g) for b in boxes] + [0.0])
            if best >= 0.5:
                tp += 1
            else:
                fn += 1
        else:
            fp += len(boxes)

    det_csv = OUT_DIR / "detections.csv"
    with open(det_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "x", "y", "w", "h"])
        w.writeheader()
        w.writerows(det_rows)

    # metrics (only if GT exists)
    if gt:
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        print(f"metrics: tp={tp} fp={fp} fn={fn}  precision={prec:.3f} recall={rec:.3f}")
    print(f"Wrote detections -> {det_csv} and annotated PNGs -> {OUT_DIR}")


if __name__ == "__main__":
    main()
