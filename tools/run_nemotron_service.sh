#!/usr/bin/env bash
set -euo pipefail

LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${HOME}/src/llama.cpp}"
MODEL_REF="${OGT_MODEL_REF:-nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M}"
MODEL_HOST="${OGT_MODEL_HOST:-127.0.0.1}"
MODEL_PORT="${OGT_MODEL_PORT:-8080}"
MODEL_CONTEXT="${OGT_MODEL_CONTEXT:-8192}"

export PATH="/usr/local/cuda-13.0/bin:${PATH}"
export LD_LIBRARY_PATH="/usr/local/cuda-13.0/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

args=(
  -hf "${MODEL_REF}"
  --host "${MODEL_HOST}"
  --port "${MODEL_PORT}"
  --ctx-size "${MODEL_CONTEXT}"
  --parallel 1
  -ngl 99
  --jinja
)

if [[ -n "${OGT_MODEL_API_KEY:-}" ]]; then
  args+=(--api-key "${OGT_MODEL_API_KEY}")
fi

exec "${LLAMA_CPP_DIR}/build/bin/llama-server" "${args[@]}"
