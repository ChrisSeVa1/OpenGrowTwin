"""Bridge the deterministic optimizer to bounded live-USD mutation proposals."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import yaml

from .optimizer import optimize_design


REFERENCE_TARGET_PATH = Path(__file__).resolve().parents[3] / "data" / "targets" / "phalaenopsis_reference.yaml"


class LiveOptimizerError(ValueError):
    """A live optimizer proposal or application violated the OGT-302 contract."""


def load_reference_target(path: Path | None = None) -> dict:
    """Load the curated MVP optimization target used by the existing CLI optimizer."""
    target_path = Path(path) if path is not None else REFERENCE_TARGET_PATH
    try:
        target = yaml.safe_load(target_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise LiveOptimizerError(f"cannot load optimizer target {target_path}") from exc
    if not isinstance(target, dict) or "target" not in target or "photon_fraction" not in target:
        raise LiveOptimizerError("optimizer target is malformed")
    return target


def _channel_total(channel: dict) -> float:
    return float(sum(float(emitter["radiant_power_w"]) for emitter in channel["emitters"]))


def _finite_float(value, label: str) -> float:
    numeric = float(value)
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise LiveOptimizerError(f"{label} must be finite")
    return numeric


def build_optimizer_proposal(
    design: dict,
    target: dict,
    *,
    fixture_path: str,
    current_fixture_height_m: float,
    candidate_heights_m=None,
    objective: str = "target_uniformity_power",
) -> dict:
    """Return an exact, JSON-compatible proposal without changing the scene."""
    if objective != "target_uniformity_power":
        raise LiveOptimizerError(f"unsupported optimizer objective {objective!r}")
    if not isinstance(fixture_path, str) or not fixture_path.startswith("/World/"):
        raise LiveOptimizerError("fixture_path must be an absolute OpenUSD path under /World")

    optimized = optimize_design(design, target, candidate_heights_m=candidate_heights_m)
    optimized_by_id = {channel["id"]: channel for channel in optimized["design"]["channels"]}
    changes = []
    for channel in design["channels"]:
        channel_id = str(channel["id"])
        if channel_id not in optimized_by_id:
            raise LiveOptimizerError(f"optimized design is missing channel {channel_id!r}")
        proposed_channel = optimized_by_id[channel_id]
        before_total = _channel_total(channel)
        after_total = _channel_total(proposed_channel)
        emitters = []
        if len(channel["emitters"]) != len(proposed_channel["emitters"]):
            raise LiveOptimizerError(f"channel {channel_id!r} emitter count changed during optimization")
        for before, after in zip(channel["emitters"], proposed_channel["emitters"], strict=True):
            source_path = before.get("source_path")
            if not isinstance(source_path, str) or not source_path.startswith(fixture_path + "/"):
                raise LiveOptimizerError(f"channel {channel_id!r} emitter lacks an approved fixture-local source path")
            emitters.append({
                "path": source_path,
                "before_radiant_power_w": _finite_float(before["radiant_power_w"], "before radiant power"),
                "after_radiant_power_w": _finite_float(after["radiant_power_w"], "after radiant power"),
            })
        changes.append({
            "channel_id": channel_id,
            "before_total_radiant_power_w": before_total,
            "after_total_radiant_power_w": after_total,
            "emitters": emitters,
        })

    payload = {
        "schema_version": "1.0",
        "task": "OGT-302",
        "objective": objective,
        "fixture_path": fixture_path,
        "before_fixture_height_m": _finite_float(current_fixture_height_m, "current fixture height"),
        "after_fixture_height_m": _finite_float(optimized["height_m"], "optimized fixture height"),
        "channel_changes": changes,
        "predicted_metrics": {key: _finite_float(value, f"metric {key}") for key, value in optimized["metrics"].items()},
        "target_id": str(target.get("id", "unknown")),
        "requires_explicit_confirmation": True,
        "scene_changed": False,
        "status": "proposal_only",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["proposal_id"] = "opt_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return payload


def apply_optimizer_proposal(stage, proposal: dict) -> dict:
    """Apply one previously reviewed exact proposal to an already-open stage.

    This function performs no optimization and accepts no free-form model output.
    The caller is responsible for obtaining explicit user confirmation before
    invoking it.
    """
    if proposal.get("task") != "OGT-302" or proposal.get("status") != "proposal_only":
        raise LiveOptimizerError("only an OGT-302 proposal_only record can be applied")
    if proposal.get("requires_explicit_confirmation") is not True:
        raise LiveOptimizerError("optimizer proposal must require explicit confirmation")
    fixture_path = proposal.get("fixture_path")
    if not isinstance(fixture_path, str) or not fixture_path.startswith("/World/"):
        raise LiveOptimizerError("optimizer proposal has an invalid fixture path")

    fixture = stage.GetPrimAtPath(fixture_path)
    translate = fixture.GetAttribute("xformOp:translate") if fixture else None
    current_translation = translate.Get() if translate else None
    if current_translation is None or len(current_translation) != 3:
        raise LiveOptimizerError(f"{fixture_path}: expected authored xformOp:translate")
    before_height = _finite_float(current_translation[2], "fixture height")
    expected_before = _finite_float(proposal["before_fixture_height_m"], "proposal before height")
    if abs(before_height - expected_before) > 1e-9:
        raise LiveOptimizerError("live fixture height changed since the optimizer proposal was created")

    emitter_updates = []
    for channel in proposal.get("channel_changes", []):
        for emitter in channel.get("emitters", []):
            path = emitter.get("path")
            if not isinstance(path, str) or not path.startswith(fixture_path + "/"):
                raise LiveOptimizerError("proposal contains an emitter outside the approved fixture")
            prim = stage.GetPrimAtPath(path)
            attribute = prim.GetAttribute("opengrow:radiantPowerW") if prim else None
            current = attribute.Get() if attribute else None
            if current is None:
                raise LiveOptimizerError(f"{path}: missing opengrow:radiantPowerW")
            expected = _finite_float(emitter["before_radiant_power_w"], "proposal before radiant power")
            if abs(float(current) - expected) > 1e-9:
                raise LiveOptimizerError(f"{path}: radiant power changed since proposal creation")
            emitter_updates.append((attribute, _finite_float(emitter["after_radiant_power_w"], "proposal radiant power")))

    after_height = _finite_float(proposal["after_fixture_height_m"], "proposal after height")
    translate.Set((float(current_translation[0]), float(current_translation[1]), after_height))
    for attribute, value in emitter_updates:
        attribute.Set(value)

    return {
        "proposal_id": proposal.get("proposal_id"),
        "fixture_path": fixture_path,
        "before_fixture_height_m": before_height,
        "after_fixture_height_m": after_height,
        "emitter_updates": len(emitter_updates),
        "scene_changed": True,
        "simulation_required": True,
    }
