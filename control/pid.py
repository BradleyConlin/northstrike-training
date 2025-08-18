from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class PIDConfig:
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    output_limits: Optional[Tuple[float, float]] = (-1.0, 1.0)
    i_limits: Optional[Tuple[float, float]] = (-0.5, 0.5)
    d_alpha: float = 0.0  # 0=no filter, 0.1..0.9 exponential smoothing


class PID:
    def __init__(self, cfg: PIDConfig):
        self.cfg = cfg
        self.i = 0.0
        self.prev_err: Optional[float] = None
        self.d_filt = 0.0

    def reset(self) -> None:
        self.i = 0.0
        self.prev_err = None
        self.d_filt = 0.0

    def step(self, err: float, dt: float) -> float:
        # Integral
        self.i += err * dt
        if self.cfg.i_limits:
            lo, hi = self.cfg.i_limits
            self.i = max(lo, min(hi, self.i))

        # Derivative (with optional low-pass on d term)
        d = 0.0 if self.prev_err is None or dt <= 0 else (err - self.prev_err) / dt
        if self.cfg.d_alpha:
            a = self.cfg.d_alpha
            self.d_filt = a * self.d_filt + (1 - a) * d
            d_term = self.d_filt
        else:
            d_term = d

        # PID sum
        u = self.cfg.kp * err + self.cfg.ki * self.i + self.cfg.kd * d_term

        # Output clamp + basic anti-windup via integral clamp already applied
        if self.cfg.output_limits:
            lo, hi = self.cfg.output_limits
            u = max(lo, min(hi, u))

        self.prev_err = err
        return u
