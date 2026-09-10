# Reproduce the local NVIDIA Nemotron copilot

OpenGrowTwin's AI component is a local open-weight model running on the same NVIDIA L4 used by Kit/RTX. The model is deliberately **not** allowed to calculate PPFD/DLI or execute arbitrary code. It proposes calls to a constrained tool set; OpenGrowTwin validates those calls deterministically and requires explicit human confirmation for mutations.

This guide rebuilds that runtime from a clean Linux GPU host.

## 1. Validated runtime

| Component | Validated value |
| --- | --- |
| OS | Ubuntu 22.04.5 LTS |
| GPU | NVIDIA L4, ~23 GB VRAM |
| NVIDIA driver | 610.57.04 |
| CUDA Toolkit | 13.0 (`nvcc 13.0.88`) |
| Model | NVIDIA Nemotron 3 Nano 4B |
| GGUF repository | `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF` |
| Quantization | `Q4_K_M` |
| GGUF filename | `NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf` |
| GGUF size | 2,837,072,864 bytes |
| GGUF SHA-256 | `be5d9a656a51922f24f1f09a759cebb694e1f5d9728bf0ef9f8c972c5a0b5ef2` |
| llama.cpp commit | `7798007a29a90e3053e799394da48cf53a2f8e0f` |
| Context | 8,192 tokens |
| Service | `127.0.0.1:8080` |

Upstream model page:

https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF

Review the current NVIDIA Nemotron Open Model License on the upstream model page before downloading or redistributing model artifacts. OpenGrowTwin does not redistribute the GGUF.

## 2. Verify the GPU and CUDA toolchain

```bash
nvidia-smi
nvcc --version
```

The recorded environment used CUDA 13.0. If `/usr/local/cuda-13.0` is absent, either install the matching toolkit or deliberately adapt the build/launcher and record the changed runtime.

```bash
ls -ld /usr/local/cuda-13.0
/usr/local/cuda-13.0/bin/nvcc --version
```

## 3. Install build prerequisites

```bash
sudo apt-get update
sudo apt-get install -y \
  git \
  cmake \
  build-essential \
  libssl-dev \
  ca-certificates \
  curl
```

`LLAMA_OPENSSL=ON` is important for the reference workflow because the launcher uses llama.cpp's Hugging Face download path over HTTPS.

## 4. Clone the exact llama.cpp revision

The OpenGrowTwin launcher defaults to `$HOME/src/llama.cpp`:

```bash
mkdir -p "$HOME/src"
cd "$HOME/src"
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git checkout 7798007a29a90e3053e799394da48cf53a2f8e0f
```

Verify:

```bash
git rev-parse HEAD
```

Expected:

```text
7798007a29a90e3053e799394da48cf53a2f8e0f
```

## 5. Build llama.cpp for the NVIDIA L4

The L4 is Ada-generation and the reference build targeted CUDA architecture 89.

```bash
cd "$HOME/src/llama.cpp"

cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA=ON \
  -DGGML_NATIVE=OFF \
  -DCMAKE_CUDA_ARCHITECTURES=89 \
  -DLLAMA_OPENSSL=ON

cmake --build build --config Release \
  --target llama-server llama-cli \
  -j "$(nproc)"
```

Verify:

```bash
test -x build/bin/llama-server && echo "llama-server OK"
test -x build/bin/llama-cli && echo "llama-cli OK"
```

Optional dynamic-link check:

```bash
ldd build/bin/llama-server | grep -E 'cuda|cublas|ssl|crypto' || true
```

## 6. Start the model through the repository launcher

In a second terminal:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
chmod +x tools/run_nemotron_service.sh
tools/run_nemotron_service.sh
```

The launcher defaults are:

```text
LLAMA_CPP_DIR=$HOME/src/llama.cpp
OGT_MODEL_REF=nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M
OGT_MODEL_HOST=127.0.0.1
OGT_MODEL_PORT=8080
OGT_MODEL_CONTEXT=8192
```

It starts `llama-server` with GPU offload and Jinja/tool-template support.

On first run, llama.cpp may download the GGUF from the upstream repository. Internet access is therefore required unless the model is already available to the runtime.

## 7. Optional local API key

The reference architecture is loopback-only. For additional local defense:

```bash
export OGT_MODEL_API_KEY='<random-local-secret>'
tools/run_nemotron_service.sh
```

Do not put this value in shell scripts, Git, screenshots, logs, or documentation.

The model endpoint should not be bound to a public interface merely to simplify remote development.

## 8. Verify the service

```bash
curl -sS http://127.0.0.1:8080/health
echo
```

Expected:

```json
{"status":"ok"}
```

Check the listener:

```bash
sudo ss -ltnp 'sport = :8080'
```

It should be bound to `127.0.0.1`, not `0.0.0.0`.

Check GPU memory:

```bash
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

