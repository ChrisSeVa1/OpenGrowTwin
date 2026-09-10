"""Local manufacturer-profile resolution for OpenGrowTwin.

Raw manufacturer optical assets are intentionally not distributed with this
repository. This module only defines stable product/file identifiers and loads
a user-supplied local bundle when all required files are present.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .physics.photometry import load_ies
from .physics.spectrum import load_spectrum


OSRAM_PROFILES = {
    "blue": {
        "manufacturer": "ams OSRAM",
        "family": "OSCONIQ P 3737 (2W) Batwing",
        "spectral_role": "Deep Blue",
        "part_number": "GD PUBRA1.15",
        "rayfile_revision": "2025-05-29",
        "validated_peak_wavelength_nm": 446.0,
        "ies": "GD_PUBRA1_15_20250529.ies",
        "spectrum": "GD_PUBRA1_15_20250529_spectrum.txt",
    },
    "red": {
        "manufacturer": "ams OSRAM",
        "family": "OSCONIQ P 3737 (2W) Batwing",
        "spectral_role": "Hyper Red",
        "part_number": "GH PUBRA1.25",
        "rayfile_revision": "2025-05-26",
        "validated_peak_wavelength_nm": 680.0,
        "ies": "GH_PUBRA1_25_20250526.ies",
        "spectrum": "GH_PUBRA1_25_20250526_spectrum.txt",
    },
    "far_red": {
        "manufacturer": "ams OSRAM",
        "family": "OSCONIQ P 3737 (2W) Batwing",
        "spectral_role": "Far Red",
        "part_number": "GF PUBRA1.25",
        "rayfile_revision": "2025-06-03",
        "validated_peak_wavelength_nm": 742.0,
        "ies": "GF_PUBRA1_25_20250603.ies",
        "spectrum": "GF_PUBRA1_25_20250603_spectrum.txt",
    },
}


def default_asset_root() -> Path:
    """Return the conventional gitignored local manufacturer-asset directory."""
    return Path(__file__).resolve().parents[2] / "sources" / "osram" / "extracted"


def _resolved_paths(asset_root=None) -> dict[str, dict[str, Path]]:
    root = Path(asset_root) if asset_root is not None else default_asset_root()
    return {
        channel_id: {
            "ies": root / profile["ies"],
            "spectrum": root / profile["spectrum"],
        }
        for channel_id, profile in OSRAM_PROFILES.items()
    }


def manufacturer_bundle_available(asset_root=None) -> bool:
    """Return True only when the complete three-channel local bundle is present."""
    return all(
        path.is_file()
        for channel_paths in _resolved_paths(asset_root).values()
        for path in channel_paths.values()
    )


def manufacturer_ies_by_channel(asset_root=None, required: bool = False) -> dict[str, str]:
    """Return channel-to-IES paths for RTX without redistributing vendor files."""
    paths = _resolved_paths(asset_root)
    missing = [
        str(channel_paths["ies"])
        for channel_paths in paths.values()
        if not channel_paths["ies"].is_file()
    ]
    if missing:
        if required:
            raise FileNotFoundError("missing manufacturer IES assets: " + ", ".join(missing))
        return {}
    return {channel_id: str(channel_paths["ies"]) for channel_id, channel_paths in paths.items()}


def apply_manufacturer_profiles(design: dict, asset_root=None, required: bool = False) -> dict:
    """Return a solver design enriched with local OSRAM IES and tabulated SPD.

    When ``required`` is False and the complete local bundle is absent, a deep
    copy of the input design is returned unchanged. This preserves the public
    repository's generic Lambertian fallback while allowing a local workstation
    to use user-supplied manufacturer assets automatically.
    """
    configured = deepcopy(design)
    paths = _resolved_paths(asset_root)
    missing = [
        str(path)
        for channel_paths in paths.values()
        for path in channel_paths.values()
        if not path.is_file()
    ]
    if missing:
        if required:
            raise FileNotFoundError("missing manufacturer optical assets: " + ", ".join(missing))
        return configured

    unknown = {str(channel["id"]) for channel in configured["channels"]} - set(OSRAM_PROFILES)
    if unknown:
        if required:
            raise ValueError(f"no manufacturer profile mapping for channels: {sorted(unknown)}")
        return configured

    loaded = {}
    for channel_id, channel_paths in paths.items():
        loaded[channel_id] = {
            "angular_distribution": load_ies(channel_paths["ies"]),
            "spectrum": load_spectrum(channel_paths["spectrum"]),
        }

    for channel in configured["channels"]:
        channel_id = str(channel["id"])
        profile = loaded[channel_id]
        metadata = OSRAM_PROFILES[channel_id]
        channel["spectrum"] = profile["spectrum"]
        channel["manufacturer_profile"] = {
            "manufacturer": metadata["manufacturer"],
            "family": metadata["family"],
            "spectral_role": metadata["spectral_role"],
            "part_number": metadata["part_number"],
            "rayfile_revision": metadata["rayfile_revision"],
            "validated_peak_wavelength_nm": metadata["validated_peak_wavelength_nm"],
            "ies_filename": metadata["ies"],
            "spectrum_filename": metadata["spectrum"],
            "spectrum_provenance": "manufacturer_tabulated_relative_spd",
        }
        for emitter in channel["emitters"]:
            if "orientation_matrix" not in emitter:
                raise ValueError(
                    f"{emitter.get('source_path', channel_id)}: manufacturer IES requires orientation_matrix"
                )
            emitter["angular_model"] = "manufacturer_ies"
            emitter["angular_distribution"] = profile["angular_distribution"]

    return configured
