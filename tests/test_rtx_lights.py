import pytest

from opengrow.usd.rtx_lights import visual_intensity, wavelength_to_visual_rgb


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
