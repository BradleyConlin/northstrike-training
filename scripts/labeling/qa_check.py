#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from typing import Dict, List, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp"}


def load_labelmap(path: str) -> Dict[int, str]:
    """
    Accepts either:
      - {'classes': ['drone','vehicle',...]}  (index = class id)
      - {'0': 'drone', '1': 'vehicle', ...}   (string/int keys)
      - {'drone': 0, 'vehicle': 1, ...}       (invert to id->name)
    Returns {id: name}.
    """
    if not path or not os.path.exists(path) or yaml is None:
        # default 5-class template
        return {0: "target", 1: "vehicle", 2: "person", 3: "building", 4: "other"}

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    # classes as list
    if isinstance(data.get("classes"), list):
        return {i: str(n) for i, n in enumerate(data["classes"])}

    # dict forms
    if isinstance(data, dict) and data:
        # id->name (keys numeric or numeric strings)
        try:
            out = {int(k): str(v) for k, v in data.items()}
            return dict(sorted(out.items()))
        except Exception:
            # maybe name->id
            inv = {int(v): str(k) for k, v in data.items()}
            return dict(sorted(inv.items()))

    # fallback
    return {0: "target", 1: "vehicle", 2: "person", 3: "building", 4: "other"}


def list_images(images_dir: str) -> List[str]:
    ims: List[str] = []
    for root, _, files in os.walk(images_dir):
        for fn in files:
            if os.path.splitext(fn)[1].lower() in IMG_EXTS:
                ims.append(os.path.join(root, fn))
    ims.sort()
    return ims


def read_yolo_file(
    label_path: str,
) -> Tuple[List[Tuple[int, float, float, float, float]], List[str]]:
    """Read a YOLO .txt file (one object per line)."""
    objs: List[Tuple[int, float, float, float, float]] = []
    issues: List[str] = []
    with open(label_path, "r") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 5:
                issues.append(f"line {i}: expected 5 fields, got {len(parts)}")
                continue
            try:
                cls = int(parts[0])
                cx, cy, w, h = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
            except Exception:
                issues.append(f"line {i}: parse error (class/coords)")
                continue
            objs.append((cls, cx, cy, w, h))
    return objs, issues


def validate_objects(
    objs: List[Tuple[int, float, float, float, float]],
    class_ids: List[int],
) -> List[str]:
    issues: List[str] = []
    for i, (cls, cx, cy, w, h) in enumerate(objs, 1):
        if cls not in class_ids:
            issues.append(f"line {i}: class {cls} not in {class_ids}")
        for v, name in [(cx, "cx"), (cy, "cy"), (w, "w"), (h, "h")]:
            if not (0.0 <= v <= 1.0):
                issues.append(f"line {i}: {name} {v:.3f} out of [0,1]")
        if w <= 0 or h <= 0:
            issues.append(f"line {i}: non-positive box size w={w:.4f}, h={h:.4f}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description="Quick QA for YOLO labels.")
    ap.add_argument("--images", required=True, help="Images root directory")
    ap.add_argument("--labels", required=True, help="Labels root directory")
    ap.add_argument("--labelmap", default="configs/labeling/labelmap.yaml")
    ap.add_argument("--json-out", default="artifacts/label_qa.json")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)

    labelmap = load_labelmap(args.labelmap)
    class_ids = sorted(labelmap.keys())

    images = list_images(args.images)
    n_images = len(images)

    with_labels = 0
    empty = 0
    class_counts: Counter[int] = Counter()
    file_issues: Dict[str, List[str]] = {}

    for img_path in images:
        stem, _ = os.path.splitext(os.path.basename(img_path))
        label_path = os.path.join(args.labels, f"{stem}.txt")
        if not os.path.exists(label_path):
            file_issues[img_path] = ["missing label file"]
            continue

        with_labels += 1
        objs, parse_issues = read_yolo_file(label_path)
        if not objs:
            empty += 1

        val_issues = validate_objects(objs, class_ids)
        if parse_issues or val_issues:
            file_issues[label_path] = parse_issues + val_issues

        for cls, _, _, _, _ in objs:
            class_counts[cls] += 1

    # Build a string-keyed class count (flake8 prefers deterministic keys)
    class_counts_str: Dict[str, int] = {str(k): int(v) for k, v in sorted(class_counts.items())}

    summary = {
        "images": n_images,
        "with_labels": with_labels,
        "empty_label_files": empty,
        "class_counts": class_counts_str,
        "labelmap": {int(k): v for k, v in labelmap.items()},
        "issues": file_issues,
    }

    with open(args.json_out, "w") as f:
        json.dump(summary, f, indent=2)

    # concise CLI summary
    print(f"[label-qa] images: {n_images}")
    print(f"[label-qa] with labels: {with_labels} | empty: {empty}")
    print(f"[label-qa] class counts: {class_counts_str}")
    if file_issues:
        print(f"[label-qa] issues: {len(file_issues)} files have problems (see {args.json_out})")
    else:
        print("[label-qa] no issues found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
