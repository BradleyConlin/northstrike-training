from planning.base import Point, plan


def test_straight_line_includes_goal_and_monotonic_progress():
    s = Point(0, 0, 0)
    g = Point(10, 0, 0)
    pts = plan(s, g, step=1.5)
    assert pts[0] == s
    assert pts[-1] == g
    # Monotonic x increase
    xs = [p.x for p in pts]
    assert all(xs[i] <= xs[i + 1] for i in range(len(xs) - 1))
    # Reasonable number of points
    assert 5 <= len(pts) <= 20


def test_zero_distance_returns_start_goal():
    s = Point(1, 2, 3)
    g = Point(1, 2, 3)
    pts = plan(s, g)
    assert pts[0] == s and pts[-1] == g and len(pts) == 2
