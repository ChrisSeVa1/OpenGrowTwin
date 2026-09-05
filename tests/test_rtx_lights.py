import pytest

from opengrow.usd.rtx_lights import _normalized_ies_mapping, visual_intensity, wavelength_to_visual_rgb


def test_visual_color_distinguishes_channels():
    blue = wavelength_to_visual_rgb(450)
    red = wavelength_to_visual_rgb(660)
    far_red = wavelength_to_visual_rgb(730)
    assert blue[2] > blue[0]
    assert red[0] > red[2]
    assert far_red[0] < red[0]


def test_visual_intensity_is_linear_and_disabled_is_dark():
    assert visual_intensity(2.25) == pytest.approx(1125.0)
    assert visual_intensity(4.5) == pytest.approx(2250.0)
    assert visual_intensity(4.5, enabled=False) == 0.0


def test_visual_mapping_rejects_invalid_scientific_values():
    with pytest.raises(ValueError):
        wavelength_to_visual_rgb(float("nan"))
    with pytest.raises(ValueError):
        visual_intensity(-1)


def test_ies_mapping_is_optional_and_preserves_asset_paths():
    assert _normalized_ies_mapping(None) == {}
    mapping = _normalized_ies_mapping({
        "blue": "sources/osram/extracted/GD_PUBRA1_15_20250529.ies",
        "red": "/tmp/GH_PUBRA1_25_20250526.ies",
    })
    assert mapping["blue"].endswith("GD_PUBRA1_15_20250529.ies")
    assert mapping["red"] == "/tmp/GH_PUBRA1_25_20250526.ies"


def test_ies_mapping_rejects_empty_identifiers_and_paths():
    with pytest.raises(TypeError):
        _normalized_ies_mapping(["blue.ies"])
    with pytest.raises(ValueError):
        _normalized_ies_mapping({"": "blue.ies"})
    with pytest.raises(ValueError):
        _normalized_ies_mapping({"blue": ""})
