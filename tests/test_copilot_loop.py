import pytest

from opengrow.copilot.execution import ToolExecutionError, ToolExecutor
from opengrow.copilot.loop import ValidatedToolLoop
from opengrow.copilot.model_service import GroundedModelAnswer, ModelToolCall


class FakeClient:
    def __init__(self, call):
        self.call = call
        self.grounded_requests = []

    def request_tool_call(self, prompt):
        return self.call

    def request_grounded_answer(self, prompt, call, tool_output):
        self.grounded_requests.append((prompt, call, tool_output))
        return GroundedModelAnswer(
            content="One approved target is available.",
            latency_s=0.1,
            usage={},
            timings={},
        )


def _call(name="list_targets", arguments=None):
    return ModelToolCall(
        call_id="call_123",
        name=name,
        arguments={} if arguments is None else arguments,
        latency_s=0.1,
        usage={},
        timings={},
    )


def test_loop_executes_one_validated_tool_and_returns_grounded_answer():
    client = FakeClient(_call())
    result = ValidatedToolLoop(client, ToolExecutor()).run("List targets.")

    assert result.call.name == "list_targets"
    assert result.execution.name == "list_targets"
    assert result.execution.output[0]["target_id"] == "phalaenopsis_ouzounis_2015_reference"
    assert result.answer.content == "One approved target is available."
    assert client.grounded_requests[0][2] == result.execution.output


def test_handler_failure_prevents_final_model_request():
    client = FakeClient(_call("inspect_scene"))
    loop = ValidatedToolLoop(client, ToolExecutor())

    with pytest.raises(ToolExecutionError, match="no implementation"):
        loop.run("Inspect scene.")
    assert client.grounded_requests == []


def test_model_call_is_revalidated_at_execution_boundary():
    client = FakeClient(_call("get_metrics", {"run_id": "../../secret"}))
    invoked = False

    def handler(run_id):
        nonlocal invoked
        invoked = True
        return {"run_id": run_id}

    loop = ValidatedToolLoop(client, ToolExecutor({"get_metrics": handler}))
    with pytest.raises(ToolExecutionError, match="rejected"):
        loop.run("Read unsafe run.")
    assert invoked is False
    assert client.grounded_requests == []
