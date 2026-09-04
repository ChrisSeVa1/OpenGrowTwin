#!/usr/bin/env python3
"""Validate an LM-63 angular field and optional tabulated SPD.

This tool deliberately consumes manufacturer assets from user-supplied paths so
OpenGrowTwin can preserve provenance without redistributing third-party rayfiles.
"""

from __future__ import annotations

import argparse
import json

from opengrow.physics.photometry import load_ies
from opengrow.physics.spectrum import load_spectrum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ies", required=True, help="Path to manufacturer LM-63 IES file")
    parser.add_argument("--radiant-flux-w", required=True, type=float)
    parser.add_argument("--spectrum", help="Path to tabulated wavelength/relative-power spectrum")
    parser.add_argument("--part-number")
    args = parser.parse_args()

    profile = load_ies(args.ies)
    integral = profile.solid_angle_integral()
    report = {
        "part_number": args.part_number,
        "ies": {
            "source": profile.source,
            "format": profile.metadata.format_line if profile.metadata else None,
            "manufacturer": profile.metadata.keywords.get("MANUFAC") if profile.metadata else None,
            "luminaire": profile.metadata.keywords.get("LUMINAIRE") if profile.metadata else None,
            "vertical_samples": int(len(profile.vertical_angles_deg)),
            "horizontal_samples": int(len(profile.horizontal_angles_deg)),
            "vertical_range_deg": [float(profile.vertical_angles_deg[0]), float(profile.vertical_angles_deg[-1])],
            "horizontal_range_deg": [float(profile.horizontal_angles_deg[0]), float(profile.horizontal_angles_deg[-1])],
            "solid_angle_integral_raw": integral,
            "authoritative_radiant_flux_w": args.radiant_flux_w,
            "relative_integral_error": (integral - args.radiant_flux_w) / args.radiant_flux_w,
            "normalized_integral": profile.normalized().solid_angle_integral(),
        },
    }

    if args.spectrum:
        spectrum = load_spectrum(args.spectrum)
        report["spectrum"] = {
            "source": spectrum.source,
            "provenance_kind": spectrum.provenance_kind,
            "sample_count": int(len(spectrum.wavelengths_nm)),
            "range_nm": [float(spectrum.wavelengths_nm[0]), float(spectrum.wavelengths_nm[-1])],
            "peak_nm": spectrum.peak_wavelength_nm,
            "photon_flux_per_radiant_w_umol_s": spectrum.photon_flux_per_watt_umol_s(),
            "photon_flux_at_authoritative_flux_umol_s": (
                spectrum.photon_flux_per_watt_umol_s() * args.radiant_flux_w
            ),
            "par_400_700_photon_flux_at_authoritative_flux_umol_s": (
                spectrum.photon_flux_per_watt_umol_s(400.0, 700.0) * args.radiant_flux_w
            ),
            "far_red_700_750_photon_flux_at_authoritative_flux_umol_s": (
                spectrum.photon_flux_per_watt_umol_s(700.0, 750.0) * args.radiant_flux_w
            ),
        }

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
