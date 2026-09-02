"""Simulation orchestration shared by the CLI and NVIDIA Kit extension."""

from __future__ import annotations

from copy import deepcopy

from .physics.direct_solver import simulate_design
from .physics.metrics import summarize
from .usd.stage_reader import stage_to_solver_design


GRID_MODES = {
    "preview": (21, 13),
    "final": None,
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


def prepare_solver_design(stage, mode: str = "preview") -> dict:
    """Read the live stage on Kit's main thread and configure grid mode."""
    return apply_grid_mode(stage_to_solver_design(stage), mode)


def run_prepared_design(design: dict, photoperiod_h: float = 14.0) -> dict:
    """Run a prepared design; safe to execute on a background worker."""
    fields = simulate_design(design)
    metrics = summarize(fields["ppfd"], fields["far_red"], photoperiod_h)
    return {
        "design": design,
        "fields": fields,
        "metrics": metrics,
        "mode_shape": [int(fields["ppfd"].shape[1]), int(fields["ppfd"].shape[0])],
        "blocked_ray_count": int(fields["blocked_ray_count"]),
        "total_ray_count": int(fields["total_ray_count"]),
    }


def simulate_stage(stage, mode: str = "preview", photoperiod_h: float = 14.0) -> dict:
    """Synchronous convenience path for scripts and acceptance tests."""
    return run_prepared_design(prepare_solver_design(stage, mode), photoperiod_h)
