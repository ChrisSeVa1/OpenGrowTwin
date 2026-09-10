import copy

import numpy as np
import pytest

from opengrow.virtual_sensor import VirtualSensorState


def _result(scale=1.0):
    ppfd = np.array([[10.0, 20.0], [30.0, 40.0]]) * scale
    far_red = np.array([[1.0, 2.0], [3.0, 4.0]]) * scale
    spectral = np.zeros((0, 2, 2), dtype=float)
    return {
        "design": {
            "grid": {
                "width_m": 1.0,
                "depth_m": 1.0,
                "center_m": [0.0, 0.0, 0.0],
                "u_axis": [1.0, 0.0, 0.0],
                "v_axis": [0.0, 1.0, 0.0],
            },
            "channels": [],
        },
        "fields": {
            "ppfd": ppfd,
            "far_red": far_red,
            "spectral_irradiance": spectral,
        },
    }


def test_selection_persists_and_refreshes_against_new_displayed_result():
    state = VirtualSensorState()
    baseline = _result(1.0)
    current = _result(2.0)

    selected = state.select(baseline, [0.0, 0.0, 0.0])
    assert state.has_selection
    assert state.world_point_m == [0.0, 0.0, 0.0]
    assert selected["ppfd_umol_m2_s"] == pytest.approx(25.0)

    refreshed = state.sample(current)
    assert refreshed["ppfd_umol_m2_s"] == pytest.approx(50.0)
    assert refreshed["far_red_umol_m2_s"] == pytest.approx(5.0)
    assert state.world_point_m == [0.0, 0.0, 0.0]


def test_clear_removes_selection_without_mutating_result():
    result = _result()
    original = copy.deepcopy(result["fields"]["ppfd"])
    state = VirtualSensorState()
    state.select(result, [0.25, -0.25, 0.0])
    state.clear()

    assert not state.has_selection
    assert state.world_point_m is None
    assert state.sample(result) is None
    np.testing.assert_array_equal(result["fields"]["ppfd"], original)


def test_invalid_selection_is_not_persisted():
    state = VirtualSensorState()
    with pytest.raises(ValueError, match="outside the sensor footprint"):
        state.select(_result(), [0.75, 0.0, 0.0])
    assert not state.has_selection
