"""Author simulation fields and metrics into an already-open USD stage."""

from __future__ import annotations

import numpy as np


HEATMAP_PATHS = {
    "baseline": "/World/GrowInstallation/Results/BaselinePPFDHeatmap",
    "current": "/World/GrowInstallation/Results/CurrentPPFDHeatmap",
}

VIEWPORT_MODES = {
    "scientific",
    "rtx",
    "combined",
}

RESULTS_PATH = "/World/GrowInstallation/Results"
MATERIAL_PATH = RESULTS_PATH + "/Materials/ScientificPPFDMaterial"

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


def legend_range(values) -> tuple[float, float]:
    """Return a finite, non-degenerate legend range for one PPFD field."""
    field = np.asarray(values, dtype=float)
    if field.size == 0 or np.any(~np.isfinite(field)):
        raise ValueError("PPFD values must contain finite samples")
    legend_min = float(field.min())
    legend_max = float(field.max())
    if legend_max <= legend_min:
        legend_max = legend_min + 1.0
    return legend_min, legend_max


def comparison_legend_range(baseline_values, current_values) -> tuple[float, float]:
    """Return one absolute PPFD scale shared by baseline and current fields."""
    baseline = np.asarray(baseline_values, dtype=float)
    current = np.asarray(current_values, dtype=float)
    if baseline.size == 0 or current.size == 0:
        raise ValueError("comparison PPFD fields must not be empty")
    if np.any(~np.isfinite(baseline)) or np.any(~np.isfinite(current)):
        raise ValueError("comparison PPFD values must be finite")
    minimum = float(min(baseline.min(), current.min()))
    maximum = float(max(baseline.max(), current.max()))
    if maximum <= minimum:
        maximum = minimum + 1.0
    return minimum, maximum


def _topology(ny: int, nx: int):
    counts = []
    indices = []
    for row in range(ny - 1):
        for column in range(nx - 1):
            lower_left = row * nx + column
            counts.append(4)
            indices.extend((lower_left, lower_left + 1, lower_left + nx + 1, lower_left + nx))
    return counts, indices


