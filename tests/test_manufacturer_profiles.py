from pathlib import Path

from opengrow.manufacturer_profiles import (
    OSRAM_PROFILES,
    apply_manufacturer_profiles,
    manufacturer_bundle_available,
    manufacturer_ies_by_channel,
)
from opengrow.physics.spectrum import TabulatedSpectrum


IES_TEXT = """IESNA:LM-63-2002
TILT=NONE
1 1 1 2 1 1 2 0 0 0
1 0 1
0 180
0
1 1
"""

SPECTRUM_TEXT = """400 1
500 1
600 0.5
750 0.1
"""


def _write_bundle(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    for profile in OSRAM_PROFILES.values():
        (root / profile["ies"]).write_text(IES_TEXT, encoding="utf-8")
        (root / profile["spectrum"]).write_text(SPECTRUM_TEXT, encoding="utf-8")


def _design():
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    return {
        "grid": {"width_m": 1.0, "depth_m": 1.0, "nx": 3, "ny": 3},
        "channels": [
            {
                "id": channel_id,
                "wavelength_nm": wavelength,
                "emitters": [
                    {
                        "source_path": f"/{channel_id}",
                        "position_m": [0.0, 0.0, 0.6],
                        "direction": [0.0, 0.0, -1.0],
                        "orientation_matrix": identity,
                        "radiant_power_w": 1.0,
                        "beam_exponent": 1.0,
                    }
                ],
            }
            for channel_id, wavelength in (("blue", 450.0), ("red", 660.0), ("far_red", 730.0))
        ],
        "occluders": [],
    }


def test_complete_local_bundle_enriches_solver_design(tmp_path):
    _write_bundle(tmp_path)
    assert manufacturer_bundle_available(tmp_path)

    mapping = manufacturer_ies_by_channel(tmp_path, required=True)
    assert set(mapping) == {"blue", "red", "far_red"}
    assert all(Path(path).is_file() for path in mapping.values())

    configured = apply_manufacturer_profiles(_design(), tmp_path, required=True)
    for channel in configured["channels"]:
        assert isinstance(channel["spectrum"], TabulatedSpectrum)
        assert channel["manufacturer_profile"]["part_number"]
        emitter = channel["emitters"][0]
        assert emitter["angular_model"] == "manufacturer_ies"
        assert emitter["angular_distribution"].solid_angle_integral() > 0.0


def test_missing_optional_bundle_preserves_generic_fallback(tmp_path):
    configured = apply_manufacturer_profiles(_design(), tmp_path, required=False)
    assert all("spectrum" not in channel for channel in configured["channels"])
    assert all(
        "angular_model" not in emitter
        for channel in configured["channels"]
        for emitter in channel["emitters"]
    )
    assert manufacturer_ies_by_channel(tmp_path, required=False) == {}
