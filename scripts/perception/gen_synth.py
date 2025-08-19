#!/usr/bin/env python3
from __future__ import annotations

import csv
import random
from pathlib import Path

import cv2
import numpy as np

OUTDIR = Path("artifacts/perception_in")
GT_CSV = OUTDIR / "gt_boxes.csv"
OUTDIR.mkdir(parents=True, exist_ok=True)

W, H = 320, 240
GREEN = (0, 255, 0)


def main(n=12):
    rows = []
    for i in range(n):
        img = np.full((H, W, 3), 30, dtype=np.uint8)  # dark background
        # random box
        w = random.randint(30, 60)
        h = random.randint(30, 60)
        x = random.randint(5, W - w - 5)
        y = random.randint(5, H - h - 5)
        cv2.rectangle(img, (x, y), (x + w, y + h), GREEN, -1)
        # slight noise
        noise = np.random.randint(0, 12, (H, W, 3), dtype=np.uint8)
        img = cv2.add(img, noise)
        fn = OUTDIR / f"img_{i:03d}.png"
        cv2.imwrite(str(fn), img)
        rows.append({"filename": fn.name, "x": x, "y": y, "w": w, "h": h})
    with open(GT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "x", "y", "w", "h"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {n} images to {OUTDIR} and GT to {GT_CSV}")


if __name__ == "__main__":
    main()
