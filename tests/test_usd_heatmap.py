import numpy as np
import pytest

from opengrow.usd.heatmap import heatmap_mesh_data, write_heatmap_usda


GRID = {"width_m": 1.0, "depth_m": 0.6, "nx": 3, "ny": 2, "z_m": 0.0}


def test_heatmap_mesh_topology():
    data = heatmap_mesh_data(np.arange(6, dtype=float).reshape(2, 3), GRID)
    assert data["points"].shape == (6, 3)
    assert data["face_vertex_counts"].tolist() == [4, 4]
    assert data["face_vertex_indices"].tolist() == [0, 1, 4, 3, 1, 2, 5, 4]
    assert data["ppfd"].tolist() == [0, 1, 2, 3, 4, 5]


def test_heatmap_shape_validation():
    with pytest.raises(ValueError):
        heatmap_mesh_data(np.zeros((3, 2)), GRID)


def test_usda_contains_exact_values_and_metadata(tmp_path):
    metrics = {
        "mean_ppfd_umol_m2_s": 2.5,
        "min_ppfd_umol_m2_s": 0.0,
        "max_ppfd_umol_m2_s": 5.0,
        "uniformity_min_mean": 0.0,
        "cv_ppfd": 0.683,
        "dli_mol_m2_day": 0.126,
    }
    result = write_heatmap_usda(
        np.arange(6, dtype=float).reshape(2, 3), GRID, metrics, tmp_path / "heatmap.usda"
    )
    text = (tmp_path / "heatmap.usda").read_text()
    assert result["vertex_count"] == 6
    assert result["face_count"] == 2
    assert 'float[] primvars:opengrow:ppfd = [0, 1, 2, 3, 4, 5]' in text
    assert "custom double opengrow:results:meanPPFD = 2.5" in text
    assert 'interpolation = "vertex"' in text
