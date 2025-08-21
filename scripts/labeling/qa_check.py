#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


def read_labelmap(path: Path) -> Dict[str, int]:
    # supports simple YAML or plain text (one class per line)
    name_to_id: Dict[str, int] = {}
    if not path.exists():
        return name_to_id
    txt = path.read_text().strip()
    if not txt:
        return name_to_id
    if ":" in txt:
        # very small YAML parser (key: value per line)
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                name_to_id[k.strip()] = int(v.strip())
    else:
        # plain list, assign incremental ids
        for i, line in enumerate([line.strip() for line in txt.splitlines() if line.strip()]):
            name_to_id[line] = i
    return name_to_id


def parse_yolo_label_file(p: Path) -> List[Tuple[int, float, float, float, float]]:
    out = []
    if not p.exists():
        return out
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split()
        if len(parts) != 5:
            continue
        try:
            cls = int(parts[0])
            cx, cy, w, h = map(float, parts[1:])
            out.append((cls, cx, cy, w, h))
        except Exception:
            continue
    return out


def run_qa(images_dir: Path, labels_dir: Path, labelmap_path: Path) -> Dict:
    images = sorted(
        [p for p in images_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    )
    labels = {p.stem: p for p in labels_dir.glob("*.txt")}
    lm = read_labelmap(labelmap_path)
    known_ids = set(lm.values())

    n_imgs = len(images)
    n_with = 0
    n_empty = 0
    class_counts: Dict[str, int] = {}
    issues: List[str] = []

    for img in images:
        lab = labels.get(img.stem)
        if not lab or not lab.exists():
            n_empty += 1
            continue
        ann = parse_yolo_label_file(lab)
        if not ann:
            n_empty += 1
            continue
        n_with += 1
        for cls, _, _, _, _ in ann:
            if lm:
                if cls not in known_ids:
                    issues.append(f"unknown_class_id:{cls} in {lab.name}")
            class_counts[str(cls)] = class_counts.get(str(cls), 0) + 1

    # Basic geometry sanity (optional): centers & sizes in 0..1
    for lab in labels.values():
        if not lab.exists():
            continue
        for cls, cx, cy, w, h in parse_yolo_label_file(lab):
            if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                issues.append(f"bad_box:{lab.name}")

    ok = len(issues) == 0

    return {
        "ok": ok,  # <-- this is what the report likely expects
        "images": n_imgs,
        "with_labels": n_with,
        "empty": n_empty,
        "class_counts": class_counts,
        "issues": issues,
        "labelmap_present": lm != {},
    }


def main():
    ap = argparse.ArgumentParser(description="Simple YOLO dataset QA")
    ap.add_argument("--images", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--labelmap", required=True)
    ap.add_argument("--json-out", default="artifacts/label_qa.json")
    args = ap.parse_args()

    img_dir = Path(args.images)
    lab_dir = Path(args.labels)
    lm_path = Path(args.labelmap)
    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    res = run_qa(img_dir, lab_dir, lm_path)

    # human-readable summary
    print(f"[label-qa] images: {res['images']}")
    print(f"[label-qa] with labels: {res['with_labels']} | empty: {res['empty']}")
    print(f"[label-qa] class counts: {res['class_counts']}")
    if res["ok"]:
        print("[label-qa] no issues found")
    else:
        print(f"[label-qa] issues: {len(res['issues'])} -> {res['issues'][:10]}")

    out_path.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
