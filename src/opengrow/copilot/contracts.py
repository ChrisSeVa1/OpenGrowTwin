"""OGT-201 allowlisted Gemma tool schemas and deterministic safety rules.

The model receives these JSON-compatible declarations. Validation happens in
ordinary Python before any tool implementation is invoked, keeping model output
away from arbitrary Python, shell commands, file paths, and USD prim paths.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import secrets
import time
from typing import Any, Callable


TARGET_IDS = ("phalaenopsis_ouzounis_2015_reference",)
FIXTURE_IDS = ("fixture_01",)
CHANNEL_IDS = ("blue", "red", "far_red")
TRANSFORM_PRESETS = ("baseline", "left_100mm", "right_100mm", "raise_100mm")
SIMULATION_MODES = ("preview", "final")
OPTIMIZER_OBJECTIVES = ("target_uniformity_power",)

CHANNEL_POWER_BOUNDS_W = {
    "blue": (0.0, 100.0),
    "red": (0.0, 100.0),
    "far_red": (0.0, 20.0),
}

MUTATING_TOOLS = frozenset({"apply_target", "set_channel_power", "set_fixture_transform"})
CONTROLLED_EXECUTION_TOOLS = frozenset({"run_simulation", "run_optimizer"})


class ContractError(ValueError):
    """A model-supplied tool call violated the frozen OGT-201 contract."""


def _object(properties: dict[str, dict], required: tuple[str, ...] = ()) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _tool(name: str, description: str, parameters: dict, *, effect: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
            "x-opengrow-effect": effect,
        },
    }


_TOKEN = {"type": "string", "minLength": 32, "maxLength": 256}
_RUN_ID = {"type": "string", "pattern": r"^run_[A-Za-z0-9_-]{1,64}$"}

TOOL_SCHEMAS = (
    _tool("list_targets", "List approved evidence-backed plant-lighting targets.", _object({}), effect="read"),
    _tool(
        "get_target",
        "Retrieve one approved target, its citation, conditions, and limitations.",
        _object({"target_id": {"type": "string", "enum": list(TARGET_IDS)}}, ("target_id",)),
        effect="read",
    ),
    _tool("inspect_scene", "Return a compact semantic summary of the live OpenUSD scene.", _object({}), effect="read"),
    _tool(
        "get_metrics",
        "Return deterministic solver metrics for a recorded run.",
        _object({"run_id": _RUN_ID}, ("run_id",)),
        effect="read",
    ),
    _tool(
        "get_occlusion_summary",
        "Return solver-produced blocked-ray diagnostics for a recorded run.",
        _object({"run_id": _RUN_ID}, ("run_id",)),
        effect="read",
    ),
    _tool(
        "compare_runs",
        "Deterministically compare metrics from two recorded runs.",
        _object({"baseline_run_id": _RUN_ID, "candidate_run_id": _RUN_ID},
                ("baseline_run_id", "candidate_run_id")),
        effect="read",
    ),
    _tool(
        "propose_configuration",
        "Validate and present one bounded action without changing the scene.",
        _object({
            "action": {"type": "string", "enum": ["apply_target", "set_channel_power", "set_fixture_transform"]},
            "reason": {"type": "string", "minLength": 1, "maxLength": 500},
        }, ("action", "reason")),
        effect="proposal",
    ),
    _tool(
        "apply_target",
        "Apply an approved evidence target after explicit user confirmation.",
        _object({
            "target_id": {"type": "string", "enum": list(TARGET_IDS)},
            "confirmation_token": _TOKEN,
        }, ("target_id", "confirmation_token")),
        effect="mutation_requires_confirmation",
    ),
    _tool(
        "set_channel_power",
        "Set total fixture-channel radiant power within authored bounds after confirmation.",
        _object({
            "fixture_id": {"type": "string", "enum": list(FIXTURE_IDS)},
            "channel_id": {"type": "string", "enum": list(CHANNEL_IDS)},
            "radiant_power_w": {"type": "number", "minimum": 0.0, "maximum": 100.0},
            "confirmation_token": _TOKEN,
        }, ("fixture_id", "channel_id", "radiant_power_w", "confirmation_token")),
        effect="mutation_requires_confirmation",
    ),
    _tool(
        "set_fixture_transform",
        "Apply a predefined fixture pose after explicit user confirmation.",
        _object({
            "fixture_id": {"type": "string", "enum": list(FIXTURE_IDS)},
            "preset": {"type": "string", "enum": list(TRANSFORM_PRESETS)},
            "confirmation_token": _TOKEN,
        }, ("fixture_id", "preset", "confirmation_token")),
        effect="mutation_requires_confirmation",
    ),
    _tool(
        "run_simulation",
        "Run the deterministic solver using the current live scene.",
        _object({"mode": {"type": "string", "enum": list(SIMULATION_MODES)}}, ("mode",)),
        effect="controlled_execution",
    ),
    _tool(
        "run_optimizer",
        "Run the bounded deterministic installation optimizer.",
        _object({"objective": {"type": "string", "enum": list(OPTIMIZER_OBJECTIVES)}}, ("objective",)),
        effect="controlled_execution",
    ),
)

TOOL_SCHEMAS_BY_NAME = {
    declaration["function"]["name"]: declaration for declaration in TOOL_SCHEMAS
}


def _validate_value(value: Any, schema: dict, path: str) -> None:
    expected = schema.get("type")
    if expected == "string":
        if not isinstance(value, str):
            raise ContractError(f"{path} must be a string")
        if len(value) < schema.get("minLength", 0):
            raise ContractError(f"{path} is too short")
        if len(value) > schema.get("maxLength", float("inf")):
            raise ContractError(f"{path} is too long")
        if "enum" in schema and value not in schema["enum"]:
            raise ContractError(f"{path} is not an approved identifier")
        if "pattern" in schema:
            import re
            if re.fullmatch(schema["pattern"], value) is None:
                raise ContractError(f"{path} has an invalid identifier format")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContractError(f"{path} must be numeric")
        numeric = float(value)
        if numeric < schema.get("minimum", float("-inf")) or numeric > schema.get("maximum", float("inf")):
            raise ContractError(f"{path} is out of bounds")
    else:
        raise RuntimeError(f"unsupported contract schema type {expected!r}")


def _validate_arguments(name: str, arguments: Any, *, confirmation_required: bool) -> dict:
    if not isinstance(arguments, dict):
        raise ContractError("tool arguments must be an object")
    schema = TOOL_SCHEMAS_BY_NAME[name]["function"]["parameters"]
    properties = schema["properties"]
    allowed = set(properties)
    required = set(schema["required"])
    if not confirmation_required:
        required.discard("confirmation_token")
        allowed.discard("confirmation_token")
    unknown = set(arguments) - allowed
    if unknown:
        raise ContractError(f"{name} contains unknown arguments: {', '.join(sorted(unknown))}")
    missing = required - set(arguments)
    if missing:
        raise ContractError(f"{name} is missing required arguments: {', '.join(sorted(missing))}")
    for key, value in arguments.items():
        _validate_value(value, properties[key], f"{name}.{key}")
    if name == "set_channel_power":
        channel = arguments.get("channel_id")
        if channel is not None:
            minimum, maximum = CHANNEL_POWER_BOUNDS_W[channel]
            power = float(arguments.get("radiant_power_w", minimum))
            if not minimum <= power <= maximum:
                raise ContractError(f"set_channel_power.radiant_power_w exceeds {channel} bounds")
    return dict(arguments)


def validate_tool_call(name: str, arguments: Any) -> dict:
    """Validate a non-mutating call or the shape of a confirmed mutation.

    Confirmation token authenticity is checked separately by ``ConfirmationStore``.
    """
    if name not in TOOL_SCHEMAS_BY_NAME:
        raise ContractError(f"unknown tool {name!r}")
    return _validate_arguments(name, arguments, confirmation_required=name in MUTATING_TOOLS)


def _argument_digest(name: str, arguments: dict) -> str:
    unsigned = {key: value for key, value in arguments.items() if key != "confirmation_token"}
    payload = json.dumps({"name": name, "arguments": unsigned}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _Confirmation:
    digest: str
    expires_at: float


class ConfirmationStore:
    """Issue short-lived, single-use tokens bound to one exact mutation."""

    def __init__(self, *, ttl_s: float = 300.0, clock: Callable[[], float] = time.monotonic):
        if ttl_s <= 0:
            raise ValueError("confirmation TTL must be positive")
        self._ttl_s = float(ttl_s)
        self._clock = clock
        self._pending: dict[str, _Confirmation] = {}

    def issue(self, name: str, arguments: dict) -> str:
        if name not in MUTATING_TOOLS:
            raise ContractError(f"{name!r} is not a confirmable mutation")
        clean = _validate_arguments(name, arguments, confirmation_required=False)
        token = secrets.token_urlsafe(32)
        self._pending[token] = _Confirmation(
            digest=_argument_digest(name, clean),
            expires_at=self._clock() + self._ttl_s,
        )
        return token

    def consume(self, name: str, arguments: dict) -> dict:
        validated = validate_tool_call(name, arguments)
        token = validated["confirmation_token"]
        confirmation = self._pending.pop(token, None)
        if confirmation is None:
            raise ContractError("mutation requires a valid unused confirmation token")
        if self._clock() > confirmation.expires_at:
            raise ContractError("confirmation token has expired")
        if confirmation.digest != _argument_digest(name, validated):
            raise ContractError("confirmation token does not match this mutation")
        return validated
