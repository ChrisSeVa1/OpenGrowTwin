import numpy as np
import pytest

from opengrow.display_state import (
    optical_model_summary,
    ppfd_legend,
    sample_virtual_sensor,
    select_display_result,
    spectrum_plot_curves,
    spectrum_series,
)
from opengrow.physics.spectrum import parse_spectrum_text


def _result():
    return {
        "design": {
            "grid": {
                "width_m": 2.0,
                "depth_m": 2.0,
                "nx": 2,
                "ny": 2,
                "center_m": [0.0, 0.0, 0.0],
                "u_axis": [1.0, 0.0, 0.0],
                "v_axis": [0.0, 1.0, 0.0],
            },
            "channels": [
                {
                    "id": "blue",
                    "wavelength_nm": 450.0,
                    "emitters": [{"angular_model": "generalized_lambertian"}],
                },
                {
                    "id": "red",
                    "wavelength_nm": 660.0,
                    "emitters": [{"angular_model": "generalized_lambertian"}],
                },
                {
                    "id": "far_red",
                    "wavelength_nm": 730.0,
                    "emitters": [{"angular_model": "generalized_lambertian"}],
                },
            ],
        },
        "fields": {
            "ppfd": np.array([[10.0, 20.0], [30.0, 40.0]]),
            "far_red": np.array([[1.0, 2.0], [3.0, 4.0]]),
            "spectral_irradiance": np.array(
                [
                    [[1.0, 1.0], [1.0, 1.0]],
                    [[2.0, 2.0], [2.0, 2.0]],
                    [[3.0, 3.0], [3.0, 3.0]],
                ]
            ),
        },
        "metrics": {},
    }


def test_select_display_result_tracks_current_and_baseline():
    current = {"id": "current"}
    baseline = {"id": "baseline"}
    assert select_display_result(current, baseline, "current") is current
    assert select_display_result(current, baseline, "baseline") is baseline
    with pytest.raises(ValueError, match="baseline"):
        select_display_result(current, None, "baseline")


def test_ppfd_legend_uses_displayed_field_limits():
    legend = ppfd_legend(_result())
    assert legend["minimum"] == pytest.approx(10.0)
    assert legend["maximum"] == pytest.approx(40.0)
    assert legend["unit"] == "µmol m⁻² s⁻¹"


def test_spectrum_series_uses_actual_tabulated_spd_shape():
    design = _result()["design"]
    spectrum = parse_spectrum_text("440 0.25\n450 1.0\n460 0.5\n")
    design["channels"][0]["spectrum"] = spectrum
    design["channels"][0]["manufacturer_profile"] = {"part_number": "TEST BLUE"}
    series = spectrum_series(design)
    blue = series[0]
    assert blue["kind"] == "tabulated_relative_spd"
    assert blue["part_number"] == "TEST BLUE"
    assert blue["peak_wavelength_nm"] == pytest.approx(450.0)
    assert blue["wavelengths_nm"] == [440.0, 450.0, 460.0]
    assert blue["relative_power"] == pytest.approx([0.25, 1.0, 0.5])
    assert series[1]["kind"] == "monochromatic_fallback"


def test_spectrum_plot_curves_align_real_spd_and_fallback_channels():
    design = _result()["design"]
    design["channels"][0]["spectrum"] = parse_spectrum_text("440 0.0\n450 1.0\n460 0.0\n")
    plot = spectrum_plot_curves(design, 380.0, 800.0, 211)
    assert len(plot["wavelengths_nm"]) == 211
    assert set(plot["curves"]) == {"blue", "red", "far_red"}
    assert all(len(values) == 211 for values in plot["curves"].values())
    wavelengths = np.asarray(plot["wavelengths_nm"])
    blue = np.asarray(plot["curves"]["blue"])
    red = np.asarray(plot["curves"]["red"])
    assert wavelengths[int(np.argmax(blue))] == pytest.approx(450.0, abs=2.1)
    assert wavelengths[int(np.argmax(red))] == pytest.approx(660.0, abs=2.1)


def test_optical_model_summary_requires_complete_manufacturer_configuration():
    design = _result()["design"]
    assert optical_model_summary(design)["mode"] == "generalized_lambertian"
    for channel in design["channels"]:
        channel["manufacturer_profile"] = {
            "part_number": channel["id"],
            "ies_filename": f"{channel['id']}.ies",
            "spectrum_filename": f"{channel['id']}.txt",
        }
        for emitter in channel["emitters"]:
            emitter["angular_model"] = "manufacturer_ies"
    summary = optical_model_summary(design)
    assert summary["mode"] == "manufacturer_ies_spd"
    assert summary["label"] == "Manufacturer IES + SPD"
    assert len(summary["profiles"]) == 3


def test_virtual_sensor_bilinearly_interpolates_center():
    result = _result()
    sensor = sample_virtual_sensor(result, [0.0, 0.0, 0.0], photoperiod_h=14.0)
    assert sensor["ppfd_umol_m2_s"] == pytest.approx(25.0)
    assert sensor["far_red_umol_m2_s"] == pytest.approx(2.5)
    assert sensor["dli_mol_m2_day"] == pytest.approx(25.0 * 14.0 * 3600.0 / 1_000_000.0)
    assert sensor["grid_fraction"] == pytest.approx([0.5, 0.5])
    assert sensor["channel_ppfd_umol_m2_s"]["blue"] > 0.0
    assert sensor["channel_ppfd_umol_m2_s"]["red"] > 0.0
    assert sensor["channel_ppfd_umol_m2_s"]["far_red"] == pytest.approx(0.0)


def test_virtual_sensor_accepts_heatmap_display_offset_but_rejects_bad_hits():
    result = _result()
    assert sample_virtual_sensor(result, [0.0, 0.0, 0.002])["ppfd_umol_m2_s"] == pytest.approx(25.0)
    with pytest.raises(ValueError, match="outside"):
        sample_virtual_sensor(result, [1.5, 0.0, 0.0])
    with pytest.raises(ValueError, match="sensor plane"):
        sample_virtual_sensor(result, [0.0, 0.0, 0.1])
