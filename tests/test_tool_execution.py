import math

import pytest

from opengrow.copilot.execution import ToolExecutionError, ToolExecutor


def test_builtin_evidence_tools_execute_inside_allowlist():
    executor = ToolExecutor()
    listed = executor.execute("list_targets", {})
    assert listed.output[0]["target_id"] == "phalaenopsis_ouzounis_2015_reference"

    target = executor.execute(
        "get_target",
        {"target_id": "phalaenopsis_ouzounis_2015_reference"},
    )
    assert target.output["source"]["citation"]["doi"] == "10.1111/ppl.12300"


def test_unregistered_tool_is_not_executed():
    executor = ToolExecutor()
    with pytest.raises(ToolExecutionError, match="no implementation registered"):
        executor.execute("inspect_scene", {})


def test_cannot_register_unknown_tool():
    with pytest.raises(ToolExecutionError, match="unknown tool"):
        ToolExecutor({"run_python": lambda: None})


def test_handler_arguments_are_validated_before_invocation():
    invoked = False

    def handler(run_id):
        nonlocal invoked
        invoked = True
        return {"run_id": run_id}

    executor = ToolExecutor({"get_metrics": handler})
    with pytest.raises(ToolExecutionError, match="rejected"):
        executor.execute("get_metrics", {"run_id": "../../secret"})
    assert invoked is False


def test_confirmed_mutation_is_exact_and_single_use():
    received = []

    def set_power(fixture_id, channel_id, radiant_power_w):
        received.append((fixture_id, channel_id, radiant_power_w))
        return {"scene_changed": True}

    executor = ToolExecutor({"set_channel_power": set_power})
    arguments = {
        "fixture_id": "fixture_01",
        "channel_id": "blue",
        "radiant_power_w": 4.5,
    }
    token = executor.issue_confirmation("set_channel_power", arguments)
    confirmed = {**arguments, "confirmation_token": token}

    result = executor.execute("set_channel_power", confirmed)
    assert result.output == {"scene_changed": True}
    assert received == [("fixture_01", "blue", 4.5)]

    with pytest.raises(ToolExecutionError, match="valid unused"):
        executor.execute("set_channel_power", confirmed)
    assert len(received) == 1


def test_mutation_token_cannot_authorize_changed_arguments():
    invoked = False

    def set_power(**arguments):
        nonlocal invoked
        invoked = True
        return arguments

    executor = ToolExecutor({"set_channel_power": set_power})
    arguments = {
        "fixture_id": "fixture_01",
        "channel_id": "blue",
        "radiant_power_w": 4.5,
    }
    token = executor.issue_confirmation("set_channel_power", arguments)
    changed = {
        **arguments,
        "radiant_power_w": 5.0,
        "confirmation_token": token,
    }
    with pytest.raises(ToolExecutionError, match="does not match"):
        executor.execute("set_channel_power", changed)
    assert invoked is False


def test_non_json_handler_result_is_rejected():
    executor = ToolExecutor({"inspect_scene": lambda: {"mean": math.nan}})
    with pytest.raises(ToolExecutionError, match="finite JSON-compatible"):
        executor.execute("inspect_scene", {})


def test_proposal_is_non_mutating():
    executor = ToolExecutor()
    result = executor.execute("propose_configuration", {
        "action": "set_channel_power",
        "reason": "Compare a bounded candidate.",
    })
    assert result.output["scene_changed"] is False
    assert result.output["requires_explicit_confirmation"] is True
