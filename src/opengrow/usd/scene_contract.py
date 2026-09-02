"""OpenGrowTwin live-scene contract and portable USDA authoring.

The writer intentionally does not depend on ``pxr`` so the deterministic CPU
workflow can create a stage. Runtime discovery is implemented in
``opengrow.usd.stage_reader`` and is executed inside Kit.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.3.0"
ROLE_ATTRIBUTE = "opengrow:role"
ROLES = frozenset({"installation", "fixture", "emitter", "sensorPlane", "occluder", "results"})


@dataclass(frozen=True)
class CoordinateConvention:
    meters_per_unit: float = 1.0
    up_axis: str = "Z"
    forward_axis: str = "-Z"
    handedness: str = "rightHanded"


COORDINATES = CoordinateConvention()


def _number(value: Any, name: str, *, minimum: float | None = None) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return result


def validate_design_for_scene(design: dict) -> None:
    """Validate fields required to author the live scene contract."""
    grid = design.get("grid")
    if not isinstance(grid, dict):
        raise ValueError("design.grid must be an object")
    for key in ("width_m", "depth_m"):
        _number(grid.get(key), f"grid.{key}", minimum=0.000001)
    _number(grid.get("z_m", 0.0), "grid.z_m")

    channels = design.get("channels")
    if not isinstance(channels, list) or not channels:
        raise ValueError("design.channels must be a non-empty list")
    ids: set[str] = set()
    for channel in channels:
        channel_id = channel.get("id")
        if not isinstance(channel_id, str) or not channel_id:
            raise ValueError("each channel requires a non-empty id")
        if channel_id in ids:
            raise ValueError(f"duplicate channel id: {channel_id}")
        ids.add(channel_id)
        _number(channel.get("wavelength_nm"), f"{channel_id}.wavelength_nm", minimum=1.0)
        emitters = channel.get("emitters")
        if not isinstance(emitters, list) or not emitters:
            raise ValueError(f"{channel_id}.emitters must be a non-empty list")
        for index, emitter in enumerate(emitters):
            prefix = f"{channel_id}.emitters[{index}]"
            position = emitter.get("position_m")
            if not isinstance(position, list) or len(position) != 3:
                raise ValueError(f"{prefix}.position_m must contain x, y, z")
            for axis, value in zip("xyz", position):
                _number(value, f"{prefix}.position_m.{axis}")
            _number(emitter.get("radiant_power_w"), f"{prefix}.radiant_power_w", minimum=0.0)
            _number(emitter.get("beam_exponent", 1.0), f"{prefix}.beam_exponent", minimum=0.0)


def _f(value: Any) -> str:
    return f"{float(value):.9g}"


def _v3(values: list[float] | tuple[float, float, float]) -> str:
    return "(" + ", ".join(_f(value) for value in values) + ")"


def write_live_scene_usda(design: dict, output_path: Path) -> dict:
    """Write the authoritative OGT-101 live scene from an existing design."""
    validate_design_for_scene(design)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid = design["grid"]
    fixture_height = max(
        float(emitter["position_m"][2])
        for channel in design["channels"]
        for emitter in channel["emitters"]
    )

    emitter_blocks: list[str] = []
    emitter_count = 0
    for channel in design["channels"]:
        for index, emitter in enumerate(channel["emitters"], start=1):
            emitter_count += 1
            x, y, z = (float(value) for value in emitter["position_m"])
            local_position = (x, y, z - fixture_height)
            name = f"{channel['id'].title().replace('_', '')}_{index:02d}"
            emitter_blocks.append(f'''            def Xform "{name}"
            {{
                custom token opengrow:role = "emitter"
                custom token opengrow:channel = "{channel['id']}"
                custom double opengrow:wavelengthNm = {_f(channel['wavelength_nm'])}
                custom double opengrow:radiantPowerW = {_f(emitter['radiant_power_w'])}
                custom double opengrow:beamExponent = {_f(emitter.get('beam_exponent', 1.0))}
                custom double3 opengrow:emissionDirection = (0, 0, -1)
                custom bool opengrow:enabled = true
                double3 xformOp:translate = {_v3(local_position)}
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }}''')

    emitters = "\n\n".join(emitter_blocks)
    width = float(grid["width_m"])
    depth = float(grid["depth_m"])
    sensor_z = float(grid.get("z_m", 0.0))
    text = f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{{
    custom string opengrow:schemaVersion = "{SCHEMA_VERSION}"
    custom token opengrow:coordinateSystem = "rightHanded_Zup"
    custom token opengrow:emitterForwardAxis = "-Z"

    def Xform "GrowInstallation" (kind = "assembly")
    {{
        custom token opengrow:role = "installation"

        def Scope "Fixtures"
        {{
            def Xform "Fixture_01" (kind = "component")
            {{
                custom token opengrow:role = "fixture"
                custom string opengrow:fixtureId = "fixture_01"
                double3 xformOp:translate = (0, 0, {_f(fixture_height)})
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Cube "Housing"
                {{
                    double size = 1
                    float3[] extent = [(-0.48, -0.28, -0.025), (0.48, 0.28, 0.025)]
                    color3f[] primvars:displayColor = [(0.12, 0.14, 0.16)]
                    double3 xformOp:scale = (0.96, 0.56, 0.05)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                }}

                def Scope "Emitters"
                {{
{emitters}
                }}
            }}
        }}

        def Scope "SensorPlanes"
        {{
            def Cube "CanopyPlane"
            {{
                custom token opengrow:role = "sensorPlane"
                custom string opengrow:sensorId = "canopy_plane"
                custom int opengrow:gridNx = {int(grid['nx'])}
                custom int opengrow:gridNy = {int(grid['ny'])}
                custom double opengrow:widthM = {_f(width)}
                custom double opengrow:depthM = {_f(depth)}
                custom double3 opengrow:samplingPointLocal = (0, 0, 0.5)
                double size = 1
                double3 xformOp:translate = (0, 0, {_f(sensor_z - 0.005)})
                double3 xformOp:scale = ({_f(width)}, {_f(depth)}, 0.01)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            }}
        }}

        def Scope "Occluders"
        {{
            def Cube "Occluder_01"
            {{
                custom token opengrow:role = "occluder"
                custom string opengrow:occluderId = "occluder_01"
                custom token opengrow:occluderShape = "box"
                custom bool opengrow:enabled = true
                double size = 1
                double3 xformOp:translate = (0.65, 0, 0.3)
                double3 xformOp:scale = (0.04, 0.06, 0.16)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            }}
        }}

        def Xform "Results"
        {{
            custom token opengrow:role = "results"
            custom string opengrow:resultAsset = "../build/optimization/ppfd_heatmap.usda"
        }}
    }}
}}
'''
    output_path.write_text(text, encoding="utf-8")
    return {
        "path": output_path.name,
        "schema_version": SCHEMA_VERSION,
        "fixture_count": 1,
        "emitter_count": emitter_count,
        "sensor_plane_count": 1,
        "occluder_count": 1,
    }
