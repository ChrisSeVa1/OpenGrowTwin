import numpy as np
import pytest

from opengrow.usd.live_results import colorize_ppfd, comparison_legend_range, legend_range


def test_colorize_uses_fixed_clamped_scale():
    colors = colorize_ppfd(np.array([-10, 0, 50, 100, 200]), 0, 100)
    assert colors.shape == (5, 3)
    assert colors[0] == pytest.approx(colors[1])
    assert colors[-1] == pytest.approx(colors[-2])
    assert not np.allclose(colors[1], colors[2])


def test_colorize_rejects_invalid_legend():
    with pytest.raises(ValueError, match="legend maximum"):
        colorize_ppfd([1, 2], 5, 5)


def test_legend_range_tracks_the_exact_displayed_field():
    assert legend_range([[10.0, 20.0], [30.0, 40.0]]) == pytest.approx((10.0, 40.0))
    assert legend_range([[100.0, 125.0], [150.0, 175.0]]) == pytest.approx((100.0, 175.0))


def test_legend_range_expands_constant_field_without_changing_minimum():
    minimum, maximum = legend_range(np.full((2, 2), 12.5))
    assert minimum == pytest.approx(12.5)
    assert maximum == pytest.approx(13.5)


def test_comparison_legend_range_is_shared_absolute_scale():
    baseline = np.array([[40.0, 50.0], [60.0, 70.0]])
    current = np.array([[120.0, 150.0], [180.0, 220.0]])
    assert comparison_legend_range(baseline, current) == pytest.approx((40.0, 220.0))


def test_comparison_legend_range_handles_zero_light_case():
    zeros = np.zeros((2, 2))
    assert comparison_legend_range(zeros, zeros) == pytest.approx((0.0, 1.0))
