#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from typing import Dict, List
from urllib.parse import urlparse

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def load_labelmap(path: str) -> Dict:
    if yaml is None:
        raise RuntimeError("PyYAML required for label map. `pip install pyyaml`")
    with open(path, "r") as f:
        lm = yaml.safe_load(f) or {}
    classes = lm.get("classes", [])
    if not classes or not isinstance(classes, list):
        raise ValueError("labelmap.yaml must define a list `classes`")
    return {"classes": classes, "index": {c: i for i, c in enumerate(classes)}}


def index_images(images_root: str) -> Dict[str, str]:
    idx = {}
    for dp, _, files in os.walk(images_root):
        for fn in files:
            low = fn.lower()
            if low.endswith((".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")):
                idx[fn] = os.path.join(dp, fn)
    return idx


def find_image_path(task: Dict, img_index: Dict[str, str]) -> str | None:
    raw = task.get("data", {}).get("image") or ""
    if not raw:
        return None
    # tolerate URLs or file paths
    base = os.path.basename(urlparse(raw).path) or os.path.basename(raw)
    return img_index.get(base)


def write_yolo(labels_path: str, lines: List[str], overwrite=False) -> None:
    os.makedirs(os.path.dirname(labels_path), exist_ok=True)
    if not overwrite and os.path.exists(labels_path):
        return
    with open(labels_path, "w") as f:
        for ln in lines:
            f.write(ln + "\n")


def rect_to_yolo(val: Dict, label_name: str, label_index: Dict[str, int]) -> str | None:
    # Label Studio rectangles are percent of image dims (0..100)
    if label_name not in label_index:
        return None
    cls = label_index[label_name]
    x = float(val.get("x", 0.0))
    y = float(val.get("y", 0.0))
    w = float(val.get("width", 0.0))
    h = float(val.get("height", 0.0))
    # convert top-left (percent) → YOLO (center normalized 0..1)
    cx = (x + w / 2.0) / 100.0
    cy = (y + h / 2.0) / 100.0
    wn = w / 100.0
    hn = h / 100.0
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < wn <= 1.0 and 0.0 < hn <= 1.0):
        return None
    return f"{cls} {cx:.6f} {cy:.6f} {wn:.6f} {hn:.6f}"


def convert(
    export_json: str, images_root: str, labels_root: str, labelmap_path: str, overwrite=False
) -> int:
    lm = load_labelmap(labelmap_path)
    idx = index_images(images_root)

    with open(export_json, "r") as f:
        tasks = json.load(f)

    converted = 0
    skipped = 0
    for task in tasks:
        img_path = find_image_path(task, idx)
        if not img_path:
            skipped += 1
            continue
        rel = os.path.relpath(img_path, images_root)
        out_txt = os.path.join(labels_root, os.path.splitext(rel)[0] + ".txt")

        # Label Studio: look inside "annotations"[*]["result"]
        annos = task.get("annotations") or task.get("completions") or []
        results = []
        for a in annos:
            results.extend(a.get("result", []))

        lines: List[str] = []
        for r in results:
            if r.get("type") not in {"rectanglelabels", "bndbox"}:
                continue
            val = r.get("value", {})
            labels = val.get("rectanglelabels") or val.get("labels") or []
            if not labels:
                continue
            yolo_line = rect_to_yolo(val, labels[0], lm["index"])
            if yolo_line:
                lines.append(yolo_line)

        write_yolo(out_txt, lines, overwrite=overwrite)
        converted += 1

    print(f"[convert] images matched: {converted}, tasks skipped (no image match): {skipped}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert Label Studio JSON export → YOLO txt.")
    ap.add_argument("--export", required=True, help="Label Studio JSON export")
    ap.add_argument("--images", required=True, help="images root (e.g., data/images)")
    ap.add_argument("--labels", required=True, help="labels root (e.g., data/labels)")
    ap.add_argument("--labelmap", default="configs/labeling/labelmap.yaml")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()
    return convert(args.export, args.images, args.labels, args.labelmap, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
