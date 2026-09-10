"""Manufacturer angular-photometry support for deterministic light transport.

The parser intentionally treats LM-63 intensity samples as an angular field with
caller-supplied radiometric semantics.  OpenGrowTwin normalizes that field over
solid angle before applying an authoritative radiant-flux value from provenance-
checked LED metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


def _trapezoid(values, coordinates, axis=-1):
    """Compatibility wrapper for NumPy versions with/without ``trapezoid``."""
    fn = getattr(np, "trapezoid", np.trapz)
    return fn(values, coordinates, axis=axis)


@dataclass(frozen=True)
class IESMetadata:
    format_line: str
    keywords: dict[str, str]
    number_of_lamps: int
    lumens_per_lamp: float
    intensity_multiplier: float
    photometric_type: int
    units_type: int
    width: float
    length: float
    height: float
    ballast_factor: float
    future_use: float
    input_watts: float


@dataclass(frozen=True)
class AngularDistribution:
    """Tabulated Type-C angular intensity distribution.

    ``intensity`` has shape ``(n_horizontal, n_vertical)``.  Angles are stored in
    degrees exactly as supplied by the source file.  Use :meth:`normalized` before
    applying a physical radiant-flux normalization.
    """

    vertical_angles_deg: np.ndarray
    horizontal_angles_deg: np.ndarray
    intensity: np.ndarray
    metadata: IESMetadata | None = None
    source: str | None = None

    def __post_init__(self):
        vertical = np.asarray(self.vertical_angles_deg, dtype=float)
        horizontal = np.asarray(self.horizontal_angles_deg, dtype=float)
        intensity = np.asarray(self.intensity, dtype=float)
        if vertical.ndim != 1 or horizontal.ndim != 1:
            raise ValueError("angular coordinates must be one-dimensional")
        if len(vertical) < 2 or len(horizontal) < 1:
            raise ValueError("angular distribution requires at least two vertical samples")
        if intensity.shape != (len(horizontal), len(vertical)):
            raise ValueError("intensity shape must be (horizontal, vertical)")
        if np.any(~np.isfinite(vertical)) or np.any(~np.isfinite(horizontal)):
            raise ValueError("angles must be finite")
        if np.any(~np.isfinite(intensity)) or np.any(intensity < 0):
            raise ValueError("intensity samples must be finite and non-negative")
        if np.any(np.diff(vertical) <= 0) or np.any(np.diff(horizontal) <= 0):
            raise ValueError("angles must be strictly increasing")
        if vertical[0] < 0 or vertical[-1] > 180:
            raise ValueError("vertical angles must lie within 0..180 degrees")
        if horizontal[0] < 0 or horizontal[-1] > 360:
            raise ValueError("horizontal angles must lie within 0..360 degrees")
        object.__setattr__(self, "vertical_angles_deg", vertical)
        object.__setattr__(self, "horizontal_angles_deg", horizontal)
        object.__setattr__(self, "intensity", intensity)

    def _periodic_grid(self):
        """Return horizontal grid/intensity suitable for periodic interpolation."""
        phi = self.horizontal_angles_deg
        values = self.intensity
        if len(phi) == 1:
            return np.array([0.0, 360.0]), np.vstack([values[0], values[0]])
        if np.isclose(phi[0], 0.0) and np.isclose(phi[-1], 360.0):
            return phi, values
        if np.isclose(phi[0], 0.0):
            return np.concatenate([phi, [360.0]]), np.vstack([values, values[0]])
        raise ValueError("periodic interpolation requires a horizontal grid beginning at 0 degrees")

    def solid_angle_integral(self) -> float:
        """Numerically integrate the tabulated field over solid angle."""
        theta = np.deg2rad(self.vertical_angles_deg)
        weighted = self.intensity * np.sin(theta)[None, :]
        theta_integrals = _trapezoid(weighted, theta, axis=1)

        phi = self.horizontal_angles_deg
        if len(phi) == 1:
            integral = float(theta_integrals[0] * 2.0 * np.pi)
        else:
            if np.isclose(phi[0], 0.0) and np.isclose(phi[-1], 360.0):
                phi_rad = np.deg2rad(phi)
                integral = float(_trapezoid(theta_integrals, phi_rad))
            elif np.isclose(phi[0], 0.0):
                phi_ext = np.concatenate([phi, [360.0]])
                vals_ext = np.concatenate([theta_integrals, [theta_integrals[0]]])
                integral = float(_trapezoid(vals_ext, np.deg2rad(phi_ext)))
            else:
                raise ValueError("solid-angle integration requires horizontal coverage from 0 degrees")
        if not np.isfinite(integral) or integral <= 0:
            raise ValueError("angular distribution has zero or invalid solid-angle integral")
        return integral

    def normalized(self) -> "AngularDistribution":
        """Return a distribution whose solid-angle integral equals one."""
        return AngularDistribution(
            self.vertical_angles_deg.copy(),
            self.horizontal_angles_deg.copy(),
            self.intensity / self.solid_angle_integral(),
            metadata=self.metadata,
            source=self.source,
        )

    def sample(self, theta_deg, phi_deg):
        """Bilinearly interpolate the angular field.

        ``phi_deg`` is periodic.  Values outside the tabulated vertical range are
        zero, which is appropriate for a source profile whose support is explicitly
        bounded by the manufacturer table.
        """
        theta = np.asarray(theta_deg, dtype=float)
        phi = np.asarray(phi_deg, dtype=float)
        theta, phi = np.broadcast_arrays(theta, phi)
        out = np.zeros(theta.shape, dtype=float)
        valid = np.isfinite(theta) & np.isfinite(phi)
        valid &= (theta >= self.vertical_angles_deg[0]) & (theta <= self.vertical_angles_deg[-1])
        if not np.any(valid):
            return float(out) if out.ndim == 0 else out

        phi_grid, field = self._periodic_grid()
        phi_wrapped = np.mod(phi[valid], 360.0)
        theta_valid = theta[valid]

        hi_t = np.searchsorted(self.vertical_angles_deg, theta_valid, side="right")
        hi_t = np.clip(hi_t, 1, len(self.vertical_angles_deg) - 1)
        lo_t = hi_t - 1
        t0 = self.vertical_angles_deg[lo_t]
        t1 = self.vertical_angles_deg[hi_t]
        wt = np.divide(theta_valid - t0, t1 - t0, out=np.zeros_like(theta_valid), where=t1 != t0)

        hi_p = np.searchsorted(phi_grid, phi_wrapped, side="right")
        hi_p = np.clip(hi_p, 1, len(phi_grid) - 1)
        lo_p = hi_p - 1
        p0 = phi_grid[lo_p]
        p1 = phi_grid[hi_p]
        wp = np.divide(phi_wrapped - p0, p1 - p0, out=np.zeros_like(phi_wrapped), where=p1 != p0)

        f00 = field[lo_p, lo_t]
        f01 = field[lo_p, hi_t]
        f10 = field[hi_p, lo_t]
        f11 = field[hi_p, hi_t]
        lower = f00 * (1.0 - wt) + f01 * wt
        upper = f10 * (1.0 - wt) + f11 * wt
        out[valid] = lower * (1.0 - wp) + upper * wp
        return float(out) if out.ndim == 0 else out


def _numeric_tokens(lines: Iterable[str]) -> list[float]:
    tokens: list[float] = []
    for line in lines:
        for token in line.replace(",", " ").split():
            try:
                tokens.append(float(token))
            except ValueError as exc:
                raise ValueError(f"invalid numeric token in LM-63 payload: {token!r}") from exc
    return tokens


def parse_ies_text(text: str, source: str | None = None) -> AngularDistribution:
    """Parse an LM-63 ``TILT=NONE`` Type-C IES profile.

    The function does not assume candela, watts/steradian, or photon units.  It
    preserves the numeric field and metadata so callers can apply provenance-aware
    semantics after validation.
    """
    lines = [line.strip() for line in text.replace("\ufeff", "").splitlines() if line.strip()]
    if not lines:
        raise ValueError("empty IES document")

    tilt_index = next((i for i, line in enumerate(lines) if line.upper().startswith("TILT=")), None)
    if tilt_index is None:
        raise ValueError("IES document is missing TILT declaration")
    if lines[tilt_index].upper() != "TILT=NONE":
        raise ValueError("only TILT=NONE IES profiles are supported")

    keywords: dict[str, str] = {}
    for line in lines[1:tilt_index]:
        if line.startswith("[") and "]" in line:
            end = line.index("]")
            keywords[line[1:end].strip()] = line[end + 1 :].strip()

    values = _numeric_tokens(lines[tilt_index + 1 :])
    if len(values) < 13:
        raise ValueError("IES numeric payload is incomplete")

    n_lamps = int(values[0])
    lumens_per_lamp = values[1]
    multiplier = values[2]
    n_vertical = int(values[3])
    n_horizontal = int(values[4])
    photometric_type = int(values[5])
    units_type = int(values[6])
    if n_lamps < 1 or n_vertical < 2 or n_horizontal < 1:
        raise ValueError("invalid LM-63 lamp or angle counts")
    if photometric_type != 1:
        raise ValueError("only LM-63 Type-C photometry is supported")
    if multiplier < 0:
        raise ValueError("intensity multiplier must be non-negative")

    width, length, height = values[7:10]
    ballast_factor, future_use, input_watts = values[10:13]
    offset = 13
    expected = offset + n_vertical + n_horizontal + n_vertical * n_horizontal
    if len(values) < expected:
        raise ValueError("IES numeric payload does not contain the declared angle/intensity samples")

    vertical = np.asarray(values[offset : offset + n_vertical], dtype=float)
    offset += n_vertical
    horizontal = np.asarray(values[offset : offset + n_horizontal], dtype=float)
    offset += n_horizontal
    intensity = np.asarray(values[offset : offset + n_vertical * n_horizontal], dtype=float)
    intensity = intensity.reshape(n_horizontal, n_vertical) * multiplier

    metadata = IESMetadata(
        format_line=lines[0],
        keywords=keywords,
        number_of_lamps=n_lamps,
        lumens_per_lamp=lumens_per_lamp,
        intensity_multiplier=multiplier,
        photometric_type=photometric_type,
        units_type=units_type,
        width=width,
        length=length,
        height=height,
        ballast_factor=ballast_factor,
        future_use=future_use,
        input_watts=input_watts,
    )
    return AngularDistribution(vertical, horizontal, intensity, metadata=metadata, source=source)


def load_ies(path) -> AngularDistribution:
    path = Path(path)
    return parse_ies_text(path.read_text(encoding="utf-8-sig"), source=str(path))
