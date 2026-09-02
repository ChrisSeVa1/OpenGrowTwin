"""Loopback-only OpenAI-compatible model client for OGT-203.

This module submits the frozen OGT-201 declarations and validates the returned
tool-call shape. It deliberately does not dispatch or execute tools; execution
belongs to OGT-204.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
import time
from typing import Any
from urllib import error, parse, request

from .contracts import TOOL_SCHEMAS, validate_tool_call


DEFAULT_ENDPOINT = "http://127.0.0.1:8080"
DEFAULT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M"
SYSTEM_PROMPT = (
    "You are the OpenGrowTwin scene assistant. Current scientific measurements "
    "and approved biological claims must come from the provided tools. Select "
    "exactly one relevant tool and never invent measurements, citations, paths, "
    "identifiers, or confirmation tokens."
)


class ModelServiceError(RuntimeError):
    """The local model service or its response violated the OGT-203 boundary."""


@dataclass(frozen=True)
class ModelToolCall:
    """One validated, non-executed model tool-call proposal."""

    call_id: str
    name: str
    arguments: dict[str, Any]
    latency_s: float
    usage: dict[str, Any]
    timings: dict[str, Any]


def _require_loopback(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    parsed = parse.urlparse(normalized)
    if parsed.scheme != "http" or not parsed.hostname:
        raise ModelServiceError("model endpoint must be an HTTP loopback URL")
    try:
        loopback = ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        loopback = parsed.hostname == "localhost"
    if not loopback:
        raise ModelServiceError("model endpoint must remain loopback-only")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ModelServiceError("model endpoint contains unsupported URL components")
    return normalized


class ModelServiceClient:
    """Minimal client for a local llama.cpp OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 30.0,
        api_key: str | None = None,
    ):
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.endpoint = _require_loopback(endpoint)
        self.model = model
        self.timeout_s = float(timeout_s)
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _read_json(self, req: request.Request) -> dict[str, Any]:
        try:
            with request.urlopen(req, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelServiceError(f"model service request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise ModelServiceError("model service response must be a JSON object")
        return payload

    def health(self) -> dict[str, Any]:
        req = request.Request(
            f"{self.endpoint}/health",
            headers=self._headers(),
            method="GET",
        )
        payload = self._read_json(req)
        if payload.get("status") != "ok":
            raise ModelServiceError("model service is not healthy")
        return payload

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            f"{self.endpoint}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        return self._read_json(req)

    def request_tool_call(
        self,
        prompt: str,
        *,
        system_prompt: str = SYSTEM_PROMPT,
        max_tokens: int = 256,
    ) -> ModelToolCall:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        started = time.monotonic()
        response = self._post({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "tools": list(TOOL_SCHEMAS),
            "tool_choice": "auto",
            "temperature": 0,
            "max_tokens": max_tokens,
        })
        latency_s = time.monotonic() - started

        choices = response.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise ModelServiceError("model response must contain exactly one choice")
        choice = choices[0]
        if choice.get("finish_reason") != "tool_calls":
            raise ModelServiceError("model did not finish with a tool call")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ModelServiceError("model response is missing the assistant message")
        if message.get("content") not in ("", None):
            raise ModelServiceError("tool-call response must not include ungrounded prose")

        calls = message.get("tool_calls")
        if not isinstance(calls, list) or len(calls) != 1:
            raise ModelServiceError("model must propose exactly one tool call")
        call = calls[0]
        function = call.get("function")
        if call.get("type") != "function" or not isinstance(function, dict):
            raise ModelServiceError("model returned an invalid function call")

        name = function.get("name")
        if not isinstance(name, str):
            raise ModelServiceError("tool call is missing a function name")
        raw_arguments = function.get("arguments")
        if isinstance(raw_arguments, str):
            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError as exc:
                raise ModelServiceError("tool arguments are not valid JSON") from exc
        else:
            arguments = raw_arguments
        try:
            validated = validate_tool_call(name, arguments)
        except (KeyError, ValueError) as exc:
            raise ModelServiceError(f"tool call failed OGT-201 validation: {exc}") from exc

        call_id = call.get("id")
        if not isinstance(call_id, str) or not call_id:
            raise ModelServiceError("tool call is missing an identifier")
        return ModelToolCall(
            call_id=call_id,
            name=name,
            arguments=validated,
            latency_s=latency_s,
            usage=response.get("usage") if isinstance(response.get("usage"), dict) else {},
            timings=response.get("timings") if isinstance(response.get("timings"), dict) else {},
        )
