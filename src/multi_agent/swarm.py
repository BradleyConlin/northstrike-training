#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

Vec2 = Tuple[float, float]


@dataclass
class Agent:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0


def _clip(v: np.ndarray, vmax: float) -> np.ndarray:
    n = np.linalg.norm(v)
    return v if n <= vmax or n == 0 else v * (vmax / n)


def simulate_swarm(
    n_agents: int,
    offsets: List[Vec2],
    waypoints: List[Vec2],
    dt: float = 0.05,
    steps: int = 400,
    vmax: float = 2.0,
    kp_leader: float = 0.8,
    kp_form: float = 0.8,
    r_avoid: float = 0.7,
    k_avoid: float = 0.6,
) -> np.ndarray:
    """
    Simple 2D single-integrator swarm.
    - agent 0 = leader, tracks waypoints sequentially.
    - followers i>0 track leader + offsets[i-1].
    - pairwise repulsion for separation (barrier-style near collisions).
    Returns: trace [steps, n_agents, 2]
    """
    assert n_agents >= 1
    assert len(offsets) >= max(0, n_agents - 1)

    agents = [Agent(x=0.0, y=0.0)] + [Agent(x=off[0], y=off[1]) for off in offsets[: n_agents - 1]]
    trace = np.zeros((steps, n_agents, 2), dtype=float)
    wp_idx = 0
    eps = 1e-6
    r_safe = 0.35  # soft safety radius for final check

    for k in range(steps):
        # leader to waypoint
        leader = agents[0]
        if wp_idx < len(waypoints):
            gx, gy = waypoints[wp_idx]
            d = np.array([gx - leader.x, gy - leader.y], dtype=float)
            if np.linalg.norm(d) < 0.5 and wp_idx < len(waypoints) - 1:
                wp_idx += 1
                gx, gy = waypoints[wp_idx]
                d = np.array([gx - leader.x, gy - leader.y], dtype=float)
            v_lead = _clip(kp_leader * d, vmax)
        else:
            v_lead = np.zeros(2)
        leader.vx, leader.vy = float(v_lead[0]), float(v_lead[1])

        # followers: formation + barrier repulsion
        for i in range(1, n_agents):
            ag = agents[i]
            ox, oy = offsets[i - 1]
            des = np.array([leader.x + ox - ag.x, leader.y + oy - ag.y], dtype=float)
            v = kp_form * des

            rep = np.zeros(2, dtype=float)
            for j in range(n_agents):
                if j == i:
                    continue
                other = agents[j]
                diff = np.array([ag.x - other.x, ag.y - other.y], dtype=float)
                dist = float(np.linalg.norm(diff))
                if 0.0 < dist < r_avoid:
                    # barrier-style strength: grows rapidly as dist -> 0
                    strength = k_avoid * max(0.0, (r_avoid / (dist + eps) - 1.0))
                    rep += (diff / (dist + eps)) * strength

            v = _clip(v + rep, vmax)

            # soft safety: if too close to anyone and still closing, push directly away
            for j in range(n_agents):
                if j == i:
                    continue
                other = agents[j]
                diff = np.array([ag.x - other.x, ag.y - other.y], dtype=float)
                dist = float(np.linalg.norm(diff))
                if 0.0 < dist < r_safe:
                    push = (diff / (dist + eps)) * (k_avoid * (r_safe - dist) / (dist + eps))
                    v = _clip(v + push, vmax)

            ag.vx, ag.vy = float(v[0]), float(v[1])

        # integrate
        for i, ag in enumerate(agents):
            ag.x += ag.vx * dt
            ag.y += ag.vy * dt
            trace[k, i, 0] = ag.x
            trace[k, i, 1] = ag.y

    return trace


def min_pairwise_distance(trace: np.ndarray) -> float:
    s, n, _ = trace.shape
    m = float("inf")
    for k in range(s):
        P = trace[k]
        for i in range(n):
            for j in range(i + 1, n):
                d = float(np.hypot(P[i, 0] - P[j, 0], P[i, 1] - P[j, 1]))
                if d < m:
                    m = d
    return 0.0 if m == float("inf") else m


def auction_assign(agents_xy: List[Vec2], goals_xy: List[Vec2]) -> List[Tuple[int, int]]:
    """Greedy market-based assignment: iteratively match closest (agent, goal)."""
    A = list(range(len(agents_xy)))
    G = list(range(len(goals_xy)))
    pairs: List[Tuple[int, int]] = []
    while A and G:
        best = None
        best_cost = 1e18
        for i in A:
            ax, ay = agents_xy[i]
            for j in G:
                gx, gy = goals_xy[j]
                c = (ax - gx) ** 2 + (ay - gy) ** 2
                if c < best_cost:
                    best_cost = c
                    best = (i, j)
        i, j = best  # type: ignore
        pairs.append((i, j))
        A.remove(i)
        G.remove(j)
    return pairs
