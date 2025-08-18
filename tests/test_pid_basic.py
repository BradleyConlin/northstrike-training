from control.pid import PID, PIDConfig


def test_pid_reduces_step_error():
    # Simple first-order plant: y_{k+1} = y_k + gain * u * dt
    cfg = PIDConfig(
        kp=1.2, ki=0.8, kd=0.05, output_limits=(-2, 2), i_limits=(-1, 1), d_alpha=0.2
    )
    pid = PID(cfg)

    y = 0.0
    target = 1.0
    dt = 0.02
    plant_gain = 0.8
    history = []
    for _ in range(500):
        err = target - y
        u = pid.step(err, dt)
        y = y + plant_gain * u * dt
        history.append(abs(err))

    # Error should drop and stay small
    assert history[0] > history[-1]
    assert abs(target - y) < 0.05


def test_pid_anti_windup_under_saturation():
    cfg = PIDConfig(
        kp=5.0, ki=2.0, kd=0.0, output_limits=(-0.2, 0.2), i_limits=(-0.3, 0.3)
    )
    pid = PID(cfg)
    dt = 0.01
    # Large persistent error forces saturation; integral must stay bounded
    for _ in range(1000):
        _ = pid.step(err=10.0, dt=dt)
    assert -0.31 < pid.i < 0.31
