"""Kit UI state machine for the guarded OpenGrowTwin copilot."""

from __future__ import annotations

import asyncio
import functools
import json
from typing import Callable, Mapping

import carb
import omni.ui as ui

from opengrow.copilot.contracts import MUTATING_TOOLS
from opengrow.copilot.execution import ToolExecutor
from opengrow.copilot.model_service import ModelServiceClient, ModelToolCall


class CopilotPanel:
    """One-turn model UI with an explicit mutation confirmation gate."""

    def __init__(self, handlers: Mapping[str, Callable]):
        self._executor = ToolExecutor(handlers)
        self._client = ModelServiceClient()
        self._task = None
        self._pending: tuple[str, ModelToolCall] | None = None
        self._input_model = ui.SimpleStringModel("")
        self._status = None
        self._answer = None
        self._confirm_button = None
        self._reject_button = None

    def build(self) -> None:
        ui.Separator(height=8)
        ui.Label("Local Nemotron Copilot", height=24)
        ui.Label("Ask about the live scene, runs, or approved evidence.", word_wrap=True)
        ui.StringField(self._input_model, height=28)
        with ui.HStack(height=32, spacing=8):
            ui.Button("Ask", clicked_fn=self._ask)
            ui.Button("Clear", clicked_fn=self._clear)
        self._status = ui.Label("Model endpoint: 127.0.0.1:8080", word_wrap=True, height=38)
        self._answer = ui.Label("No copilot conversation yet.", word_wrap=True, height=120)
        with ui.HStack(height=32, spacing=8):
            self._confirm_button = ui.Button(
                "Confirm exact change",
                clicked_fn=self._confirm,
                enabled=False,
            )
            self._reject_button = ui.Button(
                "Reject",
                clicked_fn=self._reject,
                enabled=False,
            )

    def shutdown(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._pending = None

    def _set_pending_enabled(self, enabled: bool) -> None:
        if self._confirm_button:
            self._confirm_button.enabled = enabled
        if self._reject_button:
            self._reject_button.enabled = enabled

    def _set_status(self, text: str) -> None:
        if self._status:
            self._status.text = text

    def _set_answer(self, text: str) -> None:
        if self._answer:
            self._answer.text = text

    def _clear(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
        self._pending = None
        self._set_pending_enabled(False)
        self._input_model.set_value("")
        self._set_status("Ready")
        self._set_answer("No copilot conversation yet.")

    def _ask(self) -> None:
        prompt = self._input_model.as_string.strip()
        if not prompt:
            self._set_status("Enter a question or bounded request.")
            return
        if self._task and not self._task.done():
            self._set_status("Wait for the current copilot request.")
            return
        self._pending = None
        self._set_pending_enabled(False)
        self._task = asyncio.ensure_future(self._plan(prompt))

    async def _plan(self, prompt: str) -> None:
        try:
            self._set_status("Nemotron is selecting an allowlisted tool…")
            loop = asyncio.get_running_loop()
            call = await loop.run_in_executor(
                None,
                self._client.request_tool_call,
                prompt,
            )
            if call.name in MUTATING_TOOLS:
                self._pending = (prompt, call)
                self._set_pending_enabled(True)
                self._set_status("Confirmation required — no scene change has occurred.")
                self._set_answer(
                    "Proposed tool: "
                    + call.name
                    + "\nExact arguments:\n"
                    + json.dumps(call.arguments, indent=2, sort_keys=True)
                )
                return
            execution = self._executor.execute(call.name, call.arguments)
            await self._ground(prompt, call, execution.output)
        except asyncio.CancelledError:
            self._set_status("Copilot request cancelled.")
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Copilot failed: {exc}")
            self._set_status(f"Copilot error: {exc}")

    def _confirm(self) -> None:
        if self._pending is None:
            self._set_status("No exact mutation is awaiting confirmation.")
            return
        prompt, call = self._pending
        self._pending = None
        self._set_pending_enabled(False)
        try:
            token = self._executor.issue_confirmation(call.name, call.arguments)
            confirmed = {**call.arguments, "confirmation_token": token}
            execution = self._executor.execute(call.name, confirmed)
            self._set_status("Confirmed change executed; generating grounded response…")
            self._task = asyncio.ensure_future(
                self._ground(prompt, call, execution.output)
            )
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Confirmed copilot action failed: {exc}")
            self._set_status(f"Confirmation failed: {exc}")

    def _reject(self) -> None:
        if self._pending is None:
            return
        name = self._pending[1].name
        self._pending = None
        self._set_pending_enabled(False)
        self._set_status("Proposal rejected — no scene change occurred.")
        self._set_answer(f"Rejected proposed tool: {name}")

    async def _ground(self, prompt: str, call: ModelToolCall, output) -> None:
        try:
            self._set_status("Generating answer from authoritative tool output…")
            loop = asyncio.get_running_loop()
            answer = await loop.run_in_executor(
                None,
                functools.partial(
                    self._client.request_grounded_answer,
                    prompt,
                    call,
                    output,
                ),
            )
            self._set_answer(answer.content)
            self._set_status(
                f"Complete — {call.name}; "
                f"plan {call.latency_s:.2f}s, answer {answer.latency_s:.2f}s"
            )
        except asyncio.CancelledError:
            self._set_status("Copilot response cancelled.")
        except Exception as exc:
            carb.log_error(f"[OpenGrowTwin] Grounded response failed: {exc}")
            self._set_status(f"Grounded response error: {exc}")
