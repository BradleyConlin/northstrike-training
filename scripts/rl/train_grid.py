#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from src.rl.gridworld import GridWorld, GWCfg, shortest_path_len

OUT = Path("artifacts/rl")
OUT.mkdir(parents=True, exist_ok=True)


def run_train(episodes=400, eps=0.2, gamma=0.98, alpha=0.6, seed=7):
    cfg = GWCfg(
        w=8,
        h=6,
        start=(0, 0),
        goal=(7, 5),
        obstacles={(3, 1), (3, 2), (3, 3), (3, 4)},
        hazards={(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)},  # risky corridor
    )
    env = GridWorld(cfg, seed=seed)
    nS = cfg.w * cfg.h
    nA = 4

    def s_idx(p):
        return p[1] * cfg.w + p[0]

    Q = np.zeros((nS, nA), dtype=float)
    rng = np.random.default_rng(seed)
    metrics = {"episodes": episodes, "unsafe_steps": 0, "successes": 0}

    # train
    for ep in range(episodes):
        s = s_idx(env.reset(seed + ep))
        done = False
        while not done:
            if rng.random() < eps:
                a = rng.integers(0, nA)
            else:
                a = int(np.argmax(Q[s]))
            nxt, r, done, info = env.step(a)
            s2 = s_idx(nxt)
            metrics["unsafe_steps"] += int(bool(info.get("unsafe", False)))
            # Q-learning update
            Q[s, a] = (1 - alpha) * Q[s, a] + alpha * (r + gamma * (0.0 if done else np.max(Q[s2])))
            s = s2
        if env.pos == cfg.goal:
            metrics["successes"] += 1

    # greedy eval
    traj = []
    s = s_idx(env.reset(123))
    done = False
    steps = 0
    unsafe_eval = 0
    while not done and steps < 200:
        a = int(np.argmax(Q[s]))
        nxt, r, done, info = env.step(a)
        traj.append((env.pos[0], env.pos[1], r, int(bool(info.get("unsafe", False)))))
        unsafe_eval += int(bool(info.get("unsafe", False)))
        s = s_idx(nxt)
        steps += 1

    # save artifacts
    (OUT / "policy_q.npy").write_bytes(Q.tobytes())
    with (OUT / "eval_traj.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "r", "unsafe"])
        w.writerows(traj)
    opt = shortest_path_len(cfg.w, cfg.h, cfg.start, cfg.goal, cfg.obstacles)
    summary = {
        "episodes": episodes,
        "train_success_rate": metrics["successes"] / episodes,
        "train_unsafe_steps": metrics["unsafe_steps"],
        "eval_steps": steps,
        "eval_unsafe_steps": unsafe_eval,
        "optimal_steps": int(opt),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print("Wrote:", OUT / "policy_q.npy", OUT / "eval_traj.csv", OUT / "summary.json")
    print("Summary:", json.dumps(summary))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--eps", type=float, default=0.2)
    ap.add_argument("--gamma", type=float, default=0.98)
    ap.add_argument("--alpha", type=float, default=0.6)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    run_train(args.episodes, args.eps, args.gamma, args.alpha, args.seed)
