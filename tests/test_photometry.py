import numpy as np
import pytest

from opengrow.physics.photometry import parse_ies_text


IES_FIXTURE = """IESNA:LM-63-2002
[TEST] synthetic
[MANUFAC] OpenGrowTwin test
TILT=NONE
1
1.0
2.0
3
3
1
2
0.0037 0.0037 0.00175
1 1 2.0
0 90 180
0 180 360
1 2 1
2 4 2
1 2 1
"""


def test_parse_ies_type_c_metadata_and_multiplier():
    profile = parse_ies_text(IES_FIXTURE, source="synthetic.ies")
    assert profile.metadata.format_line == "IESNA:LM-63-2002"
    assert profile.metadata.keywords["MANUFAC"] == "OpenGrowTwin test"
    assert profile.source == "synthetic.ies"
    assert profile.intensity.shape == (3, 3)
    assert profile.intensity[1, 1] == pytest.approx(8.0)


def test_normalized_angular_distribution_integrates_to_one():
    profile = parse_ies_text(IES_FIXTURE).normalized()
    assert profile.solid_angle_integral() == pytest.approx(1.0, rel=1e-12, abs=1e-12)


def test_azimuth_interpolation_is_periodic():
    profile = parse_ies_text(IES_FIXTURE)
    assert profile.sample(90.0, 0.0) == pytest.approx(profile.sample(90.0, 360.0))
    assert profile.sample(90.0, -10.0) == pytest.approx(profile.sample(90.0, 350.0))


def test_bilinear_interpolation_returns_expected_midpoint():
    profile = parse_ies_text(IES_FIXTURE)
    # At theta=45 and phi=90 the four surrounding values are 2,4,4,8
    # after applying the 2x LM-63 multiplier, so the bilinear mean is 4.5.
    assert profile.sample(45.0, 90.0) == pytest.approx(4.5)


def test_rejects_tilted_or_non_type_c_profiles():
    with pytest.raises(ValueError, match="TILT=NONE"):
        parse_ies_text(IES_FIXTURE.replace("TILT=NONE", "TILT=INCLUDE"))
    with pytest.raises(ValueError, match="Type-C"):
        parse_ies_text(IES_FIXTURE.replace("\n1\n2\n0.0037", "\n2\n2\n0.0037", 1))


def test_sample_outside_vertical_support_is_zero():
    # A partial manufacturer table may intentionally bound support below 180 deg.
    partial = IES_FIXTURE.replace("0 90 180", "0 45 90")
    profile = parse_ies_text(partial)
    assert profile.sample(120.0, 0.0) == 0.0
