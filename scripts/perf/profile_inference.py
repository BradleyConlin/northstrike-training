#!/usr/bin/env python3
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn


# Tiny CNN to simulate vision inference
class TinyCNN(nn.Module):
    def __init__(self, in_ch=3, out_dim=1000):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, 32, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.fc = nn.Linear(64, out_dim)

    def forward(self, x):
        x = self.net(x)
        x = x.flatten(1)
        return self.fc(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height", type=int, default=224)
    ap.add_argument("--width", type=int, default=224)
    ap.add_argument("--warmup", type=int, default=20)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--save-json", type=str, default="artifacts/perf.json")
    args = ap.parse_args()

    device = torch.device("cpu")
    model = TinyCNN().to(device).eval()

    x = torch.randn(args.batch, 3, args.height, args.width, device=device)

    # Warmup
    with torch.inference_mode():
        for _ in range(args.warmup):
            _ = model(x)

    times_ms = []
    with torch.inference_mode():
        for _ in range(args.iters):
            t0 = time.perf_counter()
            _ = model(x)
            t1 = time.perf_counter()
            times_ms.append((t1 - t0) * 1000.0)

    p50 = statistics.median(times_ms)
    p95 = np.percentile(times_ms, 95)
    fps = 1000.0 / p50 if p50 > 0 else float("inf")

    out = {
        "p50_ms": float(p50),
        "p95_ms": float(p95),
        "fps": float(fps),
        "iters": args.iters,
        "batch": args.batch,
        "shape": [args.batch, 3, args.height, args.width],
        "device": str(device),
    }

    Path("artifacts").mkdir(parents=True, exist_ok=True)
    with open(args.save_json, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
