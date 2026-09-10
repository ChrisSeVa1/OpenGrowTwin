"""Radiometric-to-photon-domain conversions using exact SI constants."""

from __future__ import annotations

import numpy as np

PLANCK_CONSTANT_J_S = 6.62607015e-34
SPEED_OF_LIGHT_M_S = 299_792_458.0
AVOGADRO_CONSTANT_MOL_1 = 6.02214076e23


def irradiance_to_photon_flux(irradiance_w_m2, wavelength_nm):
    """Convert monochromatic irradiance to µmol m⁻² s⁻¹.

    Inputs may be scalars or broadcast-compatible NumPy arrays.
    """
    irradiance = np.asarray(irradiance_w_m2, dtype=float)
    wavelength = np.asarray(wavelength_nm, dtype=float)
    if np.any(irradiance < 0) or np.any(wavelength <= 0):
        raise ValueError("irradiance must be non-negative and wavelength positive")
    factor = wavelength * 1e-9 / (
        PLANCK_CONSTANT_J_S * SPEED_OF_LIGHT_M_S * AVOGADRO_CONSTANT_MOL_1
    ) * 1e6
    value = irradiance * factor
    return float(value) if value.ndim == 0 else value


def dli_from_ppfd(ppfd_umol_m2_s, photoperiod_h: float):
    """Convert PPFD and photoperiod to mol m⁻² day⁻¹."""
    ppfd = np.asarray(ppfd_umol_m2_s, dtype=float)
    if np.any(ppfd < 0) or photoperiod_h < 0:
        raise ValueError("PPFD and photoperiod must be non-negative")
    value = ppfd * 0.0036 * photoperiod_h
    return float(value) if value.ndim == 0 else value
