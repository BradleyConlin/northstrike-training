from planners.astar import plan_on_grid


def test_astar_finds_path_around_wall():
    # 6x6 grid with a wall blocking the middle row (except a gap)
    w, h = 6, 6
    grid = [[0 for _ in range(w)] for _ in range(h)]
    for x in range(1, 5):
        grid[3][x] = 1
    grid[3][3] = 0  # small gap

    path = plan_on_grid(grid, (0, 0), (5, 5))
    assert path[0] == (0, 0)
    assert path[-1] == (5, 5)
    # Path should only move in 4-connected steps and never hit obstacles
    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        assert abs(x1 - x2) + abs(y1 - y2) == 1
        assert grid[y2][x2] == 0


def test_invalid_inputs():
    grid = [[0, 0], [0, 0]]
    # start out of bounds
    try:
        plan_on_grid(grid, (-1, 0), (1, 1))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_astar_diagonal_and_simplify_shorter():
    w, h = 10, 10
    grid = [[0 for _ in range(w)] for _ in range(h)]
    from planners.astar import plan_on_grid

    p4 = plan_on_grid(grid, (0, 0), (9, 9), allow_diag=False, simplify=False)
    p8 = plan_on_grid(grid, (0, 0), (9, 9), allow_diag=True, simplify=True)
    assert len(p8) <= len(p4)
