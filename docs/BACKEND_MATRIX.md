# Matched HIP/ROCm and Vulkan baseline for Qwen3.8-Flash-Next

**Work ID:** `qwen38-backend-matrix-20260828`
**Design date:** 2026-08-28
**Hardware scope:** two identical Strix Halo `gfx1151` hosts, called **host A** and **host B**

## 1. Purpose and safety statement

This design compares the HIP/ROCm and Vulkan/RADV backends. It controls the source, model, requests, host assignment, run order, cache state, and statistics.

This design does **not** state that Vulkan is safe. A prior controlled observation on this hardware class recorded a long-replay failure with `VK_ERROR_DEVICE_LOST`, an AMDGPU compute-ring timeout, and a GPU reset. A second profile also failed during long replay. The long-replay device-loss test in this design is therefore a **blocking gate**. A pass qualifies only the exact pinned build, driver, model, arguments, and workload. It does not prove general Vulkan safety.

Do not use a result from this matrix to enable a normal service. Deployment needs a separate decision and rollback plan.

## 2. Fixed baseline

### 2.1 Source pin

Use one clean `ggml-org/llama.cpp` source tree for both backends:

- Repository: <https://github.com/ggml-org/llama.cpp>
- Commit: `6c84c7d5d8833c6e0df69628f75a0f599797934e`
- Commit subject: `model: add Qwen3.8-Flash-Next (qwen4exp) (#27742)`
- Change rule: no local patch, untracked source file, submodule change, or later cherry-pick.

This commit is the merged base-support point. It keeps the backend comparison on one source tree. Do not use the HIP-tuned EngramHalo branch for the matched baseline. Its public documentation says its patch series is HIP-only and treats Vulkan as untested.

Create these source receipts before a build:

1. Full commit ID and commit-tree ID.
2. `git status --porcelain=v2` output. It must be empty.
3. Recursive submodule status.
4. SHA-256 of a deterministic `git archive` from the pinned commit.
5. SHA-256 of `CMakeCache.txt`, `build.ninja`, and the complete configure log for each backend.
6. SHA-256 of each final executable and each loaded `libggml` or backend library.
7. `llama-server --version`, `llama-bench --version`, and `--list-devices` output.

A receipt is invalid if the embedded build commit differs from the source pin.

### 2.2 Model pin

Use the same target files on both hosts and both backends:

- Repository: <https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF>
- Repository revision: `c8b5954a88c2775c546b92593eda40ea041d3176`
- Quant: `UD-IQ4_XS`
- Shards: the three files under `UD-IQ4_XS` at that revision
- Expected combined shard size: `93,682,584,224` bytes (`87.25 GiB`)
- Native model context in the public card: 262,144 tokens
- Matrix context: 65,536 tokens

Create a sorted manifest with each relative file name, byte count, SHA-256, and Hugging Face LFS object ID. Hash the manifest itself. The manifest hash and every file hash must match on host A and host B.

`UD-IQ4_XS` is the baseline because it leaves useful memory margin on a 128 GB-class unified-memory host. Unsloth reports mean KLD `0.079162` and a same-top-token rate of `91.089%` for this quant. These are publisher results, not results from this matrix.

Exclude these items from the baseline:

- MTP draft sidecar;
- vision projector;
- RPC or distributed inference;
- custom ROCmFP4 or ROCmFPX weights;
- prompt-cache persistence across process restarts;
- more than one slot or one client.

These exclusions keep the model graph and memory load matched across backends.

### 2.3 Compiler, driver, and host receipts

Freeze one software image before the campaign. Do not update packages during the campaign. Host A and host B must have byte-matched compiler and userspace-driver receipts. Record package-manager version identifiers and SHA-256 values for the resolved files, not only human-readable version strings.

Record this common receipt on both hosts:

