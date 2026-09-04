import numpy as np
import pytest

from opengrow.physics.direct_solver import (
    manufacturer_ies_irradiance,
    point_source_irradiance,
    sensor_grid,
    simulate_design,
)
from opengrow.physics.photometry import AngularDistribution
from opengrow.physics.spectrum import parse_spectrum_text


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


def test_occluder_creates_partial_shadow_and_diagnostics():
    design = {
        "grid": {"width_m": 1.0, "depth_m": 0.1, "nx": 3, "ny": 1},
        "channels": [{"id": "red", "wavelength_nm": 660, "emitters": [{
            "source_path": "/Red", "position_m": [0, 0, 1], "direction": [0, 0, -1],
            "radiant_power_w": 1, "beam_exponent": 1,
        }]}],
        "occluders": [{
            "shape": "box", "enabled": True, "center_m": [0, 0, 0.5],
            "axes": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "half_extents_m": [0.1, 0.1, 0.1],
        }],
    }
    result = simulate_design(design)
    assert result["emitter_visibility"].tolist() == [[[True, False, True]]]
    assert result["blocked_ray_count"] == 1
    assert result["total_ray_count"] == 3
    assert result["occlusion_diagnostics"][0]["source_path"] == "/Red"


def _uniform_sphere_distribution():
    return AngularDistribution(
        vertical_angles_deg=np.array([0.0, 90.0, 180.0]),
        horizontal_angles_deg=np.array([0.0, 180.0, 360.0]),
        intensity=np.ones((3, 3), dtype=float),
    )


def test_manufacturer_ies_uses_full_orientation_and_inverse_square():
    profile = _uniform_sphere_distribution()
    orientation = np.eye(3)
    near = manufacturer_ies_irradiance(
        np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 1.0], 2.0, profile, orientation
    )
    far = manufacturer_ies_irradiance(
        np.array([[[0.0, 0.0, 0.0]]]), [0.0, 0.0, 2.0], 2.0, profile, orientation
    )
    assert near.item() > 0.0
    assert (near / far).item() == pytest.approx(4.0)


def test_manufacturer_ies_rejects_non_orthonormal_orientation():
    profile = _uniform_sphere_distribution()
    grid = np.array([[[0.0, 0.0, 0.0]]])
    with pytest.raises(ValueError, match="orthonormal"):
        manufacturer_ies_irradiance(
            grid, [0.0, 0.0, 1.0], 1.0, profile,
            [[1, 0, 0], [0, 2, 0], [0, 0, 1]],
        )


def test_tabulated_spd_drives_par_and_far_red_metrics():
    spectrum = parse_spectrum_text("680 1\n700 1\n720 1\n740 1\n760 1\n")
    design = {
        "grid": {"width_m": 0.1, "depth_m": 0.1, "nx": 1, "ny": 1},
        "channels": [{
            "id": "red",
            "wavelength_nm": 700,
            "spectrum": spectrum,
            "emitters": [{
                "position_m": [0, 0, 1],
                "direction": [0, 0, -1],
                "radiant_power_w": 1.0,
                "beam_exponent": 1.0,
            }],
        }],
        "occluders": [],
    }
    result = simulate_design(design)
    assert result["ppfd"].item() > 0.0
    assert result["far_red"].item() > 0.0
    assert result["far_red_band_nm"] == [700.0, 750.0]


def test_manufacturer_ies_path_works_inside_simulate_design():
    profile = _uniform_sphere_distribution()
    design = {
        "grid": {"width_m": 0.1, "depth_m": 0.1, "nx": 1, "ny": 1},
        "channels": [{
            "id": "blue",
            "wavelength_nm": 450,
            "emitters": [{
                "position_m": [0, 0, 1],
                "radiant_power_w": 1.0,
                "angular_model": "manufacturer_ies",
                "angular_distribution": profile,
                "orientation_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            }],
        }],
        "occluders": [],
    }
    result = simulate_design(design)
    assert result["ppfd"].item() > 0.0
