import numpy as np
import pytest

from opengrow.physics.direct_solver import point_source_irradiance, sensor_grid


def test_inverse_square_on_axis():
    near = point_source_irradiance(np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 1.0], 1.0)
    far = point_source_irradiance(np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 2.0], 1.0)
    assert (near / far).item() == pytest.approx(4.0)


def test_radiant_power_linearity():
    grid = np.array([[[0.0, 0.0, 0.0]]])
    one = point_source_irradiance(grid, [0.0, 0.0, 1.0], 1.0)
    two = point_source_irradiance(grid, [0.0, 0.0, 1.0], 2.0)
    assert two == pytest.approx(one * 2.0)


def test_emitter_direction_changes_received_irradiance():
    grid = np.array([[[0.0, 0.0, 0.0]]])
    downward = point_source_irradiance(grid, [0.0, 0.0, 1.0], 1.0, direction=[0, 0, -1])
    sideways = point_source_irradiance(grid, [0.0, 0.0, 1.0], 1.0, direction=[1, 0, 0])
    assert downward.item() > 0
    assert sideways.item() == 0


def test_sensor_grid_supports_world_center_and_orientation():
    grid = sensor_grid(2.0, 1.0, 3, 2, center_m=[4, 5, 6], u_axis=[0, 1, 0], v_axis=[-1, 0, 0])
    assert grid.shape == (2, 3, 3)
    assert grid.mean(axis=(0, 1)) == pytest.approx([4, 5, 6])
