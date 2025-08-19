import numpy as np

from src.domain.geo import line_of_sight_free, point_in_polygon


def test_geofence_point_in_polygon():
    poly = [(5, 5), (35, 5), (35, 35), (5, 35)]
    assert point_in_polygon((10, 10), poly)
    assert not point_in_polygon((1, 1), poly)


def test_line_of_sight_on_grid():
    grid = np.zeros((40, 40), dtype=int)
    grid[20, 10:30] = 1  # wall at y=20
    assert line_of_sight_free((8, 8), (32, 8), grid)  # above wall -> free
    assert not line_of_sight_free((8, 20), (32, 20), grid)  # through wall -> blocked
