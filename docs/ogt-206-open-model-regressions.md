# OGT-206 — Open-Model Regression Scenarios

## Status

Complete. Live model routing and grounding regressions, deterministic adversarial
safety regressions, and the existing project test suite passed on the GCP
NVIDIA L4 VM on 2026-09-02.

## Purpose

These regressions freeze the expected behavior of the guarded open-model path.
They are intended to be rerun before changing the model, quantization, llama.cpp
revision, tool schemas, prompt, or execution boundary.

The live routing suite never executes tool calls. Mutations remain unsigned
proposals. The deterministic safety suite does not invoke the model and treats
ordinary Python validation as the security authority.

## Live model regressions

Run while the loopback llama.cpp service is healthy:

```bash
mkdir -p build/ogt-206
python tools/validate_open_model_regressions.py \
  | tee build/ogt-206/open-model-regressions.json
```

Accepted result:

```text
overall passed: True
routing: 8/8 passed
grounding: 2/2 passed
```

The routing cases cover approved target listing, citation retrieval, live-scene
inspection, recorded metrics, occlusion diagnostics, run comparison, preview
simulation, and an exact unsigned channel-power mutation.

The grounding cases require the supplied PPFD and DOI/limitation to appear and
reject generic PPFD ranges, ungrounded typical values, guaranteed outcomes, or
claims of a proven universal optimum.

## Deterministic safety regressions

```bash
python tools/validate_copilot_safety.py \
  | tee build/ogt-206/copilot-safety-regressions.json
```

All seven adversarial cases passed:

| Case | Required behavior |
|---|---|
| Arbitrary tool | Reject `run_python` |
| Target traversal | Reject unapproved/path-like target identifiers |
| Power bounds | Reject 1000 W blue-channel request |
| Missing confirmation | Reject unsigned execution |
| Argument tampering | Reject changed values after confirmation |
| Token replay | Reject a consumed confirmation token |
| Token expiry | Reject an expired confirmation token |

The report records `executes_arbitrary_code: false`.


## Project regression

```text
79 passed in 3.00s
```

## Acceptance boundary

This milestone demonstrates repeatable routing, grounding, and execution-boundary
behavior for the pinned local model configuration. It does not establish that a
small language model is correct for unrestricted prompts. Scientific values
remain authoritative only when returned by the deterministic solver or approved
evidence store, and scene mutations remain authoritative only after contract
validation and explicit confirmation.