- firmware or BIOS version and configuration export hash;
- kernel release, kernel command line, boot ID, and AMDGPU module metadata;
- operating-system image or package-set lock hash;
- CPU model, core count, memory capacity and speed, and `gfx1151` GPU identity;
- CMake, Ninja, Git, Python, C compiler, C++ compiler, linker, and C library versions;
- SHA-256 of the resolved C compiler, C++ compiler, linker, CMake, and Ninja binaries;
- CPU governor, power profile, GPU DPM state, huge-page state, swap state, and all inference-related environment variables;
- storage model, firmware, filesystem, mount options, and model-file physical location class;
- loaded kernel modules and non-secret package inventory.

Record this HIP/ROCm receipt:

- `hipcc --version`, `hipconfig --full`, and `rocminfo`;
- ROCm package versions;
- SHA-256 of the resolved HIP Clang compiler and device libraries;
- SHA-256 of the loaded HIP, rocBLAS, hipBLAS, hipBLASLt, rocWMMA, HSA, and ROCr libraries;
- the exact `GPU_TARGETS=gfx1151` configure value;
- the HIP device line from `--list-devices`.

Record this Vulkan/RADV receipt:

- `vulkaninfo --summary` and the selected physical-device properties;
- Vulkan loader, header, SPIR-V header, and shader compiler versions;
- SHA-256 of `glslc` or the actual shader compiler, Vulkan loader, RADV ICD JSON, and resolved `libvulkan_radeon` library;
- Mesa/RADV, LLVM/ACO, `libdrm`, and Vulkan package versions;
- the Vulkan device line from `--list-devices`.

Also save the dynamic-library map for each executable. A backend result is invalid if it loads an unrecorded backend library or a different driver after the receipt was frozen.

### 2.4 Build matrix

Use separate build directories and backend-specific executables. Do not build both GPU backends into one test executable.

Common configure controls:

```text
CMAKE_BUILD_TYPE=Release
GGML_NATIVE=OFF
GGML_BACKEND_DL=OFF
GGML_BUILD_TESTS=ON
```

HIP-only differences:

```text
GGML_HIP=ON
GGML_VULKAN=OFF
GPU_TARGETS=gfx1151
```

Vulkan-only differences:

```text
GGML_HIP=OFF
GGML_VULKAN=ON
```

Use the same resolved host C and C++ compilers for both builds. HIP also uses the pinned HIP Clang compiler for device code. Save the literal configure and build command arrays. Do not reconstruct commands from shell history.

Run the source tree's focused architecture and backend tests after each build. Stop if a test fails, if an operation falls back to an unexpected CPU path, or if the runtime does not identify the intended backend and `gfx1151` device.

## 3. Matched runtime profile

Use this logical argument manifest for both backends. Resolve the exact option spelling from the pinned binary's `--help` output and save the final argument array as JSON.

| Item | Fixed value |
|---|---|
| model | first `UD-IQ4_XS` shard from the pinned manifest |
| GPU layers | `999` |
| context | `65,536` tokens |
| slots / clients | `1 / 1` |
| batch | `4,096` |
| microbatch | `512` |
| K cache | `q8_0` |
| V cache | `q8_0` |
| flash attention | `on` |
| model load | memory map enabled; no persistent cross-process cache |
| CPU generation threads | `4` |
| CPU batch threads | `4` |
| polling | `50` |
| context shift | disabled |
| web UI | disabled |
| sampling for correctness | greedy, temperature `0`, fixed seed |
| generated tokens, short probe | `256` |
| generated tokens, sustained TG | `1,024` |
| reasoning template | thinking enabled, `reasoning_effort=medium`, preserved-thinking setting fixed |

Only these fields may differ:

- selected device: HIP device for the HIP build, Vulkan/RADV device for the Vulkan build;
- backend library and its required non-tuning loader variables.

Unset backend tuning variables unless the manifest explicitly fixes them before the first run. Do not add a tuning variable to only one completed cell. A tuned comparison is a new matrix.

