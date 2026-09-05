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


def _asymmetric_type_c_distribution():
    """Synthetic full-azimuth Type-C profile with a strong C=0 (+X) lobe."""
    vertical = np.array([0.0, 45.0, 90.0, 135.0, 180.0])
    horizontal = np.array([0.0, 90.0, 180.0, 270.0, 360.0])
    theta_shape = np.array([1.0, 1.0, 0.8, 0.2, 0.05])
    azimuth_scale = np.array([4.0, 1.0, 0.5, 1.0, 4.0])
    intensity = azimuth_scale[:, None] * theta_shape[None, :]
    return AngularDistribution(vertical, horizontal, intensity)


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


def test_manufacturer_ies_azimuth_follows_emitter_orientation():
    """A +90 degree local-Z rotation must rotate the Type-C C=0 lobe +X -> +Y."""
    profile = _asymmetric_type_c_distribution()
    emitter = [0.0, 0.0, 1.0]
    points = np.array([[[0.5, 0.0, 0.0], [0.0, 0.5, 0.0]]])

    identity = np.eye(3)
    rotate_z_90 = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])

    field_0 = manufacturer_ies_irradiance(points, emitter, 1.0, profile, identity)
    field_90 = manufacturer_ies_irradiance(points, emitter, 1.0, profile, rotate_z_90)

    # Identity: C=0 is local +X, so the +X sample sees the strong lobe.
    assert field_0[0, 0] > field_0[0, 1]
    # After +90 degrees about local/world Z, local +X maps to world +Y.
    assert field_90[0, 1] > field_90[0, 0]
    # Equal-radius samples verify that the angular field itself rotated, rather than
    # a distance/incidence change creating the result.
    assert field_90[0, 1] == pytest.approx(field_0[0, 0], rel=1e-12, abs=1e-12)
    assert field_90[0, 0] == pytest.approx(field_0[0, 1], rel=1e-12, abs=1e-12)


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
