import math
import sys
from pathlib import Path

# Make "src" imports work in dev without installing the package
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from controllers.lqr.lqr_position import Limits, LQRGains, LQRPos2D  # noqa: E402


def test_zero_error_zero_output():
    ctrl = LQRPos2D(LQRGains(1.5, 2.0, 0.0), limits=Limits(accel_max=3.0))
    ax, ay = ctrl.step(0.02, (1.0, 1.0), (0.0, 0.0), (1.0, 1.0))
    assert abs(ax) < 1e-9 and abs(ay) < 1e-9


def test_step_move_converges_simple_kinematics():
    ctrl = LQRPos2D(LQRGains(2.0, 3.5, 0.1), limits=Limits(accel_max=3.0, i_limit=0.5))
    dt = 0.02
    pos = [0.0, 0.0]
    vel = [0.0, 0.0]
    target = (10.0, 10.0)
    for _ in range(int(5.0 / dt)):
        ax, ay = ctrl.step(dt, tuple(pos), tuple(vel), target)
        vel[0] += ax * dt
        vel[1] += ay * dt
        pos[0] += vel[0] * dt
        pos[1] += vel[1] * dt
    ex = target[0] - pos[0]
    ey = target[1] - pos[1]
    assert math.hypot(ex, ey) < 1.0
