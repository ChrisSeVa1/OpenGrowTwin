"""Synchronize presentation-only RTX lights from scientific emitter state."""

from __future__ import annotations

import math


VISUAL_INTENSITY_PER_RADIANT_WATT = 500.0
RTX_LIGHT_NAME = "RTXLight"


def wavelength_to_visual_rgb(wavelength_nm: float) -> tuple[float, float, float]:
    """Return an approximate linear RGB cue for visualization, not metrology."""
    wavelength = float(wavelength_nm)
    if not math.isfinite(wavelength) or not 1.0 <= wavelength <= 10000.0:
        raise ValueError("wavelength must be finite and between 1 and 10000 nm")
    if wavelength < 500.0:
        return (0.08, 0.18, 1.0)
    if wavelength < 600.0:
        return (0.15, 1.0, 0.12)
    if wavelength <= 700.0:
        return (1.0, 0.025, 0.01)
    return (0.35, 0.0, 0.0)


def visual_intensity(radiant_power_w: float, enabled: bool = True, scale: float = VISUAL_INTENSITY_PER_RADIANT_WATT):
    """Derive RTX intensity from authoritative optical power."""
    power = float(radiant_power_w)
    if not math.isfinite(power) or power < 0.0:
        raise ValueError("radiant power must be finite and non-negative")
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("visual intensity scale must be finite and positive")
    return power * scale if enabled else 0.0


def sync_rtx_lights(stage, scale: float = VISUAL_INTENSITY_PER_RADIANT_WATT) -> dict:
    """Create/update one inherited-transform DiskLight below every emitter."""
    from pxr import Gf, Sdf, UsdLux

    synced = []
    for prim in list(stage.Traverse()):
        role = prim.GetAttribute("opengrow:role").Get() if prim.HasAttribute("opengrow:role") else None
        if str(role) != "emitter":
            continue
        wavelength = float(prim.GetAttribute("opengrow:wavelengthNm").Get())
        power = float(prim.GetAttribute("opengrow:radiantPowerW").Get())
        enabled = bool(prim.GetAttribute("opengrow:enabled").Get())
        light_path = prim.GetPath().AppendChild(RTX_LIGHT_NAME)
        light = UsdLux.DiskLight.Define(stage, light_path)
        color = wavelength_to_visual_rgb(wavelength)
        intensity = visual_intensity(power, enabled, scale)
        light.CreateColorAttr(Gf.Vec3f(*color))
        light.CreateIntensityAttr(intensity)
        light.CreateExposureAttr(0.0)
        light.CreateRadiusAttr(0.015)
        light.CreateNormalizeAttr(True)
        light_prim = light.GetPrim()
        light_prim.CreateAttribute("opengrow:visualOnly", Sdf.ValueTypeNames.Bool, custom=True).Set(True)
        light_prim.CreateAttribute("opengrow:scientificSourcePath", Sdf.ValueTypeNames.String, custom=True).Set(
            str(prim.GetPath())
        )
        light_prim.CreateAttribute("opengrow:visualIntensityScale", Sdf.ValueTypeNames.Double, custom=True).Set(scale)
        light_prim.CreateAttribute(
            "opengrow:spectrumWavelengthsNm", Sdf.ValueTypeNames.DoubleArray, custom=True
        ).Set([wavelength])
        light_prim.CreateAttribute(
            "opengrow:spectrumRelativePower", Sdf.ValueTypeNames.DoubleArray, custom=True
        ).Set([1.0])
        synced.append({
            "emitter_path": str(prim.GetPath()),
            "light_path": str(light_path),
            "wavelength_nm": wavelength,
            "radiant_power_w": power,
            "visual_intensity": intensity,
            "visual_color": list(color),
        })
    if not synced:
        raise ValueError("stage contains no scientific emitters to synchronize")
    return {"light_count": len(synced), "intensity_scale": scale, "lights": synced}
