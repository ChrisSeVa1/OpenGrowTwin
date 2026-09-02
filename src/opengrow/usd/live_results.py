"""Author simulation fields and metrics into an already-open USD stage."""

from __future__ import annotations

import numpy as np


HEATMAP_PATHS = {
    "baseline": "/World/GrowInstallation/Results/BaselinePPFDHeatmap",
    "current": "/World/GrowInstallation/Results/CurrentPPFDHeatmap",
}

# Compact viridis anchors avoid importing Matplotlib in Kit.
_VIRIDIS_STOPS = np.asarray([
    [0.267004, 0.004874, 0.329415],
    [0.229739, 0.322361, 0.545706],
    [0.127568, 0.566949, 0.550556],
    [0.369214, 0.788888, 0.382914],
    [0.993248, 0.906157, 0.143936],
])


def colorize_ppfd(values, legend_min: float, legend_max: float):
    """Map scalar PPFD to a fixed, clamped five-anchor viridis scale."""
    field = np.asarray(values, dtype=float)
    if np.any(~np.isfinite(field)):
        raise ValueError("PPFD values must be finite")
    if not np.isfinite(legend_min) or not np.isfinite(legend_max) or legend_max <= legend_min:
        raise ValueError("legend maximum must be finite and greater than minimum")
    normalized = np.clip((field - legend_min) / (legend_max - legend_min), 0.0, 1.0)
    position = normalized * (_VIRIDIS_STOPS.shape[0] - 1)
    lower = np.floor(position).astype(int)
    upper = np.minimum(lower + 1, _VIRIDIS_STOPS.shape[0] - 1)
    fraction = (position - lower)[..., None]
    return _VIRIDIS_STOPS[lower] * (1.0 - fraction) + _VIRIDIS_STOPS[upper] * fraction


def _topology(ny: int, nx: int):
    counts = []
    indices = []
    for row in range(ny - 1):
        for column in range(nx - 1):
            lower_left = row * nx + column
            counts.append(4)
            indices.extend((lower_left, lower_left + 1, lower_left + nx + 1, lower_left + nx))
    return counts, indices


def _write_mesh(stage, path: str, result: dict, legend_min: float, legend_max: float):
    from pxr import Gf, Sdf, UsdGeom, Vt

    field = np.asarray(result["fields"]["ppfd"], dtype=float)
    points = np.asarray(result["fields"]["grid"], dtype=float)
    if points.shape != field.shape + (3,):
        raise ValueError("solver grid and PPFD shape do not match")
    ny, nx = field.shape
    grid_config = result["design"]["grid"]
    u_axis = np.asarray(grid_config.get("u_axis", [1.0, 0.0, 0.0]), dtype=float)
    v_axis = np.asarray(grid_config.get("v_axis", [0.0, 1.0, 0.0]), dtype=float)
    display_normal = np.cross(u_axis, v_axis)
    display_normal /= np.linalg.norm(display_normal)
    display_offset_m = 0.002
    display_points = points + display_normal * display_offset_m
    counts, indices = _topology(ny, nx)
    colors = colorize_ppfd(field, legend_min, legend_max)
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*value) for value in display_points.reshape(-1, 3)]))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(indices))
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "opengrow:ppfd", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex
    ).Set(Vt.FloatArray(field.ravel().tolist()))
    mesh.CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex).Set(
        Vt.Vec3fArray([Gf.Vec3f(*value) for value in colors.reshape(-1, 3)])
    )
    prim = mesh.GetPrim()
    prim.CreateAttribute("opengrow:ppfdUnit", Sdf.ValueTypeNames.String, custom=True).Set("umol m^-2 s^-1")
    prim.CreateAttribute("opengrow:gridNx", Sdf.ValueTypeNames.Int, custom=True).Set(nx)
    prim.CreateAttribute("opengrow:gridNy", Sdf.ValueTypeNames.Int, custom=True).Set(ny)
    prim.CreateAttribute("opengrow:legendMinPPFD", Sdf.ValueTypeNames.Double, custom=True).Set(legend_min)
    prim.CreateAttribute("opengrow:legendMaxPPFD", Sdf.ValueTypeNames.Double, custom=True).Set(legend_max)
    prim.CreateAttribute("opengrow:displayOffsetM", Sdf.ValueTypeNames.Double, custom=True).Set(display_offset_m)
    metrics = result["metrics"]
    metric_attributes = {
        "meanPPFD": "mean_ppfd_umol_m2_s",
        "minPPFD": "min_ppfd_umol_m2_s",
        "maxPPFD": "max_ppfd_umol_m2_s",
        "cvPPFD": "cv_ppfd",
        "uniformityMinMean": "uniformity_min_mean",
        "dli": "dli_mol_m2_day",
        "meanFarRed": "mean_far_red_umol_m2_s",
    }
    for usd_name, metric_name in metric_attributes.items():
        prim.CreateAttribute(f"opengrow:results:{usd_name}", Sdf.ValueTypeNames.Double, custom=True).Set(
            float(metrics[metric_name])
        )
    prim.CreateAttribute("opengrow:results:blockedRayCount", Sdf.ValueTypeNames.Int64, custom=True).Set(
        int(result["blocked_ray_count"])
    )
    return mesh


def set_display_mode(stage, mode: str):
    """Show exactly one of the baseline/current heatmaps."""
    from pxr import UsdGeom

    if mode not in HEATMAP_PATHS:
        raise ValueError(f"unknown display mode {mode!r}")
    for name, path in HEATMAP_PATHS.items():
        imageable = UsdGeom.Imageable(stage.GetPrimAtPath(path))
        if not imageable:
            continue
        if name == mode:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()


def update_live_results(stage, current: dict, baseline: dict | None = None, display_mode: str = "current"):
    """Create/update live heatmaps and metrics without reopening ``stage``."""
    from pxr import Sdf, UsdGeom

    baseline = baseline or current
    if baseline["fields"]["ppfd"].shape != current["fields"]["ppfd"].shape:
        raise ValueError("baseline and current heatmap shapes must match")
    baseline_values = np.asarray(baseline["fields"]["ppfd"], dtype=float)
    legend_min = float(baseline_values.min())
    legend_max = float(baseline_values.max())
    if legend_max <= legend_min:
        legend_max = legend_min + 1.0
    with Sdf.ChangeBlock():
        results = UsdGeom.Xform.Define(stage, "/World/GrowInstallation/Results").GetPrim()
        results.CreateAttribute("opengrow:role", Sdf.ValueTypeNames.Token, custom=True).Set("results")
        results.CreateAttribute("opengrow:activeDisplay", Sdf.ValueTypeNames.Token, custom=True).Set(display_mode)
        _write_mesh(stage, HEATMAP_PATHS["baseline"], baseline, legend_min, legend_max)
        _write_mesh(stage, HEATMAP_PATHS["current"], current, legend_min, legend_max)
        set_display_mode(stage, display_mode)
    return {
        "stage": stage,
        "baseline_path": HEATMAP_PATHS["baseline"],
        "current_path": HEATMAP_PATHS["current"],
        "legend_min": legend_min,
        "legend_max": legend_max,
        "vertex_count": int(current["fields"]["ppfd"].size),
    }
