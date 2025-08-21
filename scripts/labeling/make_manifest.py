#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def find_images(images_dir: Path) -> List[Path]:
    imgs: List[Path] = []
    for p in sorted(images_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            imgs.append(p)
    return imgs


def label_path_for(image_path: Path, labels_dir: Path) -> Path:
    return labels_dir / image_path.with_suffix(".txt").name


def parse_yolo_label_file(txt_path: Path) -> List[Tuple[int, float, float, float, float]]:
    """
    Returns list of (cls, cx, cy, w, h) floats.
    Ignores empty/invalid lines.
    """
    out: List[Tuple[int, float, float, float, float]] = []
    if not txt_path.exists():
        return out
    for line in txt_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            cls = int(parts[0])
            cx, cy, w, h = map(float, parts[1:5])
        except ValueError:
            continue
        out.append((cls, cx, cy, w, h))
    return out


def deterministic_split(key: str, p_train: float, p_val: float) -> str:
    """Map a string key to 'train' | 'val' | 'test' deterministically via md5."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    r = (h % 10_000) / 10_000.0  # [0,1)
    if r < p_train:
        return "train"
    if r < p_train + p_val:
        return "val"
    return "test"


def load_labelmap(path: Path) -> Dict[int, str]:
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    # Accept either {'names': ['foo','bar']} or {0:'foo',1:'bar'} or {'0':'foo',...}
    if isinstance(data, dict) and "names" in data and isinstance(data["names"], list):
        return {i: str(n) for i, n in enumerate(data["names"])}
    out: Dict[int, str] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            try:
                ki = int(k)
                out[ki] = str(v)
            except Exception:
                continue
    return out


def write_dataset_yaml(
    out_yaml: Path,
    splits_dir: Path,
    class_names: Dict[int, str],
) -> None:
    names_list = [class_names[i] for i in sorted(class_names.keys())] if class_names else []
    payload = {
        "path": ".",  # keep relative
        "train": str((splits_dir / "train.txt").as_posix()),
        "val": str((splits_dir / "val.txt").as_posix()),
        "test": str((splits_dir / "test.txt").as_posix()),
        "nc": len(names_list),
        "names": names_list,
    }
    out_yaml.parent.mkdir(parents=True, exist_ok=True)
    with out_yaml.open("w") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def make_manifest(
    images_dir: Path,
    labels_dir: Path,
    labelmap_path: Path,
    out_yaml: Path,
    splits_dir: Path,
    stats_json: Path | None,
    p_train: float,
    p_val: float,
) -> None:
    assert (
        0.0 < p_train < 1.0 and 0.0 <= p_val < 1.0 and p_train + p_val < 1.0
    ), "Invalid split ratios"
    p_test = 1.0 - (p_train + p_val)

    images = find_images(images_dir)
    class_counts: Counter[int] = Counter()
    per_split: Dict[str, List[Path]] = {"train": [], "val": [], "test": []}
    labeled_count = 0

    for img in images:
        lbl = label_path_for(img, labels_dir)
        anns = parse_yolo_label_file(lbl)
        if anns:
            labeled_count += 1
            for cls, *_ in anns:
                class_counts[cls] += 1
        # Split by image stem (stable)
        split = deterministic_split(img.stem, p_train, p_val)
        per_split[split].append(img)

    # Write split files as absolute or repo-relative paths (use POSIX style)
    splits_dir.mkdir(parents=True, exist_ok=True)
    for name, items in per_split.items():
        with (splits_dir / f"{name}.txt").open("w") as f:
            for p in items:
                f.write(p.as_posix() + "\n")

    # Dataset YAML
    class_names = load_labelmap(labelmap_path)
    write_dataset_yaml(out_yaml, splits_dir, class_names)

    # Stats
    n_images = len(images)
    n_empty = n_images - labeled_count
    n_train = len(per_split["train"])
    n_val = len(per_split["val"])
    n_test = len(per_split["test"])  # keep and report to satisfy flake8

    stats_payload = {
        "images": n_images,
        "labeled": labeled_count,
        "empty": n_empty,
        "class_counts": dict(sorted(class_counts.items())),
        "splits": {"train": n_train, "val": n_val, "test": n_test},
        "ratios": {"train": p_train, "val": p_val, "test": p_test},
    }
    if stats_json is not None:
        stats_json.parent.mkdir(parents=True, exist_ok=True)
        stats_json.write_text(json.dumps(stats_payload, indent=2))
    print(f"[manifest] wrote {out_yaml}")
    print(f"[splits]   train/val/test: {n_train}/{n_val}/{n_test}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Create YOLO dataset.yaml + splits from images/labels")
    ap.add_argument("--images", required=True, type=Path)
    ap.add_argument("--labels", required=True, type=Path)
    ap.add_argument("--labelmap", required=True, type=Path)
    ap.add_argument("--out-yaml", required=True, type=Path)
    ap.add_argument("--splits-dir", required=True, type=Path)
    ap.add_argument("--stats-json", type=Path, default=None)
    ap.add_argument("--train", type=float, default=0.8)
    ap.add_argument("--val", type=float, default=0.1)
    args = ap.parse_args()

    make_manifest(
        images_dir=args.images,
        labels_dir=args.labels,
        labelmap_path=args.labelmap,
        out_yaml=args.out_yaml,
        splits_dir=args.splits_dir,
        stats_json=args.stats_json,
        p_train=args.train,
        p_val=args.val,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
