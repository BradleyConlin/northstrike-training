from sim.quad_2d import Quad2D, QuadParams


def test_constant_accel_no_drag_matches_kinematics():
    dt, T = 0.01, 1.0
    steps = int(T / dt)
    q = Quad2D(QuadParams(drag=0.0, accel_max=10.0))
    for _ in range(steps):
        q.step(dt, 1.0, 0.0)  # 1 m/s^2 in x
    px, py, vx, vy = q.state()
    # x = 0.5 a t^2 ; v = a t
    assert abs(px - 0.5 * 1.0 * T * T) < 1e-2
    assert abs(vx - 1.0 * T) < 1e-2
    assert abs(py) < 1e-9 and abs(vy) < 1e-9


def test_drag_reduces_velocity_magnitude():
    q = Quad2D(QuadParams(drag=1.0, accel_max=10.0))
    q.reset(vx=1.0, vy=0.0)
    q.step(0.1, 0.0, 0.0)  # no input; drag only
    _, _, vx, _ = q.state()
    assert vx < 1.0  # should decay


def test_saturation_limits_accel_effect():
    dt = 0.1
    q = Quad2D(QuadParams(drag=0.0, accel_max=0.5))
    q.step(dt, 2.0, 0.0)  # command beyond limit
    _, _, vx, _ = q.state()
    assert vx <= 0.5 * dt + 1e-9
