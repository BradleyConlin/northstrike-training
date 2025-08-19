import random

from sim.ekf_2d import EKF2D, EKFParams


def test_ekf_tracks_constant_accel():
    dt = 0.02
    ekf = EKF2D(dt, EKFParams(q_pos=1e-4, q_vel=1e-3, r_pos=0.25**2))
    ekf.reset()

    # True motion: ax=0.5, ay=-0.2; noisy position measurements
    px = py = vx = vy = 0.0
    ax, ay = 0.5, -0.2
    rng = random.Random(123)

    for k in range(int(5.0 / dt)):
        # propagate truth
        vx += ax * dt
        vy += ay * dt
        px += vx * dt
        py += vy * dt

        zpx = px + rng.gauss(0.0, 0.25)
        zpy = py + rng.gauss(0.0, 0.25)
        ekf_px, ekf_py, _, _ = ekf.step(ax, ay, zpx, zpy)

    err = ((ekf_px - px) ** 2 + (ekf_py - py) ** 2) ** 0.5
    assert err < 0.2
