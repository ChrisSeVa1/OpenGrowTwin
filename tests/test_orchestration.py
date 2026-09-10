import numpy as np
import pytest

from opengrow.orchestration import apply_grid_mode, apply_optical_model, run_prepared_design


def _design():
    return {
        "grid": {"width_m": 1.0, "depth_m": 0.6, "nx": 41, "ny": 25},
        "channels": [{"id": "red", "wavelength_nm": 660, "emitters": [{
            "position_m": [0, 0, 0.6], "direction": [0, 0, -1],
            "radiant_power_w": 1.0, "beam_exponent": 1,
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


def test_simplified_optical_model_is_explicit_and_non_mutating():
    design = _design()
    configured = apply_optical_model(design, "simplified")
    assert configured == design
    assert configured is not design
    configured["channels"][0]["emitters"][0]["radiant_power_w"] = 99.0
    assert design["channels"][0]["emitters"][0]["radiant_power_w"] == pytest.approx(1.0)


def test_unknown_optical_model_is_rejected():
    with pytest.raises(ValueError, match="unknown optical model"):
        apply_optical_model(_design(), "magic")


def test_prepared_design_returns_metrics_and_shape():
    result = run_prepared_design(apply_grid_mode(_design(), "preview"))
    assert result["mode_shape"] == [21, 13]
    assert result["metrics"]["mean_ppfd_umol_m2_s"] > 0
    assert result["blocked_ray_count"] == 0
    assert np.asarray(result["fields"]["ppfd"]).shape == (13, 21)


def test_all_emitters_off_returns_valid_zero_field():
    design = _design()
    design["channels"] = []
    result = run_prepared_design(apply_grid_mode(design, "preview"))
    assert result["mode_shape"] == [21, 13]
    assert result["metrics"]["mean_ppfd_umol_m2_s"] == pytest.approx(0.0)
    assert result["metrics"]["min_ppfd_umol_m2_s"] == pytest.approx(0.0)
    assert result["metrics"]["max_ppfd_umol_m2_s"] == pytest.approx(0.0)
    assert result["metrics"]["dli_mol_m2_day"] == pytest.approx(0.0)
    assert result["metrics"]["mean_far_red_umol_m2_s"] == pytest.approx(0.0)
    assert result["total_ray_count"] == 0
    assert np.count_nonzero(result["fields"]["ppfd"]) == 0


def test_preview_mean_tracks_final_within_three_percent_for_simple_fixture():
    preview = run_prepared_design(apply_grid_mode(_design(), "preview"))
    final = run_prepared_design(apply_grid_mode(_design(), "final"))
    difference = abs(
        preview["metrics"]["mean_ppfd_umol_m2_s"] - final["metrics"]["mean_ppfd_umol_m2_s"]
    ) / final["metrics"]["mean_ppfd_umol_m2_s"]
    assert difference < 0.03
