"""Single-tool, validated model execution loop for OGT-204."""

from __future__ import annotations

from dataclasses import dataclass

from .execution import ToolExecutionResult, ToolExecutor
from .model_service import (
    GroundedModelAnswer,
    ModelServiceClient,
    ModelToolCall,
)


@dataclass(frozen=True)
class ToolLoopResult:
    """Auditable record of one user turn."""

    prompt: str
    call: ModelToolCall
    execution: ToolExecutionResult
    answer: GroundedModelAnswer


class ValidatedToolLoop:
    """Plan once, validate twice, execute once, then answer from the result."""

    def __init__(self, client: ModelServiceClient, executor: ToolExecutor):
        self._client = client
        self._executor = executor

    def run(self, prompt: str) -> ToolLoopResult:
        call = self._client.request_tool_call(prompt)
        execution = self._executor.execute(call.name, call.arguments)
        answer = self._client.request_grounded_answer(
            prompt,
            call,
            execution.output,
        )
        return ToolLoopResult(
            prompt=prompt,
            call=call,
            execution=execution,
            answer=answer,
        )
