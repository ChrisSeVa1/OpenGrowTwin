#!/usr/bin/env python3
"""Validate azimuthal rotation of real manufacturer Type-C IES profiles.

Raw manufacturer assets are supplied locally and are not redistributed. The
script rotates a single downward-facing emitter about its optical axis through
0/90/180/270 degrees and verifies that the sampled irradiance footprint changes
consistently while the normalized solid-angle integral remains unity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from opengrow.physics.direct_solver import manufacturer_ies_irradiance, sensor_grid
from opengrow.physics.photometry import load_ies


ASSETS = {
    "blue": ("GD PUBRA1.15", "GD_PUBRA1_15_20250529.ies"),
    "red": ("GH PUBRA1.25", "GH_PUBRA1_25_20250526.ies"),
    "far_red": ("GF PUBRA1.25", "GF_PUBRA1_25_20250603.ies"),
}


def _rz(deg: float) -> list[list[float]]:
    a = np.deg2rad(deg)
    c, s = float(np.cos(a)), float(np.sin(a))
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _metrics(field: np.ndarray) -> dict:
    values = np.asarray(field, dtype=float)
    mean = float(values.mean())
    return {
        "mean": mean,
        "min": float(values.min()),
        "max": float(values.max()),
        "std": float(values.std()),
        "cv": float(values.std() / mean) if mean > 0 else None,
    }


def _quarter_turn_error(reference: np.ndarray, rotated: np.ndarray, k: int) -> dict:
    # sensor_grid stores +Y at increasing row indices, whereas np.rot90(k=+1)
    # is counter-clockwise in image/array coordinates where row indices increase
    # downward. Therefore a positive physical +Z rotation maps to k=-1 per +90°.
    expected = np.rot90(reference, k=k)
    delta = np.asarray(rotated) - expected
    scale = float(np.max(np.abs(expected)))
    max_abs = float(np.max(np.abs(delta)))
    fraction = float(max_abs / scale) if scale > 0 else None
    return {
        "max_abs": max_abs,
        "rms": float(np.sqrt(np.mean(delta * delta))),
        "max_abs_fraction_of_peak": fraction,
        "passes_1e-10_fraction_of_peak": bool(fraction is not None and fraction <= 1e-10),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-root", default="sources/osram/extracted")
    parser.add_argument("--channel", choices=sorted(ASSETS), default="blue")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    part_number, filename = ASSETS[args.channel]
    ies_path = Path(args.asset_root) / filename
    if not ies_path.is_file():
        raise FileNotFoundError(ies_path)

    profile = load_ies(ies_path)
    normalized = profile.normalized()

    grid = sensor_grid(1.0, 1.0, 41, 41, z_m=0.0)
    position = [0.0, 0.0, 0.6]
    fields = {}
    metrics = {}
    for angle in (0, 90, 180, 270):
        field = manufacturer_ies_irradiance(
            grid,
            position,
            1.0,
            profile,
            _rz(angle),
            receiver_normal=[0.0, 0.0, 1.0],
        )
        fields[angle] = field
        metrics[str(angle)] = _metrics(field)

    checks = {
        "90_vs_physical_rot90_0": _quarter_turn_error(fields[0], fields[90], -1),
        "180_vs_physical_rot180_0": _quarter_turn_error(fields[0], fields[180], -2),
        "270_vs_physical_rot270_0": _quarter_turn_error(fields[0], fields[270], -3),
    }

    report = {
        "part_number": part_number,
        "ies": str(ies_path),
        "orientation_convention": {
            "optical_axis": "local -Z",
            "type_c_c0_reference": "local +X",
            "positive_rotation": "right-handed about world +Z / optical-axis line",
            "array_rotation_note": "positive physical +Z quarter-turn maps to np.rot90(..., k=-1) because sensor-grid +Y increases with row index",
        },
        "solid_angle_integral_raw": profile.solid_angle_integral(),
        "solid_angle_integral_normalized": normalized.solid_angle_integral(),
        "grid": {"width_m": 1.0, "depth_m": 1.0, "nx": 41, "ny": 41, "source_height_m": 0.6},
        "rotations_deg": metrics,
        "quarter_turn_consistency": checks,
        "all_quarter_turn_checks_pass": all(
            item["passes_1e-10_fraction_of_peak"] for item in checks.values()
        ),
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
