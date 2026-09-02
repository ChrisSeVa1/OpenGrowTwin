import json

import pytest

from opengrow.copilot.model_service import (
    ModelServiceClient,
    ModelServiceError,
)


def _tool_response(name="inspect_scene", arguments=None):
    if arguments is None:
        arguments = {}
    return {
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(arguments),
                    },
                }],
            },
        }],
        "usage": {"total_tokens": 10},
        "timings": {"predicted_per_second": 75.0},
    }


def test_rejects_non_loopback_endpoint():
    with pytest.raises(ModelServiceError, match="loopback-only"):
        ModelServiceClient(endpoint="http://example.com:8080")


def test_accepts_localhost_and_ipv6_loopback():
    assert ModelServiceClient(endpoint="http://localhost:8080").endpoint == "http://localhost:8080"
    assert ModelServiceClient(endpoint="http://[::1]:8080").endpoint == "http://[::1]:8080"


def test_parses_and_validates_exactly_one_tool_call(monkeypatch):
    client = ModelServiceClient()
    monkeypatch.setattr(client, "_post", lambda payload: _tool_response())
    call = client.request_tool_call("Inspect the scene.")
    assert call.call_id == "call_123"
    assert call.name == "inspect_scene"
    assert call.arguments == {}
    assert call.usage == {"total_tokens": 10}


def test_rejects_unknown_model_tool(monkeypatch):
    client = ModelServiceClient()
    monkeypatch.setattr(
        client,
        "_post",
        lambda payload: _tool_response("run_python", {"code": "print('unsafe')"}),
    )
    with pytest.raises(ModelServiceError, match="OGT-201 validation"):
        client.request_tool_call("Run Python.")


def test_rejects_ordinary_prose_instead_of_tool_call(monkeypatch):
    client = ModelServiceClient()
    monkeypatch.setattr(client, "_post", lambda payload: {
        "choices": [{
            "finish_reason": "stop",
            "message": {"role": "assistant", "content": "The PPFD is probably 200."},
        }],
    })
    with pytest.raises(ModelServiceError, match="did not finish with a tool call"):
        client.request_tool_call("What is the PPFD?")


def test_rejects_malformed_arguments(monkeypatch):
    client = ModelServiceClient()
    response = _tool_response()
    response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{bad"
    monkeypatch.setattr(client, "_post", lambda payload: response)
    with pytest.raises(ModelServiceError, match="not valid JSON"):
        client.request_tool_call("Inspect the scene.")


def test_grounded_answer_sends_tool_result_and_returns_text(monkeypatch):
    client = ModelServiceClient()
    captured = {}

    def post(payload):
        captured.update(payload)
        return {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "The authoritative mean PPFD is 76.5.",
                },
            }],
            "usage": {"total_tokens": 20},
        }

    monkeypatch.setattr(client, "_post", post)
    call_response = _tool_response("get_metrics", {"run_id": "run_baseline"})
    call_message = call_response["choices"][0]["message"]["tool_calls"][0]
    from opengrow.copilot.model_service import ModelToolCall
    call = ModelToolCall(
        call_id=call_message["id"],
        name="get_metrics",
        arguments={"run_id": "run_baseline"},
        latency_s=0.1,
        usage={},
        timings={},
    )
    answer = client.request_grounded_answer(
        "What is the mean PPFD?",
        call,
        {"mean_ppfd_umol_m2_s": 76.5},
    )

    assert answer.content == "The authoritative mean PPFD is 76.5."
    assert "tools" not in captured
    assert captured["messages"][-1]["role"] == "tool"
    assert json.loads(captured["messages"][-1]["content"]) == {
        "mean_ppfd_umol_m2_s": 76.5,
    }


def test_grounded_answer_rejects_another_tool_call(monkeypatch):
    client = ModelServiceClient()
    monkeypatch.setattr(client, "_post", lambda payload: _tool_response())
    from opengrow.copilot.model_service import ModelToolCall
    call = ModelToolCall(
        call_id="call_123",
        name="inspect_scene",
        arguments={},
        latency_s=0.1,
        usage={},
        timings={},
    )
    with pytest.raises(ModelServiceError, match="finish cleanly"):
        client.request_grounded_answer("Inspect.", call, {"fixtures": 1})


def test_model_can_return_unsigned_mutation_proposal(monkeypatch):
    client = ModelServiceClient()
    arguments = {
        "fixture_id": "fixture_01",
        "channel_id": "blue",
        "radiant_power_w": 4.5,
    }
    monkeypatch.setattr(
        client,
        "_post",
        lambda payload: _tool_response("set_channel_power", arguments),
    )
    call = client.request_tool_call("Set blue power to 4.5 watts.")
    assert call.name == "set_channel_power"
    assert call.arguments == arguments
