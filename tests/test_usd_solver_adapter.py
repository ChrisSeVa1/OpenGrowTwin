import copy

import pytest

from opengrow.usd.scene_contract import SCHEMA_VERSION
from opengrow.usd.stage_reader import entities_to_solver_design


def _discovery():
    return {
        "schema_version": SCHEMA_VERSION,
        "entities": {
            "sensorPlane": [{
                "width_m": 1.0, "depth_m": 0.6, "nx": 5, "ny": 3,
                "center_m": [0, 0, 0], "u_axis": [1, 0, 0], "v_axis": [0, 1, 0],
            }],
            "emitter": [{
                "path": "/Emitter", "channel": "blue", "wavelength_nm": 450,
                "radiant_power_w": 2.5, "beam_exponent": 1.0, "enabled": True,
                "position_m": [0, 0, 0.6], "direction": [0, 0, -1],
            }],
            "occluder": [{
                "path": "/Box", "shape": "box", "enabled": True,
                "center_m": [2, 0, 0.3], "axes": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "half_extents_m": [0.1, 0.2, 0.3],
            }],
        },
    }


def test_discovery_converts_to_solver_design():
    design = entities_to_solver_design(_discovery())
    assert design["grid"]["center_m"] == [0.0, 0.0, 0.0]
    assert design["channels"][0]["id"] == "blue"
    assert design["channels"][0]["emitters"][0]["source_path"] == "/Emitter"
    assert design["channels"][0]["emitters"][0]["direction"] == [0.0, 0.0, -1.0]
    assert design["occluders"][0]["half_extents_m"] == [0.1, 0.2, 0.3]


def test_disabled_emitters_are_excluded():
    discovery = _discovery()
    discovery["entities"]["emitter"][0]["enabled"] = False
    with pytest.raises(ValueError, match="no enabled emitters"):
        entities_to_solver_design(discovery)


def test_adapter_rejects_inconsistent_channel_wavelengths():
    discovery = _discovery()
    second = copy.deepcopy(discovery["entities"]["emitter"][0])
    second["path"] = "/Emitter2"
    second["wavelength_nm"] = 451
    discovery["entities"]["emitter"].append(second)
    with pytest.raises(ValueError, match="inconsistent wavelengths"):
        entities_to_solver_design(discovery)