The observed model allocation was roughly 3 GB. A representative recorded generation rate was approximately 77 tokens/s; exact performance is not an acceptance criterion.

## 9. Verify the model artifact

If you materialize the GGUF as a normal file:

```bash
sha256sum NVIDIA-Nemotron3-Nano-4B-Q4_K_M.gguf
```

Reference SHA-256:

```text
be5d9a656a51922f24f1f09a759cebb694e1f5d9728bf0ef9f8c972c5a0b5ef2
```

A different checksum means you are not reproducing the exact reference artifact. Treat it as a new model revision and rerun validation.

## 10. Understand the trust boundary

```text
user prompt
   ↓
Nemotron (untrusted proposal generator)
   ↓
JSON/tool-call parsing
   ↓
allowlist + schema + bounds + identifiers
   ↓
read-only execution
        OR
exact mutation proposal
   ↓
explicit human confirmation token
   ↓
OpenUSD scene mutation / deterministic solver
   ↓
measured result
   ↓
model-grounded explanation
```

The model is not granted:

- arbitrary Python execution;
- shell execution;
- arbitrary filesystem paths;
- dynamically named tools;
- unrestricted USD paths;
- unbounded numeric mutation;
- authority to invent PPFD/DLI or biological evidence.

## 11. Run the live tool-selection validator

With the service healthy:

```bash
cd "$HOME/projects/OpenGrowTwin"
source .venv/bin/activate
python tools/validate_model_service.py
```

If an API key is enabled:

```bash
python tools/validate_model_service.py --api-key "$OGT_MODEL_API_KEY"
```

This sends representative prompts through the real model service, expects OpenAI-format `tool_calls`, validates proposed arguments, and compares routing against expected allowlisted calls. It does not give the model arbitrary execution.

## 12. Validate the complete model → tool → result loop

```bash
python tools/validate_tool_loop.py
```

A validated evidence lookup produced a structured `get_target` call for the approved Phalaenopsis reference and returned DOI `10.1111/ppl.12300` from the curated evidence store.

The final explanation is grounded in the deterministic tool result rather than accepted merely because the model produced plausible prose.

## 13. Run open-model routing/grounding regressions

```bash
mkdir -p build/open-model-regressions
python tools/validate_open_model_regressions.py \
  | tee build/open-model-regressions/routing-grounding.json
```

A validated reference run reported:

```text
overall passed: True
routing: 8/8 passed
grounding: 2/2 passed
```

Because this test calls the real local model, it is slower and less deterministic than pure unit tests. That is precisely why the deterministic validation layer exists.

## 14. Run adversarial deterministic safety checks

```bash
python tools/validate_copilot_safety.py \
  | tee build/open-model-regressions/safety.json
```

The safety suite verifies rejection of:

- unknown/arbitrary tool names;
- path traversal as an identifier;
- out-of-range radiant power;
- mutation without confirmation;
- arguments changed after confirmation;
- replayed confirmation token;
- expired confirmation token.

A validated reference run passed all seven adversarial cases and reported `executes_arbitrary_code: false` for the tool-executor architecture.

## 15. Run Kit and Nemotron together

Keep the model service running and start Kit from another terminal using [`kit-linux-operations.md`](kit-linux-operations.md).

Before using the copilot panel:

```bash
curl -sS http://127.0.0.1:8080/health && echo
nvidia-smi
```

Then test a bounded mutation such as a channel-power change.

Expected interaction:

1. click **Ask**;
2. see an exact proposed `set_channel_power` call;
3. verify the scene has not changed;
4. click **Confirm exact change**;
5. verify the scene/scientific result recomputes;
6. create a second proposal and click **Reject**;
7. verify no mutation occurs.

The acceptance property is the guarded state transition and internally consistent recomputation, not a specific PPFD value across unrelated scene states.

## 16. Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Permission denied` on launcher | executable bit missing | `chmod +x tools/run_nemotron_service.sh` |
| `Connection refused` | service not running/listening | check `/health`, `ss`, server terminal |
| `couldn't bind ... 8080` | existing server already owns port | reuse it or stop deliberately |
| HTTPS/model retrieval fails | llama.cpp built without working HTTPS support | install OpenSSL dev package and rebuild with `LLAMA_OPENSSL=ON` |
| model does not finish with a tool call | model routing variability | inspect raw response; rerun regressions; do not bypass validation |
| wrong tool selected | small-model nondeterminism | keep schemas narrow and deterministic validation mandatory |
| Kit fails to import project dependency | Kit Python isolation | do not assume project `.venv` packages are available in Kit |
| service reachable externally | host override/public binding | stop it and restore `127.0.0.1` unless deliberately hardened/authenticated |

## 17. Stop the model service

Use `Ctrl+C` in the server terminal and verify:

```bash
ss -ltnp | grep ':8080' || true
nvidia-smi
```

When GPU work is complete, stop the Google Cloud VM as described in the main reproduction guide.
