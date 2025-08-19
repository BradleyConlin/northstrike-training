from control.pid_pos import Limits, PIDGains, PIDPos2D


def test_zero_error_zero_output():
    ctrl = PIDPos2D(PIDGains(1.0, 0.2, 0.3), limits=Limits(accel_max=2.0, i_limit=0.5))
    ax, ay = ctrl.step(
        dt=0.02,
        pos=(1.0, 1.0),
        vel=(0.0, 0.0),
        target_pos=(1.0, 1.0),
        target_vel=(0.0, 0.0),
    )
    assert abs(ax) < 1e-9 and abs(ay) < 1e-9


def test_step_move_converges_simple_kinematics():
    ctrl = PIDPos2D(PIDGains(0.6, 0.02, 0.8), limits=Limits(accel_max=2.0, i_limit=0.8))
    dt = 0.02
    pos = [0.0, 0.0]
    vel = [0.0, 0.0]
    target = (1.0, 1.0)

    for _ in range(int(3.0 / dt)):
        ax, ay = ctrl.step(dt, tuple(pos), tuple(vel), target)
        vel[0] += ax * dt
        vel[1] += ay * dt
        pos[0] += vel[0] * dt
        pos[1] += vel[1] * dt

    ex = target[0] - pos[0]
    ey = target[1] - pos[1]
    assert (ex**2 + ey**2) ** 0.5 < 0.15  # within 15 cm after 3s


def test_anti_windup_integrator_bounded():
    # Small accel limit to force saturation; integrator must stay within i_limit
    lim = Limits(accel_max=0.3, i_limit=0.2)
    ctrl = PIDPos2D(PIDGains(1.0, 0.5, 0.0), limits=lim)
    dt = 0.02
    pos = (0.0, 0.0)
    vel = (0.0, 0.0)
    target = (10.0, 0.0)  # huge error to saturate

    for _ in range(int(5.0 / dt)):
        ctrl.step(dt, pos, vel, target)

    st = ctrl.state()
    assert abs(st["ix"]) <= lim.i_limit + 1e-9
    assert abs(st["iy"]) <= lim.i_limit + 1e-9
