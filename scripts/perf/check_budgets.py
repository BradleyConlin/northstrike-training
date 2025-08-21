#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys

import yaml


def docker_image_size_mb(tag: str) -> float:
    # docker image inspect returns size in bytes
    r = subprocess.run(
        ["docker", "image", "inspect", tag, "--format", "{{.Size}}"], capture_output=True, text=True
    )
    r.check_returncode()
    size_bytes = int(r.stdout.strip())
    return size_bytes / (1024 * 1024)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("perf_json", type=str, help="artifacts/perf.json from profiler")
    ap.add_argument("budgets_yaml", type=str, help="budgets.yaml")
    ap.add_argument("--image", default="northstrike:latest")
    args = ap.parse_args()

    with open(args.perf_json, "r") as f:
        perf = json.load(f)
    with open(args.budgets_yaml, "r") as f:
        budgets = yaml.safe_load(f)

    # 1) image size
    if shutil.which("docker"):
        size_mb = docker_image_size_mb(args.image)
        max_mb = float(budgets["image"]["max_size_mb"])
        print(f"[check] image size: {size_mb:.1f} MB (max {max_mb} MB)")
        if size_mb > max_mb:
            print(f"FAIL: image size {size_mb:.1f} MB > {max_mb} MB")
            sys.exit(1)
    else:
        print("[warn] docker not found; skipping image size check")

    # 2) inference latency budgets
    p50 = float(perf["p50_ms"])
    p95 = float(perf["p95_ms"])
    fps = float(perf["fps"])

    max_p50 = float(budgets["inference_cpu"]["max_p50_ms"])
    max_p95 = float(budgets["inference_cpu"]["max_p95_ms"])
    min_fps = float(budgets["throughput"]["min_fps"])

    ok = True
    print(f"[check] p50: {p50:.2f} ms (max {max_p50:.2f} ms)")
    if p50 > max_p50:
        ok = False
    print(f"[check] p95: {p95:.2f} ms (max {max_p95:.2f} ms)")
    if p95 > max_p95:
        ok = False
    print(f"[check] fps: {fps:.2f} (min {min_fps:.2f})")
    if fps < min_fps:
        ok = False

    if not ok:
        print("FAIL: budgets exceeded.")
        sys.exit(1)

    print("OK: budgets met.")
    sys.exit(0)


if __name__ == "__main__":
    main()
