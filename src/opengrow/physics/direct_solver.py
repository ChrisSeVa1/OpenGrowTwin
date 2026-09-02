"""Small deterministic direct-light solver for the MVP."""

from __future__ import annotations

import numpy as np

from .photons import irradiance_to_photon_flux


def _unit_vector(value, name: str):
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or np.any(~np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite three-vector")
    length = np.linalg.norm(vector)
    if length == 0:
        raise ValueError(f"{name} must be non-zero")
    return vector / length


def sensor_grid(
    width_m: float,
    depth_m: float,
    nx: int,
    ny: int,
    z_m: float = 0.0,
    center_m=None,
    u_axis=None,
    v_axis=None,
):
    if width_m <= 0 or depth_m <= 0 or nx < 1 or ny < 1:
        raise ValueError("grid dimensions must be positive")
    center = np.asarray(center_m if center_m is not None else [0.0, 0.0, z_m], dtype=float)
    if center.shape != (3,) or np.any(~np.isfinite(center)):
        raise ValueError("grid center_m must be a finite three-vector")
    u = _unit_vector(u_axis if u_axis is not None else [1.0, 0.0, 0.0], "grid u_axis")
    v = _unit_vector(v_axis if v_axis is not None else [0.0, 1.0, 0.0], "grid v_axis")
    if abs(float(np.dot(u, v))) > 1e-6:
        raise ValueError("grid u_axis and v_axis must be orthogonal")
    xs = np.linspace(-width_m / 2, width_m / 2, nx)
    ys = np.linspace(-depth_m / 2, depth_m / 2, ny)
    xx, yy = np.meshgrid(xs, ys)
    return center + xx[..., None] * u + yy[..., None] * v


def point_source_irradiance(
    grid,
    position_m,
    radiant_power_w: float,
    beam_exponent: float = 1.0,
    direction=None,
    receiver_normal=None,
):
    """Direct irradiance from an oriented point emitter onto a planar receiver.

    The normalized angular model is I(theta)=(m+1)P/(2π) cos(theta)^m.
    """
    if radiant_power_w < 0 or beam_exponent < 0:
        raise ValueError("radiant power and beam exponent must be non-negative")
    emitter_direction = _unit_vector(
        direction if direction is not None else [0.0, 0.0, -1.0], "emitter direction"
    )
    normal = _unit_vector(
        receiver_normal if receiver_normal is not None else [0.0, 0.0, 1.0], "receiver normal"
    )
    delta = np.asarray(grid, dtype=float) - np.asarray(position_m, dtype=float)
    distance = np.linalg.norm(delta, axis=-1)
    if np.any(distance == 0):
        raise ValueError("source cannot coincide with a sensor")
    ray_direction = delta / distance[..., None]
    cos_theta = np.clip(np.sum(ray_direction * emitter_direction, axis=-1), 0.0, 1.0)
    cos_incidence = np.clip(np.sum(-ray_direction * normal, axis=-1), 0.0, 1.0)
    intensity = (beam_exponent + 1.0) * radiant_power_w / (2.0 * np.pi)
    return intensity * np.power(cos_theta, beam_exponent) * cos_incidence / np.square(distance)


def simulate_design(design: dict):
    grid_cfg = design["grid"]
    grid = sensor_grid(
        grid_cfg["width_m"], grid_cfg["depth_m"], grid_cfg["nx"], grid_cfg["ny"],
        grid_cfg.get("z_m", 0.0), grid_cfg.get("center_m"),
        grid_cfg.get("u_axis"), grid_cfg.get("v_axis"),
    )
    receiver_normal = np.cross(
        _unit_vector(grid_cfg.get("u_axis", [1.0, 0.0, 0.0]), "grid u_axis"),
        _unit_vector(grid_cfg.get("v_axis", [0.0, 1.0, 0.0]), "grid v_axis"),
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
                emitter.get("direction"),
                receiver_normal,
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
