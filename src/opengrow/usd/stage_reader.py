"""Discover live OpenGrowTwin entities from an OpenUSD stage inside Kit."""

from __future__ import annotations

from .scene_contract import ROLE_ATTRIBUTE, ROLES, SCHEMA_VERSION


def _required(prim, name: str):
    attribute = prim.GetAttribute(name)
    value = attribute.Get() if attribute else None
    if value is None:
        raise ValueError(f"{prim.GetPath()}: missing {name}")
    return value


def discover_stage(stage) -> dict:
    """Return validated entities and world-space emitter state.

    ``stage`` is deliberately duck-typed; callers provide a ``pxr.Usd.Stage``
    from Kit. Importing this module therefore remains safe outside Kit.
    """
    from pxr import Gf, UsdGeom  # available in NVIDIA Kit

    meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage))
    up_axis = str(UsdGeom.GetStageUpAxis(stage))
    if abs(meters_per_unit - 1.0) > 1e-12:
        raise ValueError(f"stage metersPerUnit must be 1, got {meters_per_unit}")
    if up_axis != "Z":
        raise ValueError(f"stage upAxis must be Z, got {up_axis}")

    root = stage.GetDefaultPrim()
    if not root:
        raise ValueError("stage has no default prim")
    version = _required(root, "opengrow:schemaVersion")
    if str(version) != SCHEMA_VERSION:
        raise ValueError(f"unsupported OpenGrowTwin scene schema {version!s}")

    entities = {role: [] for role in ROLES}
    cache = UsdGeom.XformCache()
    for prim in stage.Traverse():
        role_attr = prim.GetAttribute(ROLE_ATTRIBUTE)
        role = str(role_attr.Get()) if role_attr and role_attr.Get() is not None else None
        if role is None:
            continue
        if role not in ROLES:
            raise ValueError(f"{prim.GetPath()}: unknown opengrow role {role!r}")
        record = {"path": str(prim.GetPath()), "role": role}
        transform = cache.GetLocalToWorldTransform(prim)
        if role == "emitter":
            translation = transform.ExtractTranslation()
            local_direction = _required(prim, "opengrow:emissionDirection")
            direction = transform.TransformDir(local_direction).GetNormalized()
            record.update({
                "channel": str(_required(prim, "opengrow:channel")),
                "wavelength_nm": float(_required(prim, "opengrow:wavelengthNm")),
                "radiant_power_w": float(_required(prim, "opengrow:radiantPowerW")),
                "beam_exponent": float(_required(prim, "opengrow:beamExponent")),
                "enabled": bool(_required(prim, "opengrow:enabled")),
                "position_m": [float(value) for value in translation],
                "direction": [float(value) for value in direction],
            })
        elif role == "sensorPlane":
            sampling_point = _required(prim, "opengrow:samplingPointLocal")
            center = transform.Transform(sampling_point)
            u_axis = transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0)).GetNormalized()
            v_axis = transform.TransformDir(Gf.Vec3d(0.0, 1.0, 0.0)).GetNormalized()
            record.update({
                "width_m": float(_required(prim, "opengrow:widthM")),
                "depth_m": float(_required(prim, "opengrow:depthM")),
                "nx": int(_required(prim, "opengrow:gridNx")),
                "ny": int(_required(prim, "opengrow:gridNy")),
                "center_m": [float(value) for value in center],
                "u_axis": [float(value) for value in u_axis],
                "v_axis": [float(value) for value in v_axis],
            })
        elif role == "occluder":
            shape = str(_required(prim, "opengrow:occluderShape"))
            if shape != "box" or not prim.IsA(UsdGeom.Cube):
                raise ValueError(f"{prim.GetPath()}: MVP occluder must be a Cube tagged as box")
            size = float(_required(prim, "size"))
            center = transform.ExtractTranslation()
            basis = [
                transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0)),
                transform.TransformDir(Gf.Vec3d(0.0, 1.0, 0.0)),
                transform.TransformDir(Gf.Vec3d(0.0, 0.0, 1.0)),
            ]
            lengths = [float(vector.GetLength()) for vector in basis]
            if any(length <= 0 for length in lengths):
                raise ValueError(f"{prim.GetPath()}: occluder transform is degenerate")
            record.update({
                "enabled": bool(_required(prim, "opengrow:enabled")),
                "shape": shape,
                "center_m": [float(value) for value in center],
                "axes": [[float(value) for value in vector.GetNormalized()] for vector in basis],
                "half_extents_m": [size * length / 2.0 for length in lengths],
            })
        entities[role].append(record)

    required_roles = ("fixture", "emitter", "sensorPlane", "occluder")
    missing = [role for role in required_roles if not entities[role]]
    if missing:
        raise ValueError(f"stage is missing required roles: {', '.join(missing)}")
    return {
        "schema_version": str(version),
        "meters_per_unit": meters_per_unit,
        "up_axis": up_axis,
        "entities": entities,
    }


