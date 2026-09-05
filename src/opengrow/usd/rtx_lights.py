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


def visual_intensity(
    radiant_power_w: float,
    enabled: bool = True,
    scale: float = VISUAL_INTENSITY_PER_RADIANT_WATT,
):
    """Derive RTX intensity from authoritative optical power."""
    power = float(radiant_power_w)
    if not math.isfinite(power) or power < 0.0:
        raise ValueError("radiant power must be finite and non-negative")
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("visual intensity scale must be finite and positive")
    return power * scale if enabled else 0.0


def _normalized_ies_mapping(ies_by_channel: dict | None) -> dict[str, str]:
    """Validate an optional channel-to-IES asset mapping without touching files."""
    if ies_by_channel is None:
        return {}
    if not isinstance(ies_by_channel, dict):
        raise TypeError("ies_by_channel must be a mapping of channel id to USD asset path")
    result: dict[str, str] = {}
    for channel, asset_path in ies_by_channel.items():
        channel_id = str(channel).strip()
        path = str(asset_path).strip()
        if not channel_id:
            raise ValueError("IES channel id must be non-empty")
        if not path:
            raise ValueError(f"IES asset path for channel {channel_id!r} must be non-empty")
        result[channel_id] = path
    return result


def sync_rtx_lights(
    stage,
    scale: float = VISUAL_INTENSITY_PER_RADIANT_WATT,
    ies_by_channel: dict | None = None,
) -> dict:
    """Create/update one inherited-transform DiskLight below every emitter.

    ``ies_by_channel`` optionally maps OpenGrowTwin channel ids to manufacturer IES
    asset paths. When supplied, the same scientific emitter remains authoritative for
    transform, power, and enabled state while the child RTX light receives a
    ``UsdLux.ShapingAPI`` IES profile for presentation. The RTX light remains marked
    ``opengrow:visualOnly = true`` and must not be used as scientific ground truth.
    """
    from pxr import Gf, Sdf, UsdLux

    ies_assets = _normalized_ies_mapping(ies_by_channel)
    synced = []
    for prim in list(stage.Traverse()):
        role = prim.GetAttribute("opengrow:role").Get() if prim.HasAttribute("opengrow:role") else None
        if str(role) != "emitter":
            continue
        channel = str(prim.GetAttribute("opengrow:channel").Get())
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

        ies_file = ies_assets.get(channel)
        if ies_file is not None:
            shaping = UsdLux.ShapingAPI.Apply(light_prim)
            shaping.CreateShapingIesFileAttr(Sdf.AssetPath(ies_file))
            shaping.CreateShapingIesNormalizeAttr(True)
            shaping.CreateShapingIesAngleScaleAttr(1.0)
            light_prim.CreateAttribute("opengrow:angularModel", Sdf.ValueTypeNames.Token, custom=True).Set(
                "manufacturer_ies"
            )
            light_prim.CreateAttribute("opengrow:iesAssetPath", Sdf.ValueTypeNames.Asset, custom=True).Set(
                Sdf.AssetPath(ies_file)
            )
        else:
            light_prim.CreateAttribute("opengrow:angularModel", Sdf.ValueTypeNames.Token, custom=True).Set(
                "generalized_lambertian"
            )

        synced.append({
            "emitter_path": str(prim.GetPath()),
            "light_path": str(light_path),
            "channel": channel,
            "wavelength_nm": wavelength,
            "radiant_power_w": power,
            "visual_intensity": intensity,
            "visual_color": list(color),
            "angular_model": "manufacturer_ies" if ies_file is not None else "generalized_lambertian",
            "ies_file": ies_file,
        })
    if not synced:
        raise ValueError("stage contains no scientific emitters to synchronize")
    return {
        "light_count": len(synced),
        "intensity_scale": scale,
        "ies_channel_count": len(ies_assets),
        "lights": synced,
    }
