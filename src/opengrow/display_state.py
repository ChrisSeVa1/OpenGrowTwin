"""Pure-Python display helpers for the OpenGrowTwin Kit panel.

The Kit UI should render one authoritative scientific/display state rather than
recomputing values independently in each widget. This module deliberately has
no Omniverse dependency so spectrum, legend, baseline/current selection, and
virtual-sensor behavior can be regression-tested without a GPU workstation.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np

from .physics.photons import irradiance_to_photon_flux
from .physics.spectrum import TabulatedSpectrum


DISPLAY_MODES = {"current", "baseline"}


def select_display_result(current: dict, baseline: dict | None, mode: str) -> dict:
    """Return the simulation result that the UI is currently presenting."""
    if mode not in DISPLAY_MODES:
        raise ValueError(f"unknown display mode {mode!r}")
    if mode == "baseline":
        if baseline is None:
            raise ValueError("baseline display requested before a baseline exists")
        return baseline
    return current


def ppfd_legend(result: dict) -> dict[str, float | str]:
    """Return dynamic PPFD legend limits for one displayed result."""
    field = np.asarray(result["fields"]["ppfd"], dtype=float)
    if field.size == 0 or np.any(~np.isfinite(field)):
        raise ValueError("displayed PPFD field must contain finite values")
    minimum = float(field.min())
    maximum = float(field.max())
    if maximum <= minimum:
        maximum = minimum + 1.0
    return {
        "minimum": minimum,
        "maximum": maximum,
        "unit": "µmol m⁻² s⁻¹",
    }


def optical_model_summary(design: dict) -> dict:
    """Describe the active optical model and locally resolved profiles."""
    channels = list(design.get("channels", []))
    manufacturer_channels = []
    all_emitters = []
    for channel in channels:
        emitters = list(channel.get("emitters", []))
        all_emitters.extend(emitters)
        profile = channel.get("manufacturer_profile")
        if profile is not None:
            manufacturer_channels.append(
                {
                    "channel_id": str(channel["id"]),
                    "part_number": profile.get("part_number"),
                    "ies_filename": profile.get("ies_filename"),
                    "spectrum_filename": profile.get("spectrum_filename"),
                }
            )

    manufacturer = bool(channels) and len(manufacturer_channels) == len(channels)
    manufacturer = manufacturer and bool(all_emitters) and all(
        emitter.get("angular_model") == "manufacturer_ies" for emitter in all_emitters
    )
    return {
        "mode": "manufacturer_ies_spd" if manufacturer else "generalized_lambertian",
        "label": "Manufacturer IES + SPD" if manufacturer else "Simplified / Lambertian",
        "profiles": manufacturer_channels,
    }


def spectrum_series(design: dict) -> list[dict]:
    """Prepare compact spectrum-plot data from the active scientific design.

    Manufacturer spectra are peak-normalized only for plotting; the underlying
    solver continues to use wavelength-integral normalization for radiometry.
    Monochromatic fallback channels are represented by a single nominal sample
    and explicitly labeled as such rather than pretending to be manufacturer SPD.
    """
    series = []
    for channel in design.get("channels", []):
        channel_id = str(channel["id"])
        spectrum = channel.get("spectrum")
        profile = channel.get("manufacturer_profile", {})
        if isinstance(spectrum, TabulatedSpectrum):
            relative = np.asarray(spectrum.relative_power, dtype=float)
            peak = float(relative.max())
            plot_relative = relative / peak
            series.append(
                {
                    "channel_id": channel_id,
                    "kind": "tabulated_relative_spd",
                    "part_number": profile.get("part_number"),
                    "provenance_kind": spectrum.provenance_kind,
                    "peak_wavelength_nm": spectrum.peak_wavelength_nm,
                    "wavelengths_nm": spectrum.wavelengths_nm.tolist(),
                    "relative_power": plot_relative.tolist(),
                }
            )
        else:
            wavelength = float(channel["wavelength_nm"])
            series.append(
                {
                    "channel_id": channel_id,
                    "kind": "monochromatic_fallback",
                    "part_number": None,
                    "provenance_kind": "model_nominal_wavelength",
                    "peak_wavelength_nm": wavelength,
                    "wavelengths_nm": [wavelength],
                    "relative_power": [1.0],
                }
            )
    return series


def spectrum_plot_curves(
    design: dict,
    minimum_nm: float = 380.0,
    maximum_nm: float = 800.0,
    sample_count: int = 211,
) -> dict:
    """Return aligned 0..1 spectrum curves for one combined Kit plot.

    ``omni.ui.Plot`` can efficiently update one uniformly spaced value array.
    This helper therefore resamples every active channel onto one shared wavelength
    grid. Manufacturer tabulated SPD keeps its real shape; simplified channels are
    rendered as narrow visual spikes centered on their nominal wavelength and are
    explicitly identified as model fallbacks by :func:`spectrum_series`.
    """
    if not np.isfinite(minimum_nm) or not np.isfinite(maximum_nm) or maximum_nm <= minimum_nm:
        raise ValueError("spectrum plot wavelength bounds must be finite and increasing")
    if sample_count < 2:
        raise ValueError("spectrum plot requires at least two samples")
    wavelengths = np.linspace(float(minimum_nm), float(maximum_nm), int(sample_count))
    curves = {}
    metadata = {}
    for item in spectrum_series(design):
        source_x = np.asarray(item["wavelengths_nm"], dtype=float)
        source_y = np.asarray(item["relative_power"], dtype=float)
        if item["kind"] == "tabulated_relative_spd":
            curve = np.interp(wavelengths, source_x, source_y, left=0.0, right=0.0)
        else:
            # Display-only nominal spike; solver semantics remain monochromatic.
            center = float(item["peak_wavelength_nm"])
            spacing = float(wavelengths[1] - wavelengths[0])
            sigma = max(spacing * 1.5, 1.0)
            curve = np.exp(-0.5 * np.square((wavelengths - center) / sigma))
        curves[item["channel_id"]] = curve.tolist()
        metadata[item["channel_id"]] = item
    return {
        "wavelengths_nm": wavelengths.tolist(),
        "minimum_nm": float(minimum_nm),
        "maximum_nm": float(maximum_nm),
        "curves": curves,
        "metadata": metadata,
    }


def _unit_vector(value: Iterable[float], name: str) -> np.ndarray:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or np.any(~np.isfinite(vector)):
        raise ValueError(f"{name} must be a finite three-vector")
    length = float(np.linalg.norm(vector))
    if length == 0.0:
        raise ValueError(f"{name} must be non-zero")
    return vector / length


def _bilinear(field: np.ndarray, x_index: float, y_index: float) -> float:
    ny, nx = field.shape
    x0 = int(math.floor(x_index))
    y0 = int(math.floor(y_index))
    x1 = min(x0 + 1, nx - 1)
    y1 = min(y0 + 1, ny - 1)
    tx = x_index - x0
    ty = y_index - y0
    return float(
        field[y0, x0] * (1.0 - tx) * (1.0 - ty)
        + field[y0, x1] * tx * (1.0 - ty)
        + field[y1, x0] * (1.0 - tx) * ty
        + field[y1, x1] * tx * ty
    )


def _channel_par_coefficient(channel: dict) -> float:
    spectrum = channel.get("spectrum")
    if isinstance(spectrum, TabulatedSpectrum):
        return spectrum.photon_flux_per_watt_umol_s(400.0, 700.0)
    wavelength = float(channel["wavelength_nm"])
    if 400.0 <= wavelength <= 700.0:
        return float(irradiance_to_photon_flux(1.0, wavelength))
    return 0.0


def sample_virtual_sensor(
    result: dict,
    world_point_m: Iterable[float],
    photoperiod_h: float = 14.0,
    plane_tolerance_m: float = 0.02,
) -> dict:
    """Bilinearly sample the displayed scientific fields at a canopy point.

    ``world_point_m`` may lie on the canopy or on the small rendered heatmap
    offset above it. A configurable plane tolerance accepts that visual offset,
    while points outside the rectangular sensor footprint are rejected.
    """
    if not np.isfinite(photoperiod_h) or photoperiod_h <= 0:
        raise ValueError("photoperiod_h must be finite and positive")
    point = np.asarray(world_point_m, dtype=float)
    if point.shape != (3,) or np.any(~np.isfinite(point)):
        raise ValueError("world_point_m must be a finite three-vector")

    grid_cfg = result["design"]["grid"]
    width = float(grid_cfg["width_m"])
    depth = float(grid_cfg["depth_m"])
    if width <= 0 or depth <= 0:
        raise ValueError("grid dimensions must be positive")
    center = np.asarray(
        grid_cfg.get("center_m", [0.0, 0.0, grid_cfg.get("z_m", 0.0)]), dtype=float
    )
    u_axis = _unit_vector(grid_cfg.get("u_axis", [1.0, 0.0, 0.0]), "grid u_axis")
    v_axis = _unit_vector(grid_cfg.get("v_axis", [0.0, 1.0, 0.0]), "grid v_axis")
    if abs(float(np.dot(u_axis, v_axis))) > 1e-6:
        raise ValueError("grid u_axis and v_axis must be orthogonal")
    normal = np.cross(u_axis, v_axis)
    normal /= np.linalg.norm(normal)

    delta = point - center
    plane_distance = float(np.dot(delta, normal))
    if abs(plane_distance) > plane_tolerance_m:
        raise ValueError("selected point is not on the sensor plane")
    u = float(np.dot(delta, u_axis))
    v = float(np.dot(delta, v_axis))
    half_width = width / 2.0
    half_depth = depth / 2.0
    epsilon = 1e-9
    if u < -half_width - epsilon or u > half_width + epsilon or v < -half_depth - epsilon or v > half_depth + epsilon:
        raise ValueError("selected point is outside the sensor footprint")

    ppfd_field = np.asarray(result["fields"]["ppfd"], dtype=float)
    far_red_field = np.asarray(result["fields"]["far_red"], dtype=float)
    if ppfd_field.ndim != 2 or far_red_field.shape != ppfd_field.shape:
        raise ValueError("result PPFD/far-red fields must be matching two-dimensional arrays")
    ny, nx = ppfd_field.shape
    x_index = 0.0 if nx == 1 else (u + half_width) / width * (nx - 1)
    y_index = 0.0 if ny == 1 else (v + half_depth) / depth * (ny - 1)
    x_index = float(np.clip(x_index, 0.0, max(nx - 1, 0)))
    y_index = float(np.clip(y_index, 0.0, max(ny - 1, 0)))

    ppfd = _bilinear(ppfd_field, x_index, y_index)
    far_red = _bilinear(far_red_field, x_index, y_index)

    spectral_irradiance = np.asarray(result["fields"]["spectral_irradiance"], dtype=float)
    channels = list(result["design"].get("channels", []))
    channel_ppfd = {}
    if spectral_irradiance.shape[0] == len(channels) and spectral_irradiance.shape[1:] == ppfd_field.shape:
        for index, channel in enumerate(channels):
            irradiance = _bilinear(spectral_irradiance[index], x_index, y_index)
            channel_ppfd[str(channel["id"])] = irradiance * _channel_par_coefficient(channel)

    return {
        "world_point_m": point.tolist(),
        "grid_uv_m": [u, v],
        "grid_fraction": [
            0.0 if nx == 1 else x_index / (nx - 1),
            0.0 if ny == 1 else y_index / (ny - 1),
        ],
        "ppfd_umol_m2_s": ppfd,
        "dli_mol_m2_day": ppfd * photoperiod_h * 3600.0 / 1_000_000.0,
        "far_red_umol_m2_s": far_red,
        "channel_ppfd_umol_m2_s": channel_ppfd,
    }
