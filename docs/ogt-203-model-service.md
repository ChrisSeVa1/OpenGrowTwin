# OGT-203 local open-model service

OGT-203 establishes a reproducible, loopback-only inference boundary for the
OpenGrowTwin copilot. It submits the frozen OGT-201 tool declarations and
validates model proposals, but it does not execute tools. Deterministic dispatch
into Kit remains OGT-204.

## Selected model

| Field | Recorded value |
|---|---|
| Model | NVIDIA Nemotron 3 Nano 4B |
| Repository | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` |
| Quantization | Q4_K_M |
| Snapshot | `ba223d14e45525f7fae81db77ea8cabeb2fc6c25` |
| File | `NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf` |
| File size | 2,837,072,864 bytes |
| SHA-256 | `be5d9a656a51922f24f1f09a759cebb694e1f5d9728bf0ef9f8c972c5a0b5ef2` |
| Runtime context | 8,192 tokens |
| License | NVIDIA Nemotron Open Model License; verify upstream terms for redistribution |

The GGUF is an external runtime artifact and is not committed to this
repository.

## Recorded VM and runtime

- Ubuntu 22.04.5 LTS
- NVIDIA L4, 23,034 MiB reported VRAM
- NVIDIA driver 610.57.04
- CUDA Toolkit 13.0, nvcc 13.0.88
- llama.cpp commit `7798007a29a90e3053e799394da48cf53a2f8e0f`
- GNU C++ 11.4.0
- CUDA architecture 89
- `GGML_CUDA=ON`, `GGML_NATIVE=OFF`, `LLAMA_OPENSSL=ON`

Configure and build:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=OFF \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DLLAMA_OPENSSL=ON
cmake --build build --config Release \
  --target llama-server llama-cli -j "$(nproc)"
```

## Start the service

From the OpenGrowTwin repository:

```bash
chmod +x tools/run_nemotron_service.sh
tools/run_nemotron_service.sh
```

The default endpoint is `http://127.0.0.1:8080`. The launcher does not permit
remote access unless an operator explicitly overrides the host. For additional
local defense, set a secret before launch:

```bash
export OGT_MODEL_API_KEY='<random-local-secret>'
tools/run_nemotron_service.sh
```

Do not commit that value.

## Acceptance

With the server running:

```bash
python tools/validate_model_service.py
```

If an API key was configured:

```bash
python tools/validate_model_service.py --api-key "$OGT_MODEL_API_KEY"
```

The harness sends six representative prompts through the real service, requires
one OpenAI-format `tool_calls` result per prompt, parses the JSON arguments,
passes each proposal through `validate_tool_call`, compares it with the
expected allowlisted call, prints a JSON report, and exits nonzero on failure.
It never dispatches a tool.

Run unit and repository regression tests separately:

```bash
pytest -q
```

## Initial measurements

With Kit stopped and one 8,192-token slot:

- idle model allocation: 2,970 MiB;
- post-request allocation: 2,972 MiB;
- measured generation throughput: approximately 77.5 tokens/s;
- simple tool-call request: 1.47 s total;
- health endpoint: `{"status":"ok"}`.

A deliberately ungrounded PPFD question caused the model to mention an
unsupported generic range. When the measurement tool was supplied, the model
returned a correctly structured `get_scene_metrics` test call with no visible
prose. This demonstrates why model text is not a scientific authority and why
OGT-201 validation and deterministic tools remain mandatory.

## Validated completion result

On the recorded L4 VM:

1. all 63 repository tests passed in 2.07 seconds;
2. all six live tool-selection cases passed;
3. the service remained bound to `127.0.0.1:8080`;
4. the independently calculated SHA-256 matched the Hugging Face blob identifier;
5. the existing OGT-106 Kit/RTX synchronization validation passed with
   Nemotron resident on the same L4;
6. the model health endpoint remained `{"status":"ok"}` after Kit exited;
7. post-Kit model allocation was 3,026 MiB (3,035 MiB total GPU usage).

The coexistence check validates resource compatibility only. Tool execution and
the Kit copilot panel remain intentionally deferred to OGT-204 and OGT-205.
