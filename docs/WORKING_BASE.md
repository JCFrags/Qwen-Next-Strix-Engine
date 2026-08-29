# Reproducible working-base profile

## Status

`PASS_WORKING_BASE` applies only to the exact base profile below. MTP is disabled and `BLOCKED`. Vision and context above 65,536 tokens are not qualified.

## Launch

Set both required paths, then run the foreground launcher:

```bash
export LLAMA_SERVER_BIN=/path/to/llama-server
export QWEN_MODEL_PATH=/path/to/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf
scripts/launch-working-base.sh
```

The launcher refuses a missing path, a non-executable binary, a binary SHA-256 mismatch, a wrong model entry name, or any shard hash mismatch. It verifies the accepted binary SHA-256 and the four model hashes in [`receipts/Q4_K_XL_MODEL.md`](receipts/Q4_K_XL_MODEL.md).

The fixed profile is:

- source commit `1baf32a24619aa8f6eac684308fc5852bb3cc3f9`;
- binary SHA-256 `496b5151f5be070ab4cfc24cbbd6fa62d3986b2fcc25aab019f29ed828c6ab8f`;
- exact Unsloth `UD-Q4_K_XL` four-shard model;
- HIP target `gfx1151` with all model layers assigned to the GPU;
- 65,536-token context, one slot, and continuous batching disabled;
- Q8_0 K and V caches;
- batch 4,096 and microbatch 2,052;
- four threads, flash attention, no context shift, Jinja, no Web UI, metrics, and verbosity 3;
- maximum generation 65,536 tokens;
- automatic model loading through option omission;
- no MTP sidecar and no vision projector.

The command intentionally does not set a forced load mode or lazy tensor-read option. Do not add one and call the result the accepted profile.

`WORKING_BASE_HOST`, `WORKING_BASE_PORT`, and `WORKING_BASE_ALIAS` can change only endpoint presentation. They default to `127.0.0.1`, `8080`, and the public model name. Any inference argument change creates a new profile that needs qualification.

## Why microbatch 2,052 is fixed

The changed-prefix boundary was token 45,673. The 2,052-token microbatch produced a reusable checkpoint at token 45,670. This is three tokens before that boundary. Requests 2 through 4 then processed tails of 2,056, 2,056, and 2,057 tokens without restoring changed recurrent state.

This alignment passed the strict recurrent gate. A different microbatch can put the available checkpoint after the changed-prefix boundary or can change checkpoint selection. Therefore, 2,052 is required for this receipt. A nearby value is not equivalent without a new strict gate.

## Stop and status pattern

The launcher stays in the foreground so a normal process supervisor can own lifecycle state. For a short manual trial, use one shell-owned PID:

```bash
scripts/launch-working-base.sh >working-base.log 2>&1 &
pid=$!
kill -0 "$pid"       # status
kill -TERM "$pid"     # stop
wait "$pid" || true   # wait for exit
```

Do not use a broad process-name match. A persistent deployment should use the host's existing supervisor and should keep its host-specific files outside this repository.