def _ensure_scientific_material(stage, opacity: float = 1.0):
    """Create an emissive/unlit-like material driven by vertex displayColor.

    RTX scene lighting must not tint the scientific PPFD colormap. A PreviewSurface
    with zero diffuse contribution and displayColor connected to emissiveColor
    keeps the heatmap visually independent from the blue/red/far-red lights.
    """
    from pxr import Sdf, UsdShade

    material = UsdShade.Material.Define(stage, MATERIAL_PATH)
    shader = UsdShade.Shader.Define(stage, MATERIAL_PATH + "/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set((0.0, 0.0, 0.0))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(opacity))

    reader = UsdShade.Shader.Define(stage, MATERIAL_PATH + "/DisplayColorReader")
    reader.CreateIdAttr("UsdPrimvarReader_float3")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("displayColor")
    reader.CreateOutput("result", Sdf.ValueTypeNames.Float3)
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(reader.ConnectableAPI(), "result")
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def _write_mesh(stage, path: str, result: dict, legend_min: float, legend_max: float):
    from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt

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
    # Keep the display-only scientific overlay clearly separated from the
    # physical CanopyPlane. A 2 mm offset can lose the depth test in Kit's
    # orthographic Top view; 10 mm remains inside the virtual-sensor tolerance
    # while avoiding z-fighting across perspective and orthographic cameras.
    display_offset_m = 0.010
    display_points = points + display_normal * display_offset_m
    counts, indices = _topology(ny, nx)
    colors = colorize_ppfd(field, legend_min, legend_max)
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*value) for value in display_points.reshape(-1, 3)]))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(indices))
    ppfd_primvar = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar(
        "opengrow:ppfd", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex
    )
    ppfd_primvar.Set(Vt.FloatArray(field.ravel().tolist()))
    ppfd_primvar.SetIndices(Vt.IntArray(list(range(int(field.size)))))
    display_color = mesh.CreateDisplayColorPrimvar(UsdGeom.Tokens.vertex)
    display_color.Set(Vt.Vec3fArray([Gf.Vec3f(*value) for value in colors.reshape(-1, 3)]))
    display_color.SetIndices(Vt.IntArray(list(range(int(field.size)))))

    material = _ensure_scientific_material(stage)
    UsdShade.MaterialBindingAPI(mesh.GetPrim()).Bind(material)

    prim = mesh.GetPrim()
    prim.CreateAttribute("opengrow:visualOnly", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
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


def _viewport_mode(stage) -> str:
    results = stage.GetPrimAtPath(RESULTS_PATH)
    if results:
        attr = results.GetAttribute("opengrow:viewportMode")
        value = str(attr.Get()) if attr and attr.Get() is not None else "scientific"
        if value in VIEWPORT_MODES:
            return value
    return "scientific"


def set_display_mode(stage, mode: str):
    """Select baseline/current scientific field while respecting viewport mode."""
    from pxr import UsdGeom

    if mode not in HEATMAP_PATHS:
        raise ValueError(f"unknown display mode {mode!r}")
    viewport_mode = _viewport_mode(stage)
    for name, path in HEATMAP_PATHS.items():
        prim = stage.GetPrimAtPath(path)
        if not prim:
            continue
        imageable = UsdGeom.Imageable(prim)
        if viewport_mode == "rtx":
            imageable.MakeInvisible()
        elif name == mode:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()


def set_heatmap_visualization_mode(stage, mode: str):
    """Switch viewport between scientific PPFD, RTX-only, and combined views."""
    from pxr import Sdf

    if mode not in VIEWPORT_MODES:
        raise ValueError(f"unknown viewport visualization mode {mode!r}")
    results = stage.GetPrimAtPath(RESULTS_PATH)
    if not results:
        return {"mode": mode, "applied": False}
    results.CreateAttribute("opengrow:viewportMode", Sdf.ValueTypeNames.Token, custom=True).Set(mode)
    opacity = 0.55 if mode == "combined" else 1.0
    _ensure_scientific_material(stage, opacity=opacity)
    display_attr = results.GetAttribute("opengrow:activeDisplay")
    display_mode = str(display_attr.Get()) if display_attr and display_attr.Get() is not None else "current"
    if display_mode not in HEATMAP_PATHS:
        display_mode = "current"
    set_display_mode(stage, display_mode)
    return {"mode": mode, "applied": True, "opacity": opacity}


def update_live_results(stage, current: dict, baseline: dict | None = None, display_mode: str = "current"):
    """Create/update live PPFD heatmaps without reopening ``stage``.

    Baseline and current are colorized against one shared absolute scale so a
    color means the same PPFD value during A/B switching. The meshes are bound to
    an emissive scientific material so RTX LED colors cannot tint the colormap.
    """
    from pxr import Sdf, UsdGeom

    baseline = baseline or current
    if display_mode not in HEATMAP_PATHS:
        raise ValueError(f"unknown display mode {display_mode!r}")
    if baseline["fields"]["ppfd"].shape != current["fields"]["ppfd"].shape:
        raise ValueError("baseline and current heatmap shapes must match")

    shared_range = comparison_legend_range(
        baseline["fields"]["ppfd"], current["fields"]["ppfd"]
    )
    baseline["display_legend_range"] = list(shared_range)
    current["display_legend_range"] = list(shared_range)

    results = UsdGeom.Xform.Define(stage, RESULTS_PATH).GetPrim()
    results.CreateAttribute("opengrow:role", Sdf.ValueTypeNames.Token, custom=True).Set("results")
    results.CreateAttribute("opengrow:activeDisplay", Sdf.ValueTypeNames.Token, custom=True).Set(display_mode)
    if not results.HasAttribute("opengrow:viewportMode"):
        results.CreateAttribute("opengrow:viewportMode", Sdf.ValueTypeNames.Token, custom=True).Set("scientific")

    _write_mesh(stage, HEATMAP_PATHS["baseline"], baseline, *shared_range)
    _write_mesh(stage, HEATMAP_PATHS["current"], current, *shared_range)
    set_heatmap_visualization_mode(stage, _viewport_mode(stage))

    return {
        "stage": stage,
        "baseline_path": HEATMAP_PATHS["baseline"],
        "current_path": HEATMAP_PATHS["current"],
        "legend_min": shared_range[0],
        "legend_max": shared_range[1],
        "legend_ranges": {
            "baseline": {"min": shared_range[0], "max": shared_range[1]},
            "current": {"min": shared_range[0], "max": shared_range[1]},
        },
        "viewport_mode": _viewport_mode(stage),
        "vertex_count": int(current["fields"]["ppfd"].size),
    }
