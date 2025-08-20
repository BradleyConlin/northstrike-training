#!/usr/bin/env python3
from __future__ import annotations


def tecs_vertical_speed_cmd(
    alt: float, alt_cmd: float, v: float, kp_alt: float = 0.6, vdot_lim_frac: float = 0.3
) -> float:
    """
    Very small TECS-like vertical speed controller.
    Returns climb-rate command [m/s], limited to +/- (vdot_lim_frac * v).
    """
    vdot_cmd = kp_alt * (alt_cmd - alt)
    limit = max(v * vdot_lim_frac, 1.0)
    if vdot_cmd > limit:
        vdot_cmd = limit
    if vdot_cmd < -limit:
        vdot_cmd = -limit
    return float(vdot_cmd)