Save the fully rendered chat prompt and its token-ID SHA-256. Send byte-identical request JSON, except for a unique request ID that is outside model input. Record request and response hashes.

## 4. Admission checks

Run these checks before every block:

1. Receipt hashes match the frozen campaign manifest.
2. No other GPU compute process is active.
3. No other model process is active.
4. Swap use is zero. No new major page-fault storm is present.
5. Available memory is at least the declared block minimum.
6. The GPU is visible through only the intended backend.
7. Kernel logs are readable from the block start. If they are not readable, reset detection is incomplete and the block must not start.
8. No AMDGPU timeout, fault, or reset occurred since boot.
9. CPU and GPU temperatures are below the fixed non-throttling ceiling and differ by no more than 3 degrees Celsius between paired starts.
10. The host is idle under the campaign's fixed load and I/O thresholds for five minutes.
11. The model manifest and prompt-corpus manifest match on both hosts.

Keep power mode and automatic GPU DPM behavior unchanged for the full matrix. Record clocks, power, temperature, available memory, GTT use, and disk throughput at one-second intervals.

## 5. Correctness gates

Correctness gates run before performance tests. A failure blocks performance claims for the affected build. Any host-dependent correctness difference blocks pooled cross-host results.

### Gate C0: load and graph

- The model loads without OOM, swap use, assertion, unsupported operation, or unexpected CPU fallback.
- The runtime reports the intended backend and all requested GPU layers.
- A one-token request succeeds.
- The process stays alive and a second health request succeeds.

### Gate C1: deterministic short probes

Use a versioned prompt corpus with fixed token IDs. Include arithmetic, code completion, multilingual text, structured JSON, and one tool-call schema. For each probe:

- require the known answer or exact structured field values;
- require valid UTF-8 and valid JSON or tool syntax where applicable;
- reject empty output, repeated-character runs, multilingual noise, NaN/Inf log probabilities, or an early stop not allowed by the fixture;
- save generated token IDs and top-5 log probabilities for the first 64 generated positions.

For prompts whose CPU reference has a clear top-1 margin, require the same greedy token IDs on both backends and both hosts. If a near tie causes a token difference, label it and run the fixed CPU reference probe. Do not silently call different text equivalent.

### Gate C2: context and slot reuse

Use exact marker/value fixtures at approximately 2.7K, 6.6K, 32K, and 47.7K input tokens. Token counts come from the pinned tokenizer.

At each depth, require:

1. fresh recall of an early marker and a final marker;
2. changed-value recall after reuse;
3. return-to-prior-value recall in an A/B/A sequence;
4. an unrelated middle request followed by exact early-context recall;
5. server-reported prompt-token counts within the fixture's declared bounds;
6. no silent truncation, stale value, cross-request response, or missing final suffix.

Run C2 without MTP. One slot and one client remain fixed.

### Gate C3: real agent-shaped loop

Run a fixed, offline tool loop with at least eight tool turns and at least 32K total prompt tokens. Tools return fixture data only. Require all typed arguments, tool-result markers, final answer fields, and turn order. Record time to first token, prefill rate, decode rate, and complete request/response hashes, but do not use this gate as the primary microbenchmark.

### Gate C4: long-replay device-loss gate — blocking

This gate targets the known failure class. It is not optional for Vulkan.

For each host/backend cell, run three independent repetitions. Start each repetition with a new server process. At least one repetition must follow an operator-approved reboot so the kernel-log boundary and GPU state are cold.

Use this fixed sequence:

1. Submit a 48K-token conversation and generate 4K tokens.
2. Submit a small-tail continuation. Confirm useful prefix reuse.
3. Submit a context-rewritten 54K-token prompt with a common prefix below 256 tokens. Confirm that at least 32K tokens are actually replayed.
4. Generate 8K tokens or stop only at the fixture's valid end marker. Keep the complete rendered request and maximum generation inside the 65,536-token slot.
5. Submit a short post-replay canary without restarting the process.

