"""Simulation orchestration shared by the CLI and NVIDIA Kit extension."""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from .manufacturer_profiles import apply_manufacturer_profiles
from .physics.direct_solver import sensor_grid, simulate_design
from .physics.metrics import summarize
from .usd.stage_reader import stage_to_solver_design


GRID_MODES = {
    "preview": (21, 13),
    "final": None,
}

OPTICAL_MODELS = {
    "auto",
    "simplified",
    "manufacturer",
}


def apply_grid_mode(design: dict, mode: str) -> dict:
    """Return a copy with preview or authored final sensor resolution."""
    if mode not in GRID_MODES:
        raise ValueError(f"unknown simulation mode {mode!r}")
    configured = deepcopy(design)
    resolution = GRID_MODES[mode]
    if resolution is not None:
        authored_nx = int(configured["grid"]["nx"])
        authored_ny = int(configured["grid"]["ny"])
        configured["grid"]["nx"] = min(authored_nx, resolution[0])
        configured["grid"]["ny"] = min(authored_ny, resolution[1])
    return configured


def apply_optical_model(design: dict, optical_model: str = "auto", manufacturer_asset_root=None) -> dict:
    """Return a design configured for the requested scientific optical model.

    ``simplified`` deliberately keeps the OpenUSD-derived generalized-Lambertian
    model. ``manufacturer`` requires the complete local IES+SPD bundle and fails
    loudly if it is unavailable. ``auto`` preserves the current demo/public
    behavior: use manufacturer optics when the complete local bundle exists,
    otherwise retain the simplified fallback.
    """
    if optical_model not in OPTICAL_MODELS:
        raise ValueError(f"unknown optical model {optical_model!r}")
    if optical_model == "simplified":
        return deepcopy(design)
    return apply_manufacturer_profiles(
        design,
        asset_root=manufacturer_asset_root,
        required=optical_model == "manufacturer",
    )


def prepare_solver_design(
    stage,
    mode: str = "preview",
    manufacturer_asset_root=None,
    optical_model: str = "auto",
) -> dict:
    """Read live USD state and configure the deterministic solver design.

    The active optical model is explicit so the Kit selector can change the real
    scientific path rather than merely changing a UI label. Raw vendor assets
    remain local and gitignored.
    """
    design = stage_to_solver_design(stage)
    design = apply_optical_model(
        design,
        optical_model=optical_model,
        manufacturer_asset_root=manufacturer_asset_root,
    )
    return apply_grid_mode(design, mode)


def _zero_fields(design: dict) -> dict:
    """Return a valid zero-light field for a scene with no active emitters."""
    grid_cfg = design["grid"]
    grid = sensor_grid(
        grid_cfg["width_m"],
        grid_cfg["depth_m"],
        grid_cfg["nx"],
        grid_cfg["ny"],
        grid_cfg.get("z_m", 0.0),
        grid_cfg.get("center_m"),
        grid_cfg.get("u_axis"),
        grid_cfg.get("v_axis"),
    )
    shape = grid.shape[:-1]
    zero = np.zeros(shape, dtype=float)
    return {
        "grid": grid,
        "wavelengths_nm": np.empty((0,), dtype=float),
        "spectral_irradiance": np.empty((0, *shape), dtype=float),
        "band_ppfd": np.empty((0, *shape), dtype=float),
        "ppfd": zero.copy(),
        "far_red": zero.copy(),
        "far_red_band_nm": [700.0, 750.0],
        "emitter_visibility": np.empty((0, *shape), dtype=bool),
        "occlusion_diagnostics": [],
        "blocked_ray_count": 0,
        "total_ray_count": 0,
    }


def run_prepared_design(design: dict, photoperiod_h: float = 14.0) -> dict:
    """Run a prepared design; safe to execute on a background worker."""
    fields = simulate_design(design) if design.get("channels") else _zero_fields(design)
    metrics = summarize(fields["ppfd"], fields["far_red"], photoperiod_h)
    return {
        "design": design,
        "fields": fields,
        "metrics": metrics,
        "mode_shape": [int(fields["ppfd"].shape[1]), int(fields["ppfd"].shape[0])],
        "blocked_ray_count": int(fields["blocked_ray_count"]),
        "total_ray_count": int(fields["total_ray_count"]),
    }


def simulate_stage(
    stage,
    mode: str = "preview",
    photoperiod_h: float = 14.0,
    optical_model: str = "auto",
) -> dict:
    """Synchronous convenience path for scripts and acceptance tests."""
    design = prepare_solver_design(stage, mode, optical_model=optical_model)
    return run_prepared_design(design, photoperiod_h)
