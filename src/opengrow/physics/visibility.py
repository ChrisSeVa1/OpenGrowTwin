"""Finite visibility rays against oriented proxy boxes."""

from __future__ import annotations

import numpy as np


def segment_box_visibility(sensor_points, source_position, box: dict, epsilon: float = 1e-9):
    """Return True where source-to-sensor segments do not hit an oriented box.

    The segment is parameterized from source (t=0) to sensor (t=1). Endpoints
    are excluded so a source or sensor resting on geometry is not self-blocked.
    """
    points = np.asarray(sensor_points, dtype=float)
    source = np.asarray(source_position, dtype=float)
    center = np.asarray(box["center_m"], dtype=float)
    axes = np.asarray(box["axes"], dtype=float)
    half_extents = np.asarray(box["half_extents_m"], dtype=float)
    if source.shape != (3,) or center.shape != (3,) or axes.shape != (3, 3) or half_extents.shape != (3,):
        raise ValueError("box visibility inputs have invalid dimensions")
    if np.any(half_extents <= 0) or np.any(~np.isfinite(half_extents)):
        raise ValueError("box half extents must be finite and positive")
    if not np.allclose(axes @ axes.T, np.eye(3), atol=1e-6):
        raise ValueError("box axes must be orthonormal")

    local_source = (source - center) @ axes.T
    local_points = (points - center) @ axes.T
    direction = local_points - local_source
    flat_direction = direction.reshape(-1, 3)
    t_near = np.full(flat_direction.shape[0], -np.inf)
    t_far = np.full(flat_direction.shape[0], np.inf)
    valid = np.ones(flat_direction.shape[0], dtype=bool)
    for axis in range(3):
        origin = local_source[axis]
        delta = flat_direction[:, axis]
        parallel = np.abs(delta) <= epsilon
        valid &= ~(parallel & (abs(origin) > half_extents[axis] + epsilon))
        nonparallel = ~parallel
        first = np.full_like(delta, -np.inf)
        second = np.full_like(delta, np.inf)
        first[nonparallel] = (-half_extents[axis] - origin) / delta[nonparallel]
        second[nonparallel] = (half_extents[axis] - origin) / delta[nonparallel]
        t_near = np.maximum(t_near, np.minimum(first, second))
        t_far = np.minimum(t_far, np.maximum(first, second))
    intersects = valid & (t_near <= t_far + epsilon) & (t_far > epsilon) & (t_near < 1.0 - epsilon)
    return (~intersects).reshape(points.shape[:-1])


def visibility_mask(sensor_points, source_position, occluders: list[dict] | None = None):
    """Combine visibility across all enabled proxy-box occluders."""
    visible = np.ones(np.asarray(sensor_points).shape[:-1], dtype=bool)
    for occluder in occluders or []:
        if not occluder.get("enabled", True):
            continue
        if occluder.get("shape", "box") != "box":
            raise ValueError(f"unsupported occluder shape: {occluder.get('shape')!r}")
        visible &= segment_box_visibility(sensor_points, source_position, occluder)
    return visible