A repetition fails on any of these events:

- `VK_ERROR_DEVICE_LOST`, `ErrorDeviceLost`, a Vulkan queue-submit failure, or an equivalent HIP device error;
- AMDGPU ring timeout, job timeout, page fault, VM fault, GPU reset start/end, queue reset, or failed recovery;
- no forward token or prefill progress for the fixed watchdog interval;
- server abort, signal death, health loss, changed process identity, or failed post-replay canary;
- silent truncation, wrong marker recall, unexpected cache reuse, or a processed-token count below the required replay;
- OOM, swap activity, or memory pressure that invalidates a backend comparison.

**Decision:** one failure blocks that exact backend candidate. Do not average the failed run into performance data. Preserve its complete evidence and stop performance work that depends on it. A Vulkan pass only permits the remaining controlled matrix. It does not justify the statement “Vulkan is safe.”

## 6. GPU-reset and device-loss detection

Create a kernel-log cursor immediately before each block. Save the boot ID and monotonic timestamp. During and after the block, collect kernel and process logs from that exact boundary.

Match, at minimum, case-insensitive forms of:

```text
amdgpu.*timeout
ring .* timeout
amdgpu_job_timedout
GPU reset
GPU reset begin
GPU reset end
queue reset
VM_L2_PROTECTION_FAULT
page fault
GPU fault
VK_ERROR_DEVICE_LOST
ErrorDeviceLost
hipError
HSA_STATUS_ERROR
```

Also record:

- process PID and start time before and after each request;
- backend device inventory before and after the block;
- GPU-busy, clocks, temperature, GTT, available memory, swap, and disk I/O time series;
- exit code, signal, core-dump metadata without core contents, and last progress line;
- a post-block one-token canary.

A successful kernel queue reset is still a reset and is a hard failure. A server that survives a reset does not convert the failure into a pass.

Do not use `RADV_DEBUG=hang` in timed runs. Mesa states that this mode adds trace markers and synchronization. It can change timing and behavior. Use it only in a separate diagnostic reproduction after a failure. Do not disable kernel GPU recovery for this baseline.

## 7. Cold and warm runs

### Cold block

A true cold block starts after an operator-approved host reboot. The model files must not be read before the timed load. Wait for the fixed idle and temperature admission window. Record:

- boot-to-ready time;
- model load time;
- first-request time to first token;
- first-request prefill and generation rates;
- storage bytes and major faults;
- peak and final available memory and GTT.

A process restart without a reboot is a **process-cold, page-cache-unknown** run. Report it separately. Do not label it cold.

### Warm block

Keep the same process and loaded model. Run one discarded warm-up. Then run three measured samples with prompt cache disabled or with nonce-distinct fixed-token fixtures that cannot reuse a prefix. Follow with one intentional same-prompt reuse sample. Report the no-reuse and reuse samples separately.

For `llama-bench`, retain its default warm-up and use JSON output with `10` repetitions for each PP/TG point. Its documentation states that it measures model processing and generation, but excludes tokenization and sampling. Therefore, also report server end-to-end latency.

Fixed benchmark points:

- PP: 512, 4,096, 16,384, and 32,768 tokens;
- TG: 1,024 tokens at depth 0, 16K, 32K, and 48K;
- combined request: 4,096 prompt tokens plus 1,024 generated tokens;
- real agent-shaped loop from C3.

Do not mix cold and warm observations in one summary statistic.

## 8. Host swap and run order

Use paired simultaneous blocks when practical. Start the paired requests within 60 seconds. If simultaneous execution is not possible, preserve the same order and record the delay.

One four-block Latin-square cycle is:

| Block | Host A | Host B |
|---|---|---|
| 1 | HIP | Vulkan |
| 2 | Vulkan | HIP |
| 3 | Vulkan | HIP |
| 4 | HIP | Vulkan |

This gives ABBA order on host A and BAAB order on host B. It controls first-use, time drift, and host effects.

