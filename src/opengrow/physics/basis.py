"""Per-channel basis maps for fast linear reconstruction."""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from .direct_solver import simulate_design


def design_at_height(design: dict, height_m: float) -> dict:
    """Return a copy with every emitter placed at the requested absolute z."""
    if height_m <= design["grid"].get("z_m", 0.0):
        raise ValueError("fixture height must be above the sensor plane")
    candidate = deepcopy(design)
    for channel in candidate["channels"]:
        for emitter in channel["emitters"]:
            emitter["position_m"][2] = float(height_m)
    return candidate


def channel_basis(design: dict) -> dict:
    """Compute photon fields per watt of total channel radiant power."""
    result = simulate_design(design)
    basis = []
    channel_ids = []
    wavelengths = []
    for index, channel in enumerate(design["channels"]):
        total_power = sum(float(emitter["radiant_power_w"]) for emitter in channel["emitters"])
        if total_power <= 0:
            raise ValueError(f"channel {channel['id']} needs positive radiant power to form a basis")
        basis.append(result["band_ppfd"][index] / total_power)
        channel_ids.append(channel["id"])
        wavelengths.append(float(channel["wavelength_nm"]))
    return {
        "channel_ids": channel_ids,
        "wavelengths_nm": np.asarray(wavelengths),
        "photon_per_radiant_w": np.stack(basis),
    }


def reconstruct(basis: dict, channel_radiant_power_w) -> dict:
    """Reconstruct PAR and far-red fields from cached bases."""
    powers = np.asarray(channel_radiant_power_w, dtype=float)
    fields = basis["photon_per_radiant_w"] * powers[:, None, None]
    wavelengths = basis["wavelengths_nm"]
    par = (wavelengths >= 400.0) & (wavelengths <= 700.0)
    far_red = (wavelengths > 700.0) & (wavelengths <= 800.0)
    return {
        "band_ppfd": fields,
        "ppfd": fields[par].sum(axis=0),
        "far_red": fields[far_red].sum(axis=0),
    }
