#!/usr/bin/env python3
from __future__ import annotations

import math
from typing import Tuple

Vec2 = Tuple[float, float]


def _norm2(v: Vec2) -> float:
    return math.hypot(v[0], v[1])


def _unit(v: Vec2) -> Vec2:
    n = _norm2(v)
    return (v[0] / n, v[1] / n) if n > 1e-6 else (1.0, 0.0)


def _dot(a: Vec2, b: Vec2) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _wrap_pi(a: float) -> float:
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


def l1_lateral_accel(
    pos: Vec2,
    vel: Vec2,
    wp_prev: Vec2,
    wp_next: Vec2,
    L1_period: float = 12.0,
    damping: float = 0.75,
    a_max: float = 15.0,
) -> float:
    """
    True L1-style guidance:
      1) project 'pos' to the current leg (wp_prev->wp_next) to get closest point C
      2) choose lookahead point P = C + t_hat * L1_dist (clamped to the leg)
      3) command lateral accel to align velocity heading toward P
    Returns ay [m/s^2] (positive = turn left).
    """
    V = max(_norm2(vel), 1.0)
    # classical L1 distance
    L1_dist = max(V * L1_period / (2.0 * math.pi), 5.0)

    # leg vector + unit tangent
    t_vec = (wp_next[0] - wp_prev[0], wp_next[1] - wp_prev[1])
    L = _norm2(t_vec)
    if L < 1e-6:
        # degenerate leg: just point at wp_next
        t_hat = (1.0, 0.0)
        P = wp_next
    else:
        t_hat = (t_vec[0] / L, t_vec[1] / L)
        # projection of pos onto the infinite line, then clamp to segment
        w = (pos[0] - wp_prev[0], pos[1] - wp_prev[1])
        s = max(0.0, min(L, _dot(w, t_hat)))
        # closest point on the segment
        # lookahead point along the segment
        sP = min(L, s + L1_dist)
        P = (wp_prev[0] + t_hat[0] * sP, wp_prev[1] + t_hat[1] * sP)

    # desired bearing to lookahead point
    psi_des = math.atan2(P[1] - pos[1], P[0] - pos[0])
    psi = math.atan2(vel[1], vel[0])
    eta = _wrap_pi(psi_des - psi)

    # L1 normal-accel command
    k = 2.0 * damping
    a_cmd = (V * V / max(L1_dist, 1.0)) * (k * math.sin(eta))

    # clamp
    if a_cmd > a_max:
        a_cmd = a_max
    if a_cmd < -a_max:
        a_cmd = -a_max
    return a_cmd
