import numpy as np

from opengrow.physics.visibility import segment_box_visibility, visibility_mask


BOX = {
    "shape": "box",
    "enabled": True,
    "center_m": [0, 0, 0.5],
    "axes": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
    "half_extents_m": [0.1, 0.1, 0.1],
}


def test_box_blocks_only_intersecting_segments():
    sensors = np.array([[[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]]])
    visible = segment_box_visibility(sensors, [0, 0, 1], BOX)
    assert visible.tolist() == [[False, True]]


def test_disabled_box_does_not_block():
    sensors = np.array([[[0.0, 0.0, 0.0]]])
    box = {**BOX, "enabled": False}
    assert visibility_mask(sensors, [0, 0, 1], [box]).item()


def test_rotated_box_uses_oriented_axes():
    root = np.sqrt(0.5)
    box = {**BOX, "axes": [[root, root, 0], [-root, root, 0], [0, 0, 1]]}
    sensors = np.array([[[0.0, 0.0, 0.0], [0.5, 0.0, 0.0]]])
    assert segment_box_visibility(sensors, [0, 0, 1], box).tolist() == [[False, True]]
