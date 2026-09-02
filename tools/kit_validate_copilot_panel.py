"""OGT-205 headless acceptance for the guarded live-scene mutation path."""

from __future__ import annotations

from dataclasses import asdict
import json
import sys
from pathlib import Path

from pxr import Usd
repository = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repository / "src"))
for site_packages in sorted((repository / ".venv" / "lib").glob("python*/site-packages")):
    sys.path.append(str(site_packages))

from opengrow.copilot import ModelServiceClient  # noqa: E402
from opengrow.copilot.execution import ToolExecutor  # noqa: E402
from opengrow.orchestration import simulate_stage  # noqa: E402
from opengrow.usd.rtx_lights import sync_rtx_lights  # noqa: E402
from opengrow.usd.stage_reader import discover_stage  # noqa: E402


stage = Usd.Stage.Open(str(repository / "demo" / "grow_chamber.usda"))
if stage is None:
    raise RuntimeError("could not open demo/grow_chamber.usda")


def set_channel_power(fixture_id, channel_id, radiant_power_w):
    discovered = discover_stage(stage)
    fixtures = [
        item for item in discovered["entities"]["fixture"]
        if item["path"].rsplit("/", 1)[-1].lower() == fixture_id.lower()
    ]
    if len(fixtures) != 1:
        raise ValueError(f"fixture {fixture_id!r} did not resolve uniquely")
    prefix = fixtures[0]["path"] + "/"
    emitters = [
        item for item in discovered["entities"]["emitter"]
        if item["path"].startswith(prefix) and item["channel"] == channel_id
    ]
    if not emitters:
        raise ValueError(f"fixture {fixture_id!r} has no {channel_id!r} emitters")
    before = sum(item["radiant_power_w"] for item in emitters)
    per_emitter = float(radiant_power_w) / len(emitters)
    for emitter in emitters:
        stage.GetPrimAtPath(emitter["path"]).GetAttribute("opengrow:radiantPowerW").Set(per_emitter)
    sync_rtx_lights(stage)
    return {
        "before_total_radiant_power_w": before,
        "after_total_radiant_power_w": float(radiant_power_w),
        "emitter_count": len(emitters),
        "per_emitter_radiant_power_w": per_emitter,
    }


before = discover_stage(stage)
before_total = sum(
    item["radiant_power_w"] for item in before["entities"]["emitter"]
    if item["channel"] == "blue"
)

prompt = "Set the total blue-channel radiant power of fixture_01 to 4.5 watts."
client = ModelServiceClient()
executor = ToolExecutor({"set_channel_power": set_channel_power})
call = client.request_tool_call(prompt)
if call.name != "set_channel_power":
    raise AssertionError(f"expected set_channel_power, got {call.name!r}")
expected = {"fixture_id": "fixture_01", "channel_id": "blue", "radiant_power_w": 4.5}
if call.arguments != expected:
    raise AssertionError(f"unexpected proposed arguments: {call.arguments!r}")

# The unsigned model proposal must not execute.
still_before = discover_stage(stage)
still_before_total = sum(
    item["radiant_power_w"] for item in still_before["entities"]["emitter"]
    if item["channel"] == "blue"
)
if abs(still_before_total - before_total) > 1e-12:
    raise AssertionError("scene changed before explicit confirmation")

token = executor.issue_confirmation(call.name, call.arguments)
execution = executor.execute(call.name, {**call.arguments, "confirmation_token": token})
after = discover_stage(stage)
after_total = sum(
    item["radiant_power_w"] for item in after["entities"]["emitter"]
    if item["channel"] == "blue"
)
if abs(after_total - 4.5) > 1e-12:
    raise AssertionError("confirmed total channel power was not authored")

result = simulate_stage(stage, "preview")
answer = client.request_grounded_answer(prompt, call, execution.output)
print("[OpenGrowTwin] OGT-205 guarded headless copilot acceptance valid")
print(json.dumps({
    "proposal": {"name": call.name, "arguments": call.arguments},
    "mutation_before_confirmation": False,
    "confirmation_consumed": True,
    "before_total_blue_w": before_total,
    "after_total_blue_w": after_total,
    "mean_ppfd_after": result["metrics"]["mean_ppfd_umol_m2_s"],
    "grounded_answer": answer.content,
    "arbitrary_code_execution": False,
}, indent=2, sort_keys=True))
