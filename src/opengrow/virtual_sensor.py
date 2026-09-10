"""Persistent virtual quantum-sensor state over displayed simulation results.

The sensor stores only a world-space selection. Scientific values are always
recomputed by bilinearly sampling the authoritative displayed result, so a
fixture edit + simulation or baseline/current toggle cannot leave stale values.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from opengrow.display_state import sample_virtual_sensor


class VirtualSensorState:
    """Persist a canopy selection and sample whichever result is displayed."""

    def __init__(self):
        self._world_point_m: list[float] | None = None

    @property
    def has_selection(self) -> bool:
        return self._world_point_m is not None

    @property
    def world_point_m(self) -> list[float] | None:
        return None if self._world_point_m is None else list(self._world_point_m)

    def clear(self) -> None:
        self._world_point_m = None

    def select(self, result: dict, world_point_m: Iterable[float]) -> dict:
        """Validate/store a point and return its sample for ``result``."""
        point = np.asarray(list(world_point_m), dtype=float)
        sample = sample_virtual_sensor(result, point)
        self._world_point_m = point.tolist()
        return sample

    def sample(self, result: dict | None) -> dict | None:
        """Sample the persistent point from the currently displayed result."""
        if result is None or self._world_point_m is None:
            return None
        return sample_virtual_sensor(result, self._world_point_m)