def entities_to_solver_design(discovered: dict) -> dict:
    """Convert validated discovery records to the deterministic solver model."""
    if discovered.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("discovery data has an unsupported schema version")
    entities = discovered.get("entities", {})
    sensors = entities.get("sensorPlane", [])
    if len(sensors) != 1:
        raise ValueError("MVP requires exactly one sensor plane")
    sensor = sensors[0]
    grid = {
        "width_m": float(sensor["width_m"]),
        "depth_m": float(sensor["depth_m"]),
        "nx": int(sensor["nx"]),
        "ny": int(sensor["ny"]),
        "center_m": [float(value) for value in sensor["center_m"]],
        "u_axis": [float(value) for value in sensor["u_axis"]],
        "v_axis": [float(value) for value in sensor["v_axis"]],
    }
    if grid["width_m"] <= 0 or grid["depth_m"] <= 0 or grid["nx"] < 1 or grid["ny"] < 1:
        raise ValueError("sensor plane dimensions and resolution must be positive")

    channels: dict[str, dict] = {}
    for emitter in entities.get("emitter", []):
        if not emitter.get("enabled", False):
            continue
        channel_id = str(emitter["channel"])
        wavelength = float(emitter["wavelength_nm"])
        power = float(emitter["radiant_power_w"])
        exponent = float(emitter["beam_exponent"])
        if not 1.0 <= wavelength <= 10000.0:
            raise ValueError(f"{emitter['path']}: wavelength is out of bounds")
        if power < 0.0 or power > 10000.0:
            raise ValueError(f"{emitter['path']}: radiant power is out of bounds")
        if exponent < 0.0 or exponent > 1000.0:
            raise ValueError(f"{emitter['path']}: beam exponent is out of bounds")
        channel = channels.setdefault(channel_id, {
            "id": channel_id, "wavelength_nm": wavelength, "emitters": [],
        })
        if channel["wavelength_nm"] != wavelength:
            raise ValueError(f"channel {channel_id!r} contains inconsistent wavelengths")
        channel["emitters"].append({
            "source_path": emitter["path"],
            "position_m": [float(value) for value in emitter["position_m"]],
            "direction": [float(value) for value in emitter["direction"]],
            "radiant_power_w": power,
            "beam_exponent": exponent,
        })
    if not channels:
        raise ValueError("stage has no enabled emitters")
    occluders = []
    for occluder in entities.get("occluder", []):
        if occluder.get("shape") != "box":
            raise ValueError(f"{occluder['path']}: unsupported occluder shape")
        half_extents = [float(value) for value in occluder["half_extents_m"]]
        if len(half_extents) != 3 or any(value <= 0 for value in half_extents):
            raise ValueError(f"{occluder['path']}: invalid half extents")
        occluders.append({
            "source_path": occluder["path"],
            "enabled": bool(occluder["enabled"]),
            "shape": "box",
            "center_m": [float(value) for value in occluder["center_m"]],
            "axes": [[float(value) for value in axis] for axis in occluder["axes"]],
            "half_extents_m": half_extents,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "grid": grid,
        "channels": list(channels.values()),
        "occluders": occluders,
    }


def stage_to_solver_design(stage) -> dict:
    """Discover a live USD stage and return solver-compatible state."""
    return entities_to_solver_design(discover_stage(stage))
