import copy

import numpy as np

from opengrow.physics.direct_solver import simulate_design
from opengrow.physics.photometry import AngularDistribution
from opengrow.physics.spectrum import parse_spectrum_text


def _synthetic_batwing_profile():
    """Open synthetic Type-C profile with off-axis energy redistribution."""
    vertical = np.array([0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0])
    horizontal = np.array([0.0, 90.0, 180.0, 270.0, 360.0])
    # Deliberately weak on axis and strongest near 60 degrees. The same shape
    # is used in every C-plane so this regression isolates polar redistribution.
    theta_shape = np.array([0.25, 0.8, 1.6, 0.4, 0.08, 0.02, 0.01])
    intensity = np.tile(theta_shape, (horizontal.size, 1))
    return AngularDistribution(vertical, horizontal, intensity)


def _base_design():
    spectrum = parse_spectrum_text(
        "440 0.20\n446 1.00\n452 0.35\n660 0.10\n680 0.80\n700 0.10\n"
    )
    return {
        "grid": {"width_m": 1.0, "depth_m": 0.6, "nx": 11, "ny": 7},
        "channels": [
            {
                "id": "blue",
                "wavelength_nm": 450.0,
                "spectrum": spectrum,
                "emitters": [
                    {
                        "source_path": "/Blue_01",
                        "position_m": [0.0, 0.0, 0.6],
                        "direction": [0.0, 0.0, -1.0],
                        "radiant_power_w": 2.0,
                        "beam_exponent": 1.0,
                    }
                ],
            }
        ],
        "occluders": [],
    }


def test_angular_model_only_ab_is_deterministic_and_material():
    """Changing only the angular model must reproducibly change the canopy field."""
    lambertian_design = _base_design()
    manufacturer_design = copy.deepcopy(lambertian_design)

    emitter = manufacturer_design["channels"][0]["emitters"][0]
    emitter["angular_model"] = "manufacturer_ies"
    emitter["angular_distribution"] = _synthetic_batwing_profile()
    emitter["orientation_matrix"] = np.eye(3).tolist()

    # Controlled-variable contract: geometry, power, spectrum, and visibility
    # are identical. Only the angular-model-specific fields are added.
    l_emitter = lambertian_design["channels"][0]["emitters"][0]
    m_emitter = manufacturer_design["channels"][0]["emitters"][0]
    assert l_emitter["position_m"] == m_emitter["position_m"]
    assert l_emitter["radiant_power_w"] == m_emitter["radiant_power_w"]
    assert lambertian_design["channels"][0]["spectrum"] is not None
    assert manufacturer_design["channels"][0]["spectrum"] is not None
    assert lambertian_design["occluders"] == manufacturer_design["occluders"] == []

    lambertian = simulate_design(lambertian_design)
    manufacturer_a = simulate_design(manufacturer_design)
    manufacturer_b = simulate_design(manufacturer_design)

    l_field = np.asarray(lambertian["ppfd"], dtype=float)
    m_field_a = np.asarray(manufacturer_a["ppfd"], dtype=float)
    m_field_b = np.asarray(manufacturer_b["ppfd"], dtype=float)

    assert l_field.shape == m_field_a.shape == (7, 11)
    assert np.all(np.isfinite(l_field))
    assert np.all(np.isfinite(m_field_a))
    assert np.all(l_field >= 0.0)
    assert np.all(m_field_a >= 0.0)

    # Determinism: the same manufacturer input produces byte-equivalent values.
    assert np.array_equal(m_field_a, m_field_b)

    # Scientific A/B expectation: angular redistribution changes the field even
    # though the controlled geometry/power/SPD/visibility inputs are unchanged.
    assert not np.allclose(l_field, m_field_a, rtol=1e-6, atol=1e-12)
    assert float(np.mean(np.abs(m_field_a - l_field))) > 0.0

    assert lambertian["blocked_ray_count"] == 0
    assert manufacturer_a["blocked_ray_count"] == 0
    assert lambertian["total_ray_count"] == manufacturer_a["total_ray_count"]
