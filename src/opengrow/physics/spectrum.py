"""Tabulated spectral-distribution support for OpenGrowTwin."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .photons import irradiance_to_photon_flux


def _trapezoid(values, coordinates, axis=-1):
    fn = getattr(np, "trapezoid", np.trapz)
    return fn(values, coordinates, axis=axis)


@dataclass(frozen=True)
class TabulatedSpectrum:
    """Relative spectral distribution tabulated against wavelength.

    ``relative_power`` is deliberately unitless.  Use :meth:`normalized_density`
    to obtain a spectral density whose wavelength integral is one, then multiply
    by an authoritative total radiant flux.
    """

    wavelengths_nm: np.ndarray
    relative_power: np.ndarray
    source: str | None = None
    provenance_kind: str = "manufacturer_tabulated_relative_spd"

    def __post_init__(self):
        wavelengths = np.asarray(self.wavelengths_nm, dtype=float)
        power = np.asarray(self.relative_power, dtype=float)
        if wavelengths.ndim != 1 or power.ndim != 1 or wavelengths.shape != power.shape:
            raise ValueError("wavelengths and relative power must be matching one-dimensional arrays")
        if len(wavelengths) < 2:
            raise ValueError("spectrum requires at least two wavelength samples")
        if np.any(~np.isfinite(wavelengths)) or np.any(~np.isfinite(power)):
            raise ValueError("spectrum samples must be finite")
        if np.any(wavelengths <= 0) or np.any(np.diff(wavelengths) <= 0):
            raise ValueError("wavelengths must be positive and strictly increasing")
        if np.any(power < 0):
            raise ValueError("relative spectral power must be non-negative")
        if not np.any(power > 0):
            raise ValueError("spectrum cannot be identically zero")
        object.__setattr__(self, "wavelengths_nm", wavelengths)
        object.__setattr__(self, "relative_power", power)

    @property
    def peak_wavelength_nm(self) -> float:
        return float(self.wavelengths_nm[int(np.argmax(self.relative_power))])

    def normalized_density(self) -> np.ndarray:
        """Return W/W/nm-style relative density integrating to one over nm."""
        area = float(_trapezoid(self.relative_power, self.wavelengths_nm))
        if not np.isfinite(area) or area <= 0:
            raise ValueError("spectrum has zero or invalid wavelength integral")
        return self.relative_power / area

    def radiant_spectral_density(self, radiant_flux_w: float) -> np.ndarray:
        """Return spectral radiant flux density in W/nm."""
        if radiant_flux_w < 0 or not np.isfinite(radiant_flux_w):
            raise ValueError("radiant flux must be finite and non-negative")
        return self.normalized_density() * radiant_flux_w

    def photon_flux_per_watt_umol_s(self, minimum_nm=None, maximum_nm=None) -> float:
        """Integrate emitted photon flux for one watt of total radiant flux."""
        mask = np.ones_like(self.wavelengths_nm, dtype=bool)
        if minimum_nm is not None:
            mask &= self.wavelengths_nm >= float(minimum_nm)
        if maximum_nm is not None:
            mask &= self.wavelengths_nm <= float(maximum_nm)
        if np.count_nonzero(mask) < 2:
            return 0.0
        wavelengths = self.wavelengths_nm[mask]
        spectral_w_per_nm = self.normalized_density()[mask]
        spectral_photons = irradiance_to_photon_flux(spectral_w_per_nm, wavelengths)
        return float(_trapezoid(spectral_photons, wavelengths))

    def fraction_in_band(self, minimum_nm: float, maximum_nm: float) -> float:
        """Return fraction of radiant flux falling inside a wavelength interval."""
        mask = (self.wavelengths_nm >= minimum_nm) & (self.wavelengths_nm <= maximum_nm)
        if np.count_nonzero(mask) < 2:
            return 0.0
        density = self.normalized_density()
        return float(_trapezoid(density[mask], self.wavelengths_nm[mask]))


def parse_spectrum_text(
    text: str,
    source: str | None = None,
    provenance_kind: str = "manufacturer_tabulated_relative_spd",
) -> TabulatedSpectrum:
    wavelengths = []
    values = []
    for line_number, raw_line in enumerate(text.replace("\ufeff", "").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        parts = line.replace(",", " ").split()
        if len(parts) < 2:
            raise ValueError(f"invalid spectrum row at line {line_number}")
        try:
            wavelength = float(parts[0])
            value = float(parts[1])
        except ValueError as exc:
            raise ValueError(f"invalid numeric spectrum row at line {line_number}") from exc
        wavelengths.append(wavelength)
        values.append(value)
    return TabulatedSpectrum(
        np.asarray(wavelengths, dtype=float),
        np.asarray(values, dtype=float),
        source=source,
        provenance_kind=provenance_kind,
    )


def load_spectrum(path, provenance_kind: str = "manufacturer_tabulated_relative_spd") -> TabulatedSpectrum:
    path = Path(path)
    return parse_spectrum_text(
        path.read_text(encoding="utf-8-sig"),
        source=str(path),
        provenance_kind=provenance_kind,
    )
