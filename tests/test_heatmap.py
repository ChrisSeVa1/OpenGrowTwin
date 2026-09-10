import numpy as np
import pytest

from opengrow.visualization.heatmap import render_comparison


def test_heatmap_rejects_mismatched_fields(tmp_path):
    with pytest.raises(ValueError):
        render_comparison(np.zeros((2, 2)), np.zeros((3, 3)),
                          {"width_m": 1.0, "depth_m": 1.0}, tmp_path)
