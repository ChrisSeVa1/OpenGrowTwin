"""Small deterministic direct-light solver for the MVP."""

from __future__ import annotations

import numpy as np

from .photometry import AngularDistribution
from .photons import irradiance_to_photon_flux
from .spectrum import TabulatedSpectrum
from .visibility import visibility_mask


def _unit_vector(value, name: str):
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or np.any(~np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite three-vector")
    length = np.linalg.norm(vector)
    if length == 0:
        raise ValueError(f"{name} must be non-zero")
    return vector / length


def _orientation_matrix(value):
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (3, 3) or np.any(~np.isfinite(matrix)):
        raise ValueError("emitter orientation_matrix must be a finite 3x3 matrix")
    gram = matrix.T @ matrix
    if not np.allclose(gram, np.eye(3), atol=1e-6):
        raise ValueError("emitter orientation_matrix must be orthonormal")
    if np.linalg.det(matrix) <= 0:
        raise ValueError("emitter orientation_matrix must be right-handed")
    return matrix


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
    """Direct irradiance from an oriented generalized-Lambertian point emitter."""
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


def manufacturer_ies_irradiance(
    grid,
    position_m,
    radiant_power_w: float,
    angular_distribution: AngularDistribution,
    orientation_matrix,
    receiver_normal=None,
):
    """Direct irradiance using normalized LM-63 Type-C manufacturer photometry.

    ``orientation_matrix`` maps emitter-local XYZ axes into world space. OpenGrowTwin
    defines emitter-local ``-Z`` as the optical axis and local ``+X`` as the Type-C
    C=0 reference direction. The full azimuthal orientation is therefore preserved.
    """
    if radiant_power_w < 0 or not np.isfinite(radiant_power_w):
        raise ValueError("radiant power must be finite and non-negative")
    if not isinstance(angular_distribution, AngularDistribution):
        raise TypeError("angular_distribution must be an AngularDistribution")
    local_to_world = _orientation_matrix(orientation_matrix)
    world_to_local = local_to_world.T
    normal = _unit_vector(
        receiver_normal if receiver_normal is not None else [0.0, 0.0, 1.0], "receiver normal"
    )

    delta = np.asarray(grid, dtype=float) - np.asarray(position_m, dtype=float)
    distance = np.linalg.norm(delta, axis=-1)
    if np.any(distance == 0):
        raise ValueError("source cannot coincide with a sensor")
    ray_world = delta / distance[..., None]
    ray_local = np.einsum("ij,...j->...i", world_to_local, ray_world)

    cos_theta = np.clip(-ray_local[..., 2], -1.0, 1.0)
    theta_deg = np.degrees(np.arccos(cos_theta))
    phi_deg = np.degrees(np.arctan2(ray_local[..., 1], ray_local[..., 0]))
    phi_deg = np.mod(phi_deg, 360.0)

    normalized = angular_distribution.normalized()
    p_sr_inv = normalized.sample(theta_deg, phi_deg)
    cos_incidence = np.clip(np.sum(-ray_world * normal, axis=-1), 0.0, 1.0)
    return radiant_power_w * p_sr_inv * cos_incidence / np.square(distance)


def _channel_photon_coefficients(channel: dict):
    spectrum = channel.get("spectrum")
    if isinstance(spectrum, TabulatedSpectrum):
        return {
            "total": spectrum.photon_flux_per_watt_umol_s(),
            "par": spectrum.photon_flux_per_watt_umol_s(400.0, 700.0),
            "far_red_700_750": spectrum.photon_flux_per_watt_umol_s(700.0, 750.0),
        }
    wavelength = float(channel["wavelength_nm"])
    one = float(irradiance_to_photon_flux(1.0, wavelength))
    return {
        "total": one,
        "par": one if 400.0 <= wavelength <= 700.0 else 0.0,
        "far_red_700_750": one if 700.0 < wavelength <= 750.0 else 0.0,
    }


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
    par_fields = []
    far_red_fields = []
    visibility_fields = []
    occlusion_diagnostics = []
    occluders = design.get("occluders", [])
    for channel in channels:
        field = np.zeros(grid.shape[:-1], dtype=float)
        for emitter in channel["emitters"]:
            visible = visibility_mask(grid, emitter["position_m"], occluders)
            angular_model = emitter.get("angular_model", "generalized_lambertian")
            if angular_model == "generalized_lambertian":
                contribution = point_source_irradiance(
                    grid,
                    emitter["position_m"],
                    emitter["radiant_power_w"],
                    emitter.get("beam_exponent", 1.0),
                    emitter.get("direction"),
                    receiver_normal,
                )
            elif angular_model == "manufacturer_ies":
                contribution = manufacturer_ies_irradiance(
                    grid,
                    emitter["position_m"],
                    emitter["radiant_power_w"],
                    emitter["angular_distribution"],
                    emitter["orientation_matrix"],
                    receiver_normal,
                )
            else:
                raise ValueError(f"unsupported angular model {angular_model!r}")
            field += contribution * visible
            visibility_fields.append(visible)
            blocked = int(visible.size - np.count_nonzero(visible))
            occlusion_diagnostics.append({
                "source_path": emitter.get("source_path"),
                "channel": channel["id"],
                "blocked_ray_count": blocked,
                "total_ray_count": int(visible.size),
                "blocked_fraction": blocked / int(visible.size),
            })
        spectral_irradiance.append(field)
        coefficients = _channel_photon_coefficients(channel)
        photon_fields.append(field * coefficients["total"])
        par_fields.append(field * coefficients["par"])
        far_red_fields.append(field * coefficients["far_red_700_750"])
    irradiance = np.stack(spectral_irradiance)
    photons = np.stack(photon_fields)
    ppfd = np.stack(par_fields).sum(axis=0)
    far_red = np.stack(far_red_fields).sum(axis=0)
    return {
        "grid": grid,
        "wavelengths_nm": wavelengths,
        "spectral_irradiance": irradiance,
        "band_ppfd": photons,
        "ppfd": ppfd,
        "far_red": far_red,
        "far_red_band_nm": [700.0, 750.0],
        "emitter_visibility": np.stack(visibility_fields),
        "occlusion_diagnostics": occlusion_diagnostics,
        "blocked_ray_count": sum(item["blocked_ray_count"] for item in occlusion_diagnostics),
        "total_ray_count": sum(item["total_ray_count"] for item in occlusion_diagnostics),
    }
