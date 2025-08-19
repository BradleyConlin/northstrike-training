from planners.rrt import plan_on_grid_rrt


def test_rrt_finds_path_on_free_grid_deterministic():
    w, h = 30, 30
    grid = [[0 for _ in range(w)] for _ in range(h)]
    path = plan_on_grid_rrt(grid, (0, 0), (29, 29), seed=123, simplify=True)
    assert path[0] == (0, 0) and path[-1] == (29, 29)
    # shouldn't be absurdly long
    assert len(path) <= 90