Repeat the four-block cycle five times. This gives 10 independent cold assignments for each host/backend cell. Rotate the first block of each new cycle so that the campaign does not always begin with the same host/backend pair. Pre-generate the complete order and hash it before the first run. Do not change the order after seeing results.

A block contains admission, cold measurements, correctness canaries, warm measurements, log checks, and cooldown. C4 long replay can run in separate identically ordered gate blocks before the main performance campaign.

## 9. Performance statistics

Keep raw per-repetition values. Do not remove an outlier only because it is slow or fast.

Mark a sample invalid only for a predeclared cause:

- receipt drift;
- another compute process;
- thermal or power throttling;
- reset, device loss, OOM, swap, or server failure;
- wrong token count or failed correctness fixture;
- missing telemetry or timing boundary.

Report invalid samples and reasons. Replace an invalid block at the end with the same host/backend assignment. Keep the original record.

For each host, backend, cache state, and depth, report:

- count, median, arithmetic mean, standard deviation, median absolute deviation, minimum, maximum, and coefficient of variation;
- median and geometric mean of the paired HIP/Vulkan rate ratio;
- paired bootstrap 95% confidence interval with 10,000 resamples at the independent block level;
- cold load, TTFT, PP, TG, end-to-end latency, peak memory, GTT, energy if available, and MTP acceptance as not applicable.

Use rates for PP and TG. Use latencies for load, TTFT, and end-to-end time. Always state the ratio direction, for example `Vulkan / HIP` for rates and `HIP / Vulkan` for latency speedup.

Treat warm repetitions inside one block as repeated measurements, not independent hosts. Bootstrap blocks, not inner samples. With only two hosts, do not claim population-wide hardware inference. Report host A and host B separately first. Then report the blocked aggregate.

Flag a cell as unstable when warm-run coefficient of variation exceeds 5%. Investigate when paired host medians differ by more than 5%. Do not hide a persistent difference by pooling.

## 10. Cross-host validation

Before aggregation, require:

1. identical model and prompt manifests;
2. identical source archive, compiler, package-set, kernel, firmware, and backend-driver receipts;
3. matching build flags and matching binary SHA-256 for the same backend;
4. the same backend device capabilities;
5. all correctness gates pass on both hosts;
6. no reset or device-loss evidence on either host;
7. no systematic thermal, power, memory, or storage difference;
8. same-backend host median rates within 5%, or a documented cause and a decision not to pool.

Use a difference-of-differences check:

```text
(host A Vulkan / host A HIP) / (host B Vulkan / host B HIP)
```

Report this value and its block-bootstrap interval for each primary metric. A value materially different from 1 indicates a host-by-backend interaction. Investigate it before stating a backend effect.

Repeat one randomly selected frozen block on the opposite host at the end. Require its correctness hashes and performance interval to agree with the original cell. This is the final cross-host swap check.

## 11. Alternative branches and exclusion rules

Alternative branches are new matrices. Do not merge them into baseline statistics.

### Memory-first branch

`UD-Q3_K_XL` is credible on both backends. Its public size is about 83.81 GiB. It uses the same mainline `qwen4exp` graph and leaves more memory margin. Use it only with its own pinned revision, shard manifest, correctness gates, and full host swap.

### Quality-first branch

`UD-Q4_K_XL` is about 103.69 GiB. Run it only if each backend can load the exact files with no swap, no OOM, no missing kernel, and at least 16 GiB available memory after the 65,536-token context is allocated. Require a separate load-phase peak-memory test. Do not infer Vulkan fit from a HIP-only lazy-PLE result.

### MTP branch

The public Q8 MTP sidecar is about 4.1 GB, but current public support uses backend-specific or draft branches. EngramHalo documents HIP-only tuning. A Vulkan-first fork uses a different kernel path. Therefore, MTP is not a matched baseline branch.

