import pytest

from opengrow.copilot.contracts import (
    ConfirmationStore,
    ContractError,
    MODEL_TOOL_SCHEMAS,
    MUTATING_TOOLS,
    TOOL_SCHEMAS,
    validate_tool_call,
    validate_tool_proposal,
)


def test_tool_names_are_unique_and_schemas_are_strict():
    names = [tool["function"]["name"] for tool in TOOL_SCHEMAS]
    assert len(names) == len(set(names))
    assert all(tool["function"]["parameters"]["additionalProperties"] is False for tool in TOOL_SCHEMAS)


def test_unknown_tool_and_arguments_are_rejected():
    with pytest.raises(ContractError, match="unknown tool"):
        validate_tool_call("run_python", {"code": "print('unsafe')"})
    with pytest.raises(ContractError, match="unknown arguments"):
        validate_tool_call("inspect_scene", {"usd_path": "/World/Secret"})


def test_arbitrary_paths_and_unapproved_identifiers_are_rejected():
    with pytest.raises(ContractError, match="approved identifier"):
        validate_tool_call("get_target", {"target_id": "../../private/target.yaml"})
    with pytest.raises(ContractError, match="approved identifier"):
        validate_tool_call("set_fixture_transform", {
            "fixture_id": "/World/GrowInstallation/Fixtures/Fixture_01",
            "preset": "baseline",
            "confirmation_token": "x" * 32,
        })


def test_channel_specific_power_bounds_are_enforced():
    with pytest.raises(ContractError, match="exceeds far_red bounds"):
        validate_tool_call("set_channel_power", {
            "fixture_id": "fixture_01",
            "channel_id": "far_red",
            "radiant_power_w": 20.1,
            "confirmation_token": "x" * 32,
        })


def test_mutation_without_confirmation_is_rejected():
    with pytest.raises(ContractError, match="confirmation_token"):
        validate_tool_call("apply_target", {
            "target_id": "phalaenopsis_ouzounis_2015_reference",
        })


def test_confirmation_is_bound_to_exact_arguments_and_single_use():
    store = ConfirmationStore()
    proposal = {
        "fixture_id": "fixture_01",
        "channel_id": "blue",
        "radiant_power_w": 12.5,
    }
    token = store.issue("set_channel_power", proposal)
    confirmed = {**proposal, "confirmation_token": token}
    assert store.consume("set_channel_power", confirmed) == confirmed
    with pytest.raises(ContractError, match="valid unused"):
        store.consume("set_channel_power", confirmed)


def test_confirmation_cannot_authorize_changed_arguments():
    store = ConfirmationStore()
    token = store.issue("set_fixture_transform", {
        "fixture_id": "fixture_01", "preset": "right_100mm",
    })
    with pytest.raises(ContractError, match="does not match"):
        store.consume("set_fixture_transform", {
            "fixture_id": "fixture_01",
            "preset": "left_100mm",
            "confirmation_token": token,
        })


def test_expired_confirmation_is_rejected():
    now = [100.0]
    store = ConfirmationStore(ttl_s=5.0, clock=lambda: now[0])
    args = {"target_id": "phalaenopsis_ouzounis_2015_reference"}
    token = store.issue("apply_target", args)
    now[0] = 106.0
    with pytest.raises(ContractError, match="expired"):
        store.consume("apply_target", {**args, "confirmation_token": token})


def test_controlled_execution_has_enum_only_modes():
    assert validate_tool_call("run_simulation", {"mode": "preview"})["mode"] == "preview"
    with pytest.raises(ContractError, match="approved identifier"):
        validate_tool_call("run_simulation", {"mode": "shell"})


def test_model_mutation_schemas_are_unsigned_proposals():
    by_name = {tool["function"]["name"]: tool for tool in MODEL_TOOL_SCHEMAS}
    for name in MUTATING_TOOLS:
        function = by_name[name]["function"]
        parameters = function["parameters"]
        assert "confirmation_token" not in parameters["properties"]
        assert "confirmation_token" not in parameters["required"]
        assert function["x-opengrow-effect"] == "proposal_requires_confirmation"


def test_model_can_propose_bounded_mutation_but_cannot_supply_token():
    arguments = {
        "fixture_id": "fixture_01",
        "channel_id": "blue",
        "radiant_power_w": 4.5,
    }
    assert validate_tool_proposal("set_channel_power", arguments) == arguments

    with pytest.raises(ContractError, match="unknown arguments"):
        validate_tool_proposal(
            "set_channel_power",
            {**arguments, "confirmation_token": "x" * 32},
        )

    with pytest.raises(ContractError, match="confirmation_token"):
        validate_tool_call("set_channel_power", arguments)
