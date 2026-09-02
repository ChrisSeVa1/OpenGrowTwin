"""Deterministic allowlisted tool dispatch for the OGT-204 copilot loop."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping

from .contracts import (
    MUTATING_TOOLS,
    TOOL_SCHEMAS_BY_NAME,
    ConfirmationStore,
    ContractError,
    validate_tool_call,
)
from .evidence import ApprovedEvidenceStore


ToolHandler = Callable[..., Any]


class ToolExecutionError(RuntimeError):
    """A validated call could not be executed inside the registered boundary."""


@dataclass(frozen=True)
class ToolExecutionResult:
    """JSON-compatible result returned by exactly one allowlisted handler."""

    name: str
    arguments: dict[str, Any]
    output: Any


class ToolExecutor:
    """Dispatch only validated tools to explicitly registered Python callables.

    No dynamic imports, attribute lookup, shell access, file paths, or arbitrary
    Python are accepted. Mutations additionally consume a short-lived token
    bound to their exact arguments.
    """

    def __init__(
        self,
        handlers: Mapping[str, ToolHandler] | None = None,
        *,
        evidence_store: ApprovedEvidenceStore | None = None,
        confirmation_store: ConfirmationStore | None = None,
    ):
        self._handlers: dict[str, ToolHandler] = {}
        self._evidence_store = evidence_store or ApprovedEvidenceStore()
        self._confirmations = confirmation_store or ConfirmationStore()
        self.register("list_targets", self._evidence_store.list_targets)
        self.register("get_target", self._evidence_store.get_target)
        self.register("propose_configuration", self._propose_configuration)
        for name, handler in (handlers or {}).items():
            self.register(name, handler)

    @property
    def registered_tools(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def register(self, name: str, handler: ToolHandler) -> None:
        if name not in TOOL_SCHEMAS_BY_NAME:
            raise ToolExecutionError(f"cannot register unknown tool {name!r}")
        if not callable(handler):
            raise TypeError("tool handler must be callable")
        self._handlers[name] = handler

    def issue_confirmation(self, name: str, arguments: dict[str, Any]) -> str:
        """Issue a token after the UI has obtained explicit user approval."""
        return self._confirmations.issue(name, arguments)

    @staticmethod
    def _propose_configuration(action: str, reason: str) -> dict[str, Any]:
        return {
            "action": action,
            "reason": reason,
            "status": "proposal_only",
            "scene_changed": False,
            "requires_explicit_confirmation": True,
        }

    @staticmethod
    def _require_json_compatible(value: Any) -> Any:
        try:
            encoded = json.dumps(value, allow_nan=False, sort_keys=True)
            return json.loads(encoded)
        except (TypeError, ValueError) as exc:
            raise ToolExecutionError("tool result must be finite JSON-compatible data") from exc

    def execute(self, name: str, arguments: Any) -> ToolExecutionResult:
        """Validate again, enforce confirmation, and invoke one handler."""
        try:
            if name in MUTATING_TOOLS:
                validated = self._confirmations.consume(name, arguments)
            else:
                validated = validate_tool_call(name, arguments)
        except ContractError as exc:
            raise ToolExecutionError(f"tool call rejected: {exc}") from exc

        handler = self._handlers.get(name)
        if handler is None:
            raise ToolExecutionError(f"no implementation registered for {name!r}")

        handler_arguments = dict(validated)
        handler_arguments.pop("confirmation_token", None)
        try:
            output = handler(**handler_arguments)
        except ToolExecutionError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"{name} handler failed: {exc}") from exc
        return ToolExecutionResult(
            name=name,
            arguments=dict(validated),
            output=self._require_json_compatible(output),
        )
