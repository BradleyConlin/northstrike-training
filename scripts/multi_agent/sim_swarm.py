#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

from src.multi_agent.swarm import min_pairwise_distance, simulate_swarm

OUTDIR = Path("artifacts/swarm")
OUTDIR.mkdir(parents=True, exist_ok=True)


def main():
    offsets = [(1.5, 0.0), (-1.5, 0.0), (0.0, 1.5), (0.0, -1.5)]
    waypoints = [(6.0, 0.0), (6.0, 6.0), (0.0, 6.0), (0.0, 0.0)]
    trace = simulate_swarm(
        n_agents=5,
        offsets=offsets,
        waypoints=waypoints,
        dt=0.05,
        steps=400,
        vmax=2.0,
        kp_leader=0.9,
        kp_form=0.9,
        r_avoid=0.8,
        k_avoid=0.7,
    )
    # write CSV
    with (OUTDIR / "swarm_trace.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "agent", "x", "y"])
        for k in range(trace.shape[0]):
            t = k * 0.05
            for i in range(trace.shape[1]):
                w.writerow([t, i, trace[k, i, 0], trace[k, i, 1]])

    # plot
    plt.figure()
    for i in range(trace.shape[1]):
        plt.plot(trace[:, i, 0], trace[:, i, 1], label=f"a{i}")
        plt.scatter(trace[0, i, 0], trace[0, i, 1], s=10)
    plt.axis("equal")
    plt.legend(ncol=3, fontsize=8)
    plt.title("Swarm formation + avoidance")
    plt.tight_layout()
    plt.savefig(OUTDIR / "swarm_plot.png", dpi=120)

    mind = min_pairwise_distance(trace)
    print(f"min_pairwise_distance={mind:.2f} m")
    print(f"Wrote: {OUTDIR/'swarm_trace.csv'} and {OUTDIR/'swarm_plot.png'}")


if __name__ == "__main__":
    main()