A later MTP test must pin the sidecar SHA-256 and matching graph implementation, start from a base-model pass, repeat all correctness and long-replay gates, and report acceptance for code and prose separately. Do not compare an EngramHalo HIP result with a different-source Vulkan result as if only the backend changed.

### Excluded branches

Do not include BF16, official FP8, vLLM, or SGLang in this single-host matrix. Their documented model or kernel paths do not provide a matched one-host `gfx1151` fit. Do not use an RPC split across host A and host B. The hosts are independent replicates in this design.

## 12. Required result package

The public result package must contain no hostnames, network addresses, usernames, credentials, or private file locations. Use host A and host B only.

Include:

- design and frozen run-order hash;
- source, model, compiler, driver, host, binary, argument, and prompt receipts;
- raw JSON or JSONL benchmark output;
- request and response hashes plus correctness decisions;
- kernel and process log slices from exact cursors;
- one-second telemetry;
- invalid-sample ledger;
- statistics script and its SHA-256;
- per-host tables, blocked aggregate, bootstrap intervals, and difference-of-differences;
- C4 device-loss decision and known limits.

The terminal status must be one of:

- `PASS_FOR_EXACT_MATRIX`: all gates pass. This does not state general Vulkan safety.
- `VULKAN_BLOCKED_DEVICE_LOSS`: any Vulkan C4 reset, hang, device loss, or post-replay failure.
- `BACKEND_BLOCKED_CORRECTNESS`: visible or silent correctness failure.
- `MATRIX_INVALID_RECEIPT_DRIFT`: source, model, compiler, driver, host, or argument mismatch.
- `MATRIX_INCONCLUSIVE`: insufficient valid independent blocks or unresolved host interaction.

## 13. Public sources

Accessed 2026-08-28.

1. Qwen model card. It describes Qwen3.8-Flash-Next as an experimental Qwen4 architecture preview and gives a native 262,144-token context: <https://huggingface.co/Qwen/Qwen3.8-Flash-Next>
2. Unsloth GGUF repository and pinned revision: <https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/c8b5954a88c2775c546b92593eda40ea041d3176>
3. Unsloth quant guide and published KLD table: <https://unsloth.ai/docs/models/qwen3.8-next>
4. Merged llama.cpp Qwen3.8 support: <https://github.com/ggml-org/llama.cpp/commit/6c84c7d5d8833c6e0df69628f75a0f599797934e>
5. llama.cpp HIP and Vulkan build instructions: <https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>
6. `llama-bench` repetitions, depth tests, and JSON sample fields: <https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md>
7. Mesa RADV driver scope: <https://docs.mesa3d.org/drivers/radv.html>
8. Mesa RADV hang-debugging behavior and report contents: <https://docs.mesa3d.org/drivers/amd/hang-debugging.html>
9. EngramHalo backend-scope and Strix Halo notes: <https://github.com/Aristo94/EngramHalo.cpp/blob/b08a77760fa73520d02d83b274f31b8fccf282bc/docs/strix-halo/README.md>
10. Public Q8 MTP sidecar description: <https://huggingface.co/EasiiX/Qwen3.8-Flash-Next-MTP-Strix-Halo-GGUF>

## 14. Known limits

- No benchmark was run for this design.
- Public performance reports are not substitutes for this matched matrix.
- Two hosts can expose a host interaction, but they cannot estimate variation across all Strix Halo systems.
- A reboot gives the strongest practical cold boundary, but firmware and storage caches can retain state.
- Greedy output can differ at near-tied logits because backends use different floating-point reduction orders. The design requires disclosure and a CPU reference check instead of silent equivalence.
- Kernel logs can prove that a reset was reported. They cannot prove the absence of every transient hardware fault.
- Passing C4 does not remove the known long-replay risk class. It only fails to reproduce it under the exact frozen matrix.
- Qwen3.8-Flash-Next and its llama.cpp support were new at the design date. Any later source or driver needs a new receipt and full gate cycle.
