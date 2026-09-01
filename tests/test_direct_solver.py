import numpy as np
import pytest

from opengrow.physics.direct_solver import point_source_irradiance


def test_inverse_square_on_axis():
    near = point_source_irradiance(np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 1.0], 1.0)
    far = point_source_irradiance(np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 2.0], 1.0)
    assert (near / far).item() == pytest.approx(4.0)


def test_radiant_power_linearity():
    grid = np.array([[[0.0, 0.0, 0.0]]])
    one = point_source_irradiance(grid, [0.0, 0.0, 1.0], 1.0)
    two = point_source_irradiance(grid, [0.0, 0.0, 1.0], 2.0)
    assert two == pytest.approx(one * 2.0)
