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
    from pxr import UsdGeom  # available in NVIDIA Kit

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
        if role == "emitter":
            transform = cache.GetLocalToWorldTransform(prim)
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
        entities[role].append(record)

    required_roles = ("fixture", "emitter", "sensorPlane", "occluder")
    missing = [role for role in required_roles if not entities[role]]
    if missing:
        raise ValueError(f"stage is missing required roles: {', '.join(missing)}")
    return {"schema_version": str(version), "entities": entities}
