"""Render PPFD maps without changing or interpolating scientific values."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _extent(grid_config: dict) -> tuple[float, float, float, float]:
    return (-float(grid_config["width_m"]) / 2, float(grid_config["width_m"]) / 2,
            -float(grid_config["depth_m"]) / 2, float(grid_config["depth_m"]) / 2)


def render_comparison(baseline, optimized, grid_config: dict, out_dir: Path) -> dict[str, str]:
    """Write maps with a shared absolute scale; values are never interpolated."""
    baseline = np.asarray(baseline, dtype=float)
    optimized = np.asarray(optimized, dtype=float)
    if baseline.shape != optimized.shape:
        raise ValueError("baseline and optimized fields must have the same shape")
    out_dir.mkdir(parents=True, exist_ok=True)
    scale_max = float(max(baseline.max(), optimized.max()))
    extent = _extent(grid_config)
    paths = {
        "baseline_heatmap": "ppfd_baseline.png",
        "optimized_heatmap": "ppfd_optimized.png",
        "comparison_heatmap": "ppfd_comparison.png",
        "baseline_csv": "ppfd_baseline.csv",
        "optimized_csv": "ppfd_optimized.csv",
    }
    np.savetxt(out_dir / paths["baseline_csv"], baseline, delimiter=",", fmt="%.9f")
    np.savetxt(out_dir / paths["optimized_csv"], optimized, delimiter=",", fmt="%.9f")
    for field, title, key in ((baseline, "Baseline PPFD", "baseline_heatmap"),
                              (optimized, "Optimized PPFD", "optimized_heatmap")):
        fig, axis = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
        image = axis.imshow(field, origin="lower", extent=extent, cmap="viridis",
                            vmin=0.0, vmax=scale_max, aspect="equal", interpolation="nearest")
        axis.set(title=title, xlabel="Canopy x (m)", ylabel="Canopy y (m)")
        fig.colorbar(image, ax=axis, label="PPFD (µmol m⁻² s⁻¹)")
        fig.savefig(out_dir / paths[key], dpi=160)
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
    for axis, field, title in zip(axes, (baseline, optimized), ("Baseline", "Optimized"), strict=True):
        image = axis.imshow(field, origin="lower", extent=extent, cmap="viridis",
                            vmin=0.0, vmax=scale_max, aspect="equal", interpolation="nearest")
        axis.set(title=title, xlabel="Canopy x (m)", ylabel="Canopy y (m)")
    fig.colorbar(image, ax=axes, label="PPFD (µmol m⁻² s⁻¹)", shrink=0.9)
    fig.suptitle("OpenGrowTwin PPFD — shared absolute color scale")
    fig.savefig(out_dir / paths["comparison_heatmap"], dpi=160)
    plt.close(fig)
    return paths
