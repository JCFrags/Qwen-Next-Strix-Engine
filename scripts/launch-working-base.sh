#!/usr/bin/env bash
set -Eeuo pipefail

: "${LLAMA_SERVER_BIN:?set LLAMA_SERVER_BIN to the accepted llama-server binary}"
: "${QWEN_MODEL_PATH:?set QWEN_MODEL_PATH to the first UD-Q4_K_XL shard}"

readonly expected_binary_sha256="496b5151f5be070ab4cfc24cbbd6fa62d3986b2fcc25aab019f29ed828c6ab8f"
readonly expected_model_name="Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf"

[[ -x "$LLAMA_SERVER_BIN" ]] || { echo "LLAMA_SERVER_BIN is not executable" >&2; exit 2; }
[[ -r "$QWEN_MODEL_PATH" ]] || { echo "QWEN_MODEL_PATH is not readable" >&2; exit 2; }
[[ "${QWEN_MODEL_PATH##*/}" == "$expected_model_name" ]] || {
    echo "QWEN_MODEL_PATH must name the first accepted UD-Q4_K_XL shard" >&2
    exit 2
}

observed_binary_sha256=$(sha256sum "$LLAMA_SERVER_BIN" | awk '{print $1}')
[[ "$observed_binary_sha256" == "$expected_binary_sha256" ]] || {
    echo "LLAMA_SERVER_BIN does not match the accepted binary" >&2
    exit 3
}

model_dir=${QWEN_MODEL_PATH%/*}
if [[ "$model_dir" == "$QWEN_MODEL_PATH" ]]; then
    model_dir=.
elif [[ -z "$model_dir" ]]; then
    model_dir=/
fi
(
    cd "$model_dir"
    sha256sum --check --strict - <<'MODEL_SHA256'
4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082  Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9  Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf
56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3  Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf
753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a  Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf
MODEL_SHA256
)

export ROCBLAS_USE_HIPBLASLT=1
exec "$LLAMA_SERVER_BIN" \
    --model "$QWEN_MODEL_PATH" \
    --alias "${WORKING_BASE_ALIAS:-Qwen3.8-Flash-Next-UD-Q4_K_XL}" \
    --host "${WORKING_BASE_HOST:-127.0.0.1}" \
    --port "${WORKING_BASE_PORT:-8080}" \
    --n-gpu-layers 999 \
    --flash-attn on \
    --cache-type-k q8_0 \
    --cache-type-v q8_0 \
    --ctx-size 65536 \
    --batch-size 4096 \
    --ubatch-size 2052 \
    --threads 4 \
    --parallel 1 \
    --no-cont-batching \
    --n-predict 65536 \
    --no-context-shift \
    --jinja \
    --no-webui \
    --metrics \
    --verbosity 3
