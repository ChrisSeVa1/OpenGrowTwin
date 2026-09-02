import json

import pytest

from opengrow.usd.scene_contract import SCHEMA_VERSION, validate_design_for_scene, write_live_scene_usda


def _design():
    return {
        "grid": {"width_m": 1.0, "depth_m": 0.6, "nx": 5, "ny": 3, "z_m": 0.0},
        "channels": [
            {
                "id": "blue",
                "wavelength_nm": 450,
                "emitters": [
                    {"position_m": [0.1, -0.1, 0.6], "radiant_power_w": 2.5, "beam_exponent": 1.0}
                ],
            },
            {
                "id": "far_red",
                "wavelength_nm": 730,
                "emitters": [
                    {"position_m": [-0.1, 0.1, 0.6], "radiant_power_w": 0.5, "beam_exponent": 2.0}
                ],
            },
        ],
    }


def test_live_scene_contains_discoverable_contract(tmp_path):
    path = tmp_path / "scene.usda"
    result = write_live_scene_usda(_design(), path)
    text = path.read_text(encoding="utf-8")
    assert result == {
        "path": "scene.usda",
        "schema_version": SCHEMA_VERSION,
        "fixture_count": 1,
        "emitter_count": 2,
        "sensor_plane_count": 1,
        "occluder_count": 1,
    }
    assert 'metersPerUnit = 1' in text
    assert 'upAxis = "Z"' in text
    assert text.count('opengrow:role = "emitter"') == 2
    assert 'custom token opengrow:role = "sensorPlane"' in text
    assert 'custom token opengrow:role = "occluder"' in text
    assert 'custom double opengrow:wavelengthNm = 450' in text
    assert 'custom double3 opengrow:emissionDirection = (0, 0, -1)' in text
    assert 'double3 xformOp:translate = (0.1, -0.1, 0)' in text


def test_scene_design_validation_rejects_invalid_power():
    design = _design()
    design["channels"][0]["emitters"][0]["radiant_power_w"] = -1
    with pytest.raises(ValueError, match="radiant_power_w"):
        validate_design_for_scene(design)


def test_cli_authors_scene(tmp_path, capsys):
    from opengrow.cli import main

    design_path = tmp_path / "design.json"
    output_path = tmp_path / "live.usda"
    design_path.write_text(json.dumps(_design()), encoding="utf-8")
    assert main(["scene", str(design_path), "--out", str(output_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["emitter_count"] == 2
    assert output_path.exists()
