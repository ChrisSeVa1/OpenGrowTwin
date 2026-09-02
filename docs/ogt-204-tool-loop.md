# OGT-204 validated tool-execution loop

OGT-204 connects the OGT-203 model boundary to deterministic Python handlers.
It remains independent of Kit UI so the same safety rules can be unit-tested
without a GPU.

## One-turn boundary

Each user turn has exactly four steps:

1. the local model proposes exactly one OGT-201 tool call;
2. the call is parsed and validated by the model client;
3. `ToolExecutor` validates it again and invokes one explicitly registered
   handler;
4. the JSON-compatible result is returned as an OpenAI `tool` message, with
   tools omitted from the final request, and the model produces grounded text.

There is no autonomous multi-tool loop, dynamic import, arbitrary attribute
lookup, shell command, file path, or model-generated Python execution.

## Deterministic dispatch

`ToolExecutor` includes handlers for:

- `list_targets`;
- `get_target`;
- `propose_configuration`.

Scene inspection, run storage, simulation, optimization, and mutations require
explicit handler registration by the owning runtime. This prevents core Python
from pretending it owns Kit's main-thread stage.

Every handler result must round-trip through strict finite JSON. NumPy arrays,
NaN, infinity, custom objects, and other implicit serialization are rejected.

## Mutation confirmation

Mutation tools still use the OGT-201 `ConfirmationStore`. A UI must:

1. validate and display the exact unsigned mutation;
2. obtain explicit user approval;
3. call `issue_confirmation`;
4. submit the identical arguments with that token.

The executor consumes the token before calling the handler. Tokens are
short-lived, bound to an argument digest, and single-use. A changed or replayed
request never reaches the handler.

## Tests

Run without a model or GPU:

```bash
python -m pytest -q
```

The OGT-204 tests cover built-in evidence dispatch, unknown tools, unregistered
tools, validation before invocation, finite JSON results, proposals, exact
single-use confirmations, handler failure, and revalidation between the model
client and executor.

## Live acceptance

With the loopback Nemotron service running:

```bash
python tools/validate_tool_loop.py
```

The acceptance prompt asks for the publication supporting the approved
Phalaenopsis reference. A pass requires:

- a validated `get_target` call;
- the allowlisted target identifier;
- execution through `ApprovedEvidenceStore`;
- DOI `10.1111/ppl.12300` in both tool data and final model text;
- no universal-optimum or growth-maximization claim.

## Kit boundary

OGT-204 provides handler injection but does not access a USD stage by itself.
OGT-205 will register Kit-owned handlers and expose the loop through the
Copilot panel. USD reads and writes must remain on Kit's main thread; solver
work may continue on a background executor.

## Completion gate

OGT-204 is complete when the full unit suite and live grounded acceptance pass.
The branch must not merge merely because static model tool selection works:
the executed result must return to the model and constrain its final answer.
