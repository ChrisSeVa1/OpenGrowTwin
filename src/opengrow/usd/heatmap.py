"""Generate an ASCII OpenUSD heatmap mesh without requiring Kit or pxr."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import colormaps
import numpy as np


def _format_tuples(values, digits: int = 7) -> str:
    return ",\n            ".join(
        "(" + ", ".join(f"{float(component):.{digits}g}" for component in value) + ")"
        for value in values
    )


def _format_scalars(values, digits: int = 9) -> str:
    return ", ".join(f"{float(value):.{digits}g}" for value in values)


def _format_ints(values) -> str:
    return ", ".join(str(int(value)) for value in values)


def heatmap_mesh_data(ppfd, grid_config: dict) -> dict:
    """Return vertex, quad-topology, value, and display-color arrays."""
    field = np.asarray(ppfd, dtype=float)
    if field.ndim != 2 or min(field.shape) < 2:
        raise ValueError("PPFD must be a two-dimensional grid of at least 2 x 2")
    if np.any(~np.isfinite(field)) or np.any(field < 0):
        raise ValueError("PPFD values must be finite and non-negative")
    ny, nx = field.shape
    configured_shape = (int(grid_config["ny"]), int(grid_config["nx"]))
    if field.shape != configured_shape:
        raise ValueError(f"PPFD shape {field.shape} does not match grid {configured_shape}")
    xs = np.linspace(-float(grid_config["width_m"]) / 2, float(grid_config["width_m"]) / 2, nx)
    ys = np.linspace(-float(grid_config["depth_m"]) / 2, float(grid_config["depth_m"]) / 2, ny)
    z = float(grid_config.get("z_m", 0.0)) + 0.002
    points = np.array([(x, y, z) for y in ys for x in xs], dtype=float)
    face_indices = []
    for row in range(ny - 1):
        for column in range(nx - 1):
            lower_left = row * nx + column
            face_indices.extend((
                lower_left,
                lower_left + 1,
                lower_left + nx + 1,
                lower_left + nx,
            ))
    values = field.ravel()
    maximum = float(values.max())
    normalized = values / maximum if maximum else np.zeros_like(values)
    colors = colormaps["viridis"](normalized)[:, :3]
    return {
        "points": points,
        "face_vertex_counts": np.full((nx - 1) * (ny - 1), 4, dtype=int),
        "face_vertex_indices": np.asarray(face_indices, dtype=int),
        "ppfd": values,
        "display_color": colors,
        "shape": (ny, nx),
    }


def write_heatmap_usda(ppfd, grid_config: dict, metrics: dict, output_path: Path) -> dict:
    """Write a self-contained mesh layer ready for Kit/Omniverse composition."""
    data = heatmap_mesh_data(ppfd, grid_config)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ny, nx = data["shape"]
    text = f"""#usda 1.0
(
    defaultPrim = "OpenGrowTwinResults"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "OpenGrowTwinResults" (
    kind = "component"
)
{{
    custom string opengrow:schemaVersion = "0.2.0"
    custom string opengrow:resultType = "PPFD"

    def Mesh "PPFDHeatmap"
    {{
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [{_format_ints(data["face_vertex_counts"])}]
        int[] faceVertexIndices = [{_format_ints(data["face_vertex_indices"])}]
        point3f[] points = [
            {_format_tuples(data["points"])}
        ]
        color3f[] primvars:displayColor = [
            {_format_tuples(data["display_color"])}
        ] (
            interpolation = "vertex"
        )
        float[] primvars:opengrow:ppfd = [{_format_scalars(data["ppfd"])}] (
            interpolation = "vertex"
        )
        custom string opengrow:ppfdUnit = "umol m^-2 s^-1"
        custom int opengrow:grid:nx = {nx}
        custom int opengrow:grid:ny = {ny}
        custom double opengrow:results:meanPPFD = {float(metrics["mean_ppfd_umol_m2_s"]):.12g}
        custom double opengrow:results:minPPFD = {float(metrics["min_ppfd_umol_m2_s"]):.12g}
        custom double opengrow:results:maxPPFD = {float(metrics["max_ppfd_umol_m2_s"]):.12g}
        custom double opengrow:results:uniformityMinMean = {float(metrics["uniformity_min_mean"]):.12g}
        custom double opengrow:results:cvPPFD = {float(metrics["cv_ppfd"]):.12g}
        custom double opengrow:results:dli = {float(metrics["dli_mol_m2_day"]):.12g}
    }}
}}
"""
    output_path.write_text(text, encoding="utf-8")
    return {
        "path": output_path.name,
        "vertex_count": int(len(data["points"])),
        "face_count": int(len(data["face_vertex_counts"])),
        "ppfd_min": float(data["ppfd"].min()),
        "ppfd_max": float(data["ppfd"].max()),
    }
