#!/usr/bin/env python3
"""Compare generalized-Lambertian and manufacturer-IES transport.

The comparison intentionally holds geometry, radiant power, visibility, and
manufacturer tabulated SPD constant. Only the angular model changes. Vendor
assets are read from user-supplied local paths and are never bundled here.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np

from opengrow.physics.direct_solver import simulate_design
from opengrow.physics.photometry import load_ies
from opengrow.physics.spectrum import load_spectrum


ASSETS = {
    "blue": {
        "ies": "GD_PUBRA1_15_20250529.ies",
        "spectrum": "GD_PUBRA1_15_20250529_spectrum.txt",
        "part_number": "GD PUBRA1.15",
    },
    "red": {
        "ies": "GH_PUBRA1_25_20250526.ies",
        "spectrum": "GH_PUBRA1_25_20250526_spectrum.txt",
        "part_number": "GH PUBRA1.25",
    },
    "far_red": {
        "ies": "GF_PUBRA1_25_20250603.ies",
        "spectrum": "GF_PUBRA1_25_20250603_spectrum.txt",
        "part_number": "GF PUBRA1.25",
    },
}

# Demo fixture emitters point down. For manufacturer photometry OpenGrowTwin
# defines local -Z as the optical axis and +X as the Type-C C=0 direction.
IDENTITY_ORIENTATION = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _metrics(field: np.ndarray) -> dict:
    values = np.asarray(field, dtype=float)
    mean = float(np.mean(values))
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    std = float(np.std(values))
    return {
        "mean": mean,
        "min": minimum,
        "max": maximum,
        "std": std,
        "cv": std / mean if mean > 0.0 else None,
        "min_mean_uniformity": minimum / mean if mean > 0.0 else None,
    }


def _difference(reference: np.ndarray, candidate: np.ndarray) -> dict:
    reference = np.asarray(reference, dtype=float)
    candidate = np.asarray(candidate, dtype=float)
    delta = candidate - reference
    denominator = float(np.mean(reference))
    return {
        "mean_delta": float(np.mean(delta)),
        "mean_absolute_delta": float(np.mean(np.abs(delta))),
        "max_absolute_delta": float(np.max(np.abs(delta))),
        "rms_delta": float(np.sqrt(np.mean(np.square(delta)))),
        "mean_absolute_delta_percent_of_lambertian_mean": (
            100.0 * float(np.mean(np.abs(delta))) / denominator if denominator > 0.0 else None
        ),
    }


def _load_design(design_path: Path, asset_root: Path):
    base = json.loads(design_path.read_text(encoding="utf-8"))
    # OGT-301A compares direct transport only; an absent occluder list means all
    # rays remain visible while preserving the same visibility path in both runs.
    base.setdefault("occluders", [])

    missing_channels = {channel["id"] for channel in base["channels"]} - set(ASSETS)
    if missing_channels:
        raise ValueError(f"no manufacturer asset mapping for channels: {sorted(missing_channels)}")

    lambertian = copy.deepcopy(base)
    manufacturer = copy.deepcopy(base)
    provenance = {}

    for lam_channel, ies_channel in zip(lambertian["channels"], manufacturer["channels"]):
        channel_id = lam_channel["id"]
        asset = ASSETS[channel_id]
        ies_path = asset_root / asset["ies"]
        spectrum_path = asset_root / asset["spectrum"]
        if not ies_path.is_file():
            raise FileNotFoundError(ies_path)
        if not spectrum_path.is_file():
            raise FileNotFoundError(spectrum_path)

        angular_distribution = load_ies(ies_path)
        spectrum = load_spectrum(spectrum_path)
        # Use the same manufacturer SPD in both runs so the comparison isolates
        # angular photometry rather than mixing angular and spectral changes.
        lam_channel["spectrum"] = spectrum
        ies_channel["spectrum"] = spectrum

        for emitter in lam_channel["emitters"]:
            emitter["angular_model"] = "generalized_lambertian"
            emitter.setdefault("direction", [0.0, 0.0, -1.0])
        for emitter in ies_channel["emitters"]:
            emitter["angular_model"] = "manufacturer_ies"
            emitter["angular_distribution"] = angular_distribution
            emitter["orientation_matrix"] = IDENTITY_ORIENTATION

        provenance[channel_id] = {
            "part_number": asset["part_number"],
            "ies": str(ies_path),
            "spectrum": str(spectrum_path),
            "ies_solid_angle_integral_raw": angular_distribution.solid_angle_integral(),
            "ies_solid_angle_integral_normalized": angular_distribution.normalized().solid_angle_integral(),
            "spectrum_peak_nm": spectrum.peak_wavelength_nm,
        }

    return lambertian, manufacturer, provenance


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", default="demo/design.json")
    parser.add_argument("--asset-root", default="sources/osram/extracted")
    parser.add_argument("--output", help="Optional JSON report path")
    args = parser.parse_args()

    lambertian_design, manufacturer_design, provenance = _load_design(
        Path(args.design), Path(args.asset_root)
    )
    lambertian = simulate_design(lambertian_design)
    manufacturer = simulate_design(manufacturer_design)

    report = {
        "comparison": {
            "changed_variable": "angular_model_only",
            "lambertian_model": "generalized_lambertian",
            "manufacturer_model": "manufacturer_ies",
            "manufacturer_ies_orientation_convention": {
                "optical_axis": "local -Z",
                "type_c_c0_reference": "local +X",
                "demo_orientation_matrix": IDENTITY_ORIENTATION,
            },
            "same_geometry": True,
            "same_radiant_power": True,
            "same_manufacturer_spd": True,
            "same_visibility_model": True,
        },
        "provenance": provenance,
        "ppfd_umol_m2_s": {
            "lambertian": _metrics(lambertian["ppfd"]),
            "manufacturer_ies": _metrics(manufacturer["ppfd"]),
            "difference": _difference(lambertian["ppfd"], manufacturer["ppfd"]),
        },
        "far_red_700_750_umol_m2_s": {
            "lambertian": _metrics(lambertian["far_red"]),
            "manufacturer_ies": _metrics(manufacturer["far_red"]),
            "difference": _difference(lambertian["far_red"], manufacturer["far_red"]),
        },
        "grid_shape": list(lambertian["ppfd"].shape),
        "blocked_ray_count": {
            "lambertian": int(lambertian["blocked_ray_count"]),
            "manufacturer_ies": int(manufacturer["blocked_ray_count"]),
        },
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
