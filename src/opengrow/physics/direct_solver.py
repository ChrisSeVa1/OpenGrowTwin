"""Small deterministic direct-light solver for the MVP."""

from __future__ import annotations

import numpy as np

from .photons import irradiance_to_photon_flux


def sensor_grid(width_m: float, depth_m: float, nx: int, ny: int, z_m: float = 0.0):
    if width_m <= 0 or depth_m <= 0 or nx < 1 or ny < 1:
        raise ValueError("grid dimensions must be positive")
    xs = np.linspace(-width_m / 2, width_m / 2, nx)
    ys = np.linspace(-depth_m / 2, depth_m / 2, ny)
    xx, yy = np.meshgrid(xs, ys)
    return np.stack((xx, yy, np.full_like(xx, z_m)), axis=-1)


def point_source_irradiance(grid, position_m, radiant_power_w: float, beam_exponent: float = 1.0):
    """Direct irradiance from a downward-facing point emitter.

    The normalized angular model is I(theta)=(m+1)P/(2π) cos(theta)^m.
    """
    if radiant_power_w < 0 or beam_exponent < 0:
        raise ValueError("radiant power and beam exponent must be non-negative")
    delta = np.asarray(grid, dtype=float) - np.asarray(position_m, dtype=float)
    distance = np.linalg.norm(delta, axis=-1)
    if np.any(distance == 0):
        raise ValueError("source cannot coincide with a sensor")
    cos_theta = np.clip(-delta[..., 2] / distance, 0.0, 1.0)
    intensity = (beam_exponent + 1.0) * radiant_power_w / (2.0 * np.pi)
    return intensity * np.power(cos_theta, beam_exponent + 1.0) / np.square(distance)


def simulate_design(design: dict):
    grid_cfg = design["grid"]
    grid = sensor_grid(
        grid_cfg["width_m"], grid_cfg["depth_m"], grid_cfg["nx"], grid_cfg["ny"], grid_cfg.get("z_m", 0.0)
    )
    channels = design["channels"]
    wavelengths = np.array([channel["wavelength_nm"] for channel in channels], dtype=float)
    spectral_irradiance = []
    photon_fields = []
    for channel in channels:
        field = np.zeros(grid.shape[:-1], dtype=float)
        for emitter in channel["emitters"]:
            field += point_source_irradiance(
                grid,
                emitter["position_m"],
                emitter["radiant_power_w"],
                emitter.get("beam_exponent", 1.0),
            )
        spectral_irradiance.append(field)
        photon_fields.append(irradiance_to_photon_flux(field, channel["wavelength_nm"]))
    irradiance = np.stack(spectral_irradiance)
    photons = np.stack(photon_fields)
    par_mask = (wavelengths >= 400.0) & (wavelengths <= 700.0)
    far_red_mask = (wavelengths > 700.0) & (wavelengths <= 800.0)
    ppfd = photons[par_mask].sum(axis=0)
    far_red = photons[far_red_mask].sum(axis=0)
    return {"grid": grid, "wavelengths_nm": wavelengths, "spectral_irradiance": irradiance, "band_ppfd": photons, "ppfd": ppfd, "far_red": far_red}
