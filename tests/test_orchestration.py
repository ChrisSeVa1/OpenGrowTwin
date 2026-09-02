import numpy as np
import pytest

from opengrow.orchestration import apply_grid_mode, run_prepared_design


def _design():
    return {
        "grid": {"width_m": 1.0, "depth_m": 0.6, "nx": 41, "ny": 25},
        "channels": [{"id": "red", "wavelength_nm": 660, "emitters": [{
            "position_m": [0, 0, 0.6], "direction": [0, 0, -1],
            "radiant_power_w": 1.0, "beam_exponent": 1.0,
        }]}],
        "occluders": [],
    }


def test_preview_and_final_grid_modes_do_not_mutate_input():
    design = _design()
    assert apply_grid_mode(design, "preview")["grid"]["nx"] == 21
    assert apply_grid_mode(design, "preview")["grid"]["ny"] == 13
    assert apply_grid_mode(design, "final")["grid"]["nx"] == 41
    assert design["grid"]["nx"] == 41


def test_unknown_grid_mode_is_rejected():
    with pytest.raises(ValueError, match="unknown simulation mode"):
        apply_grid_mode(_design(), "instant")


def test_prepared_design_returns_metrics_and_shape():
    result = run_prepared_design(apply_grid_mode(_design(), "preview"))
    assert result["mode_shape"] == [21, 13]
    assert result["metrics"]["mean_ppfd_umol_m2_s"] > 0
    assert result["blocked_ray_count"] == 0
    assert np.asarray(result["fields"]["ppfd"]).shape == (13, 21)


def test_preview_mean_tracks_final_within_three_percent_for_simple_fixture():
    preview = run_prepared_design(apply_grid_mode(_design(), "preview"))
    final = run_prepared_design(apply_grid_mode(_design(), "final"))
    difference = abs(
        preview["metrics"]["mean_ppfd_umol_m2_s"] - final["metrics"]["mean_ppfd_umol_m2_s"]
    ) / final["metrics"]["mean_ppfd_umol_m2_s"]
    assert difference < 0.03
