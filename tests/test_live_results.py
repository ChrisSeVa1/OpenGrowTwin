import numpy as np
import pytest

from opengrow.usd.live_results import colorize_ppfd


def test_colorize_uses_fixed_clamped_scale():
    colors = colorize_ppfd(np.array([-10, 0, 50, 100, 200]), 0, 100)
    assert colors.shape == (5, 3)
    assert colors[0] == pytest.approx(colors[1])
    assert colors[-1] == pytest.approx(colors[-2])
    assert not np.allclose(colors[1], colors[2])


def test_colorize_rejects_invalid_legend():
    with pytest.raises(ValueError, match="legend maximum"):
        colorize_ppfd([1, 2], 5, 5)
