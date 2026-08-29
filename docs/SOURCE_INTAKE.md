# Qwen3.8-Flash-Next Strix Halo source-intake candidate

**Work ID:** `qwen38-source-intake-20260828`
**Source-state check:** 2026-08-28
**Scope:** source and artifact intake only. No deployment, build, or runtime change was made.

## Executive decision

Use a fresh, pinned `ggml-org/llama.cpp` tree as the long-term source base. The required `qwen4exp` text and vision support is already upstream. It merged through [pull request 27742](https://github.com/ggml-org/llama.cpp/pull/27742) at merge commit [`6c84c7d5d8833c6e0df69628f75a0f599797934e`](https://github.com/ggml-org/llama.cpp/commit/6c84c7d5d8833c6e0df69628f75a0f599797934e).

Treat [`Aristo94/EngramHalo.cpp`](https://github.com/Aristo94/EngramHalo.cpp) as the primary `gfx1151` HIP donor. The checked branch tip is unsigned commit [`b08a77760fa73520d02d83b274f31b8fccf282bc`](https://github.com/Aristo94/EngramHalo.cpp/commit/b08a77760fa73520d02d83b274f31b8fccf282bc). Its branch is close to upstream and has a documented post-merge lineage. Port or retain each performance change as a separate commit with an off switch and a focused test.

Do **not** use the complete [`apepojken/llama.cpp:qwen4exp-spec-mtp`](https://github.com/apepojken/llama.cpp/tree/qwen4exp-spec-mtp) Vulkan branch as a deployment base. Its checked tip is unsigned commit [`843d5750579a15ed4a42d73eb862855c271021ac`](https://github.com/apepojken/llama.cpp/commit/843d5750579a15ed4a42d73eb862855c271021ac). A public, independent `gfx1151` reproduction found prompt-length-dependent output corruption while the speed result remained high. Some small changes are still useful as isolated donors.

Do **not** substitute the [`jockevaupptaget` MTP sidecar](https://huggingface.co/jockevaupptaget/Qwen3.8-Flash-Next-MTP-GGUF) for the EngramHalo/EasiiX sidecar. The tensor layouts differ. The repository also declares Apache-2.0 even though it says the weights derive directly from a model under the Qwen Community License 1.0. This license metadata conflict must be resolved before redistribution.

## Evidence labels

- **Direct source evidence** means repository API state, commit contents, license text, or an upstream pull-request record inspected for this report.
- **Published measurement** means a number reported by a source author. It was not reproduced during this intake.
- **Independent public reproduction** means a result reported by a different public user. It is still a public self-report, not a controlled audit.
- **Inference** means a technical conclusion from the inspected source relationships. It is not a completed merge or runtime test.

No new performance measurement was run for this report.

## Exact source identities

### Authoritative model and upstream runtime

| Item | Exact identity at check | Status and use |
|---|---|---|
| Official model | [`Qwen/Qwen3.8-Flash-Next`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), revision [`de4b8e4d43b917e7706784d8bb445c9af86a3540`](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/tree/de4b8e4d43b917e7706784d8bb445c9af86a3540) | Authoritative weights and configuration. License is Qwen Community License 1.0, not Apache-2.0. |
| Quantized GGUF donor | [`unsloth/Qwen3.8-Flash-Next-GGUF`](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF), revision [`c8b5954a88c2775c546b92593eda40ea041d3176`](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/c8b5954a88c2775c546b92593eda40ea041d3176) | Declares the official model as its base and Qwen Community License 1.0. Pin the exact selected shards, not only the repository revision. |
| Upstream base support | [llama.cpp PR 27742](https://github.com/ggml-org/llama.cpp/pull/27742), head `eaf93765572e794b8e3754fe45adbe12d381e997`, merge `6c84c7d5d8833c6e0df69628f75a0f599797934e` | Merged 2026-08-27. Adds converter, text graph, PLE, GDN state, QSA, quantized KV, state handling, and vision. This is the required architecture baseline. |
| Upstream MTP | [llama.cpp draft PR 27836](https://github.com/ggml-org/llama.cpp/pull/27836), head [`1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af`](https://github.com/rmonsurate/llama.cpp/commit/1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af) | Open and draft at check. GitHub reported `mergeable: true`, `mergeable_state: unstable`, 3 commits, 9 changed files, and no commit-status records. Do not treat the synthetic `merge_commit_sha` as a merged commit. |
| Upstream tip observed | [`d7bd3bfcad3e29c7e49fd26f38c79ee3e9a3fd6b`](https://github.com/ggml-org/llama.cpp/commit/d7bd3bfcad3e29c7e49fd26f38c79ee3e9a3fd6b) | Mutable reference only. Pin a chosen base again at implementation time. |

PR 27742 records two manually resolved rebase conflicts in `tests/test-llama-archs.cpp` and `src/llama-model-saver.cpp`. It also states that the synthetic architecture test does not exercise PLE input and is not a full correctness oracle for GDN segmentation.

PR 27836 uses these exact commits:

1. [`d303eec923f92ccab7109e97d95cb5c1ab83e0d2`](https://github.com/rmonsurate/llama.cpp/commit/d303eec923f92ccab7109e97d95cb5c1ab83e0d2) — register qwen4exp NextN tensor names.
2. [`d72620018f612bb05d16e585108e3440947a1f9f`](https://github.com/rmonsurate/llama.cpp/commit/d72620018f612bb05d16e585108e3440947a1f9f) — add the NextN/MTP draft graph.
3. [`1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af`](https://github.com/rmonsurate/llama.cpp/commit/1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af) — export the MTP draft head.

The PR author reports byte-identical temperature-zero output with MTP on and off on Apple Silicon. A later `gfx1151` comment reports two unresolved converter/loader issues for a standalone sidecar: the export whitelist can omit the head mixer, and the exported `blk.48.*` layout can still make the standalone loader require trunk blocks. These are release blockers for adopting PR 27836 unchanged.

### Primary `gfx1151` HIP donor

[`Aristo94/EngramHalo.cpp`](https://github.com/Aristo94/EngramHalo.cpp) is MIT-licensed. Its checked branch tip is `b08a77760fa73520d02d83b274f31b8fccf282bc`. GitHub compared that tip with the observed upstream tip and reported a common base of `b19cbe925be361d229f0fe03435affe4a2717f37`, with the fork 24 commits ahead and 9 behind. This is a divergence count, not a merge-conflict test.

Applicable source commits include:

| Commit | Applicable change | Intake note |
|---|---|---|
| [`a8f7e2265ae54886f2ce5326d8c496fffaebe076`](https://github.com/Aristo94/EngramHalo.cpp/commit/a8f7e2265ae54886f2ce5326d8c496fffaebe076) | HIP wide top-k selection for RDNA 3.5 | Direct `gfx1151` value. Prevents QSA indexer fallback to CPU for widths above 1024. |
| [`54d5baa8092e300d60d134de3692c4dbec667062`](https://github.com/Aristo94/EngramHalo.cpp/commit/54d5baa8092e300d60d134de3692c4dbec667062) | Skip fully masked flash-attention warp slices and select the RDNA head-256 vector path | Broad CUDA/HIP kernel change. Keep a feature gate and test other architectures. The commit credits a rebased `kyuz0/amd-strix-halo-toolboxes` tile change. Preserve that provenance. |
| [`b744cd8973227fee4f129d739ae4ddaa1f29aac9`](https://github.com/Aristo94/EngramHalo.cpp/commit/b744cd8973227fee4f129d739ae4ddaa1f29aac9) | Chunked GDN prefill kernel | Experimental on RDNA. The source says it was opt-in and not active in the published `gfx1151` numbers. Defer until the simpler ports settle. |
| [`c7e33834f9babee01df00f68b7c766dd1043465d`](https://github.com/Aristo94/EngramHalo.cpp/commit/c7e33834f9babee01df00f68b7c766dd1043465d) | Lazy mapped-row prefetch and an IQ4_NL `get_rows` path for 160-value PLE rows | High value for an SSD-backed PLE table. It combines a model/runtime change and a backend quantization change. Split these during intake. |
| [`62794305b44a0c0dbade84ff2488999f62ab95ec`](https://github.com/Aristo94/EngramHalo.cpp/commit/62794305b44a0c0dbade84ff2488999f62ab95ec) | Gather selected QSA KV rows instead of applying a dense mask | High decode value at depth. It changes decode numerics. The author reports a 0.03% perplexity delta and an NMSE regression bound. Multi-sequence HIP use is not validated and is disabled by default. |
| [`dc519925ca91b9e487bd633c1636f553f06224ff`](https://github.com/Aristo94/EngramHalo.cpp/commit/dc519925ca91b9e487bd633c1636f553f06224ff) | MTP graph and standalone sidecar loading | Public `gfx1151` measurements are favorable, but this overlaps upstream PR 27836. Do not merge both implementations. Select one graph and one tensor format. |
| [`59ea5f93f810ceffec0d970b36336a5251f88022`](https://github.com/Aristo94/EngramHalo.cpp/commit/59ea5f93f810ceffec0d970b36336a5251f88022) | Export the matching qwen4exp MTP block | Must remain paired with `dc519925...` and its exact sidecar layout. |

EngramHalo's published numbers are source-author measurements. They are not an independent audit. The branch tip and the listed feature commits are unsigned.

### Excluded Vulkan branch and eligible isolated changes

The `apepojken` branch tip is `843d5750579a15ed4a42d73eb862855c271021ac`. Relative to the observed upstream tip, GitHub reported a merge base of `4d19b287691e8f47fc303be420f630c40ec45684`, with the fork 46 commits ahead and 44 behind. The branch began before the final upstream qwen4exp merge history. A wholesale merge would replay much of PR 27742 and is therefore excluded.

Eligible donor commits are:

- [`51c0c10d5904550dc822925f74367aa47982249c`](https://github.com/apepojken/llama.cpp/commit/51c0c10d5904550dc822925f74367aa47982249c): add `ggml_cont()` to the transposed GDN activation before concatenation. The qwen4exp change is four additions and one deletion. The same commit also adds a Vulkan debug probe. Port only the qwen4exp change. The author reports about 8% better prefill and greedy identity.
- [`32af70900c81b4d629a2edf7772156d66f9e37e5`](https://github.com/apepojken/llama.cpp/commit/32af70900c81b4d629a2edf7772156d66f9e37e5): a 713-line mixed commit. It enables qwen4exp recurrent rollback rings, writes all convolution-state ring banks, extends PLE history for rejection, handles draft contexts that cannot partially roll back, changes cache reuse, and adds a separate MTP implementation and converter. Port only reviewed rollback and PLE-history subchanges. Do not import its MTP graph or sidecar format.
- [`472b758426db93206c2df130ef0f994721711b1a`](https://github.com/apepojken/llama.cpp/commit/472b758426db93206c2df130ef0f994721711b1a): incremental pooled QSA summary-key cache with state-operation watermarks. The author reports a 17% decode gain at 32K. This is state-invasive and must come after rollback correctness is established.

All three commits disclose AI assistance in their commit messages. Preserve the human author, exact commit, AI-assistance disclosure, and any upstream lineage in the provenance record.

### HaloFPX donor

[`JCFrags/HaloFPX`](https://github.com/JCFrags/HaloFPX) is MIT-licensed. Its checked `main` tip is signed commit [`d10757d364f4c20f8e27a47c55ec6ed76fb435cd`](https://github.com/JCFrags/HaloFPX/commit/d10757d364f4c20f8e27a47c55ec6ed76fb435cd). It predates the final qwen4exp merge and is not a suitable engine base.

One small source correction is applicable: [pull request 35](https://github.com/JCFrags/HaloFPX/pull/35), merged as [`167df62ffc8970bc408d72e97ab71a57de4b69d2`](https://github.com/JCFrags/HaloFPX/commit/167df62ffc8970bc408d72e97ab71a57de4b69d2). It keeps sampled-logit pointer, IDs, and row count in one branch, and falls back to a full raw-vocabulary row only when no sampled row exists. This is a server probability-reporting correctness fix. It is not a decode-speed optimization.

Do not import HaloFPX ROCmFPX MMVQ sum removal, dense-FFN activation reuse, or proposed Q/K/V activation reuse into the conventional Q4_K qwen4exp lane. Those paths target different quantization and operation shapes. The dense-FFN path excludes routed MoE.

## Known corruption and incompatibility evidence

### Prompt-length-dependent corrupted output

An [independent public reproduction](https://github.com/ggml-org/llama.cpp/pull/27836#issuecomment-5456825600) tested `apepojken` commit `472b7584` with the `jockevaupptaget` Q8_0 sidecar on Strix Halo `gfx1151` with ROCm 7.1. The report states:

- greedy output was correct at 133 and 718 prompt tokens;
- output became multilingual noise at 2,668 and 6,568 prompt tokens;
- the failure remained with draft depth 6 and 2;
- the corrupted run still reported 42.7 generated tokens/s versus a 16.8 tokens/s baseline.

This is strong public evidence that speed and draft acceptance are not correctness tests. It is a third-party self-report, not a repository test artifact. It is sufficient to exclude the branch and sidecar as a complete deployment base.

### Sidecar format split

The excluded sidecar repository says it converted separate `fc_embedding` and `fc_hidden` projections and uses the `apepojken` graph. The EngramHalo/EasiiX path documents a fused `eh_proj` and its own head mixer. These formats must not be interchanged.

The checked artifact repositories are:

- [`EasiiX/Qwen3.8-Flash-Next-MTP-Strix-Halo-GGUF`](https://huggingface.co/EasiiX/Qwen3.8-Flash-Next-MTP-Strix-Halo-GGUF), revision `6f7900648b1c6b14f067a182c640e47971e9ab35`;
- [`jockevaupptaget/Qwen3.8-Flash-Next-MTP-GGUF`](https://huggingface.co/jockevaupptaget/Qwen3.8-Flash-Next-MTP-GGUF), revision `69da733459b737b79273c0a322340de9c9c08fa2`.

EasiiX identifies the official Qwen checkpoint as the source, provides a matching converter command, credits the relevant design work, and includes the Qwen Community License 1.0. This is the better documented sidecar provenance. It still needs an exact file digest and GGUF tensor manifest in the intake lock file.

### Additional upstream MTP defects

The public PR 27836 thread also records:

- an old community export with missing hyper-connection tensors, an 8-byte-aligned data section, and an incorrect tensor count;
- a `blk.0` versus `blk.38` naming mismatch in another community path;
- a current standalone export/loader contradiction on `gfx1151`.

Do not accept an MTP file because it loads or gives high acceptance. Validate its tensor names, dimensions, GGUF alignment, count, source checkpoint, converter commit, and long-prompt output identity.

## Merge and conflict forecast

No local merge simulation was run. The items below are direct divergence facts plus an explicit conflict forecast.

1. **Upstream base versus EngramHalo:** 24 ahead and 9 behind at check. Expected manual conflict surfaces are `src/models/qwen4exp.cpp`, qwen4exp converter code, hybrid/QSA memory code, speculative decoding code, and CUDA/HIP kernels. EngramHalo is close enough for isolated replay, but not for an unreviewed merge.
2. **Upstream base versus `apepojken`:** 46 ahead and 44 behind. The fork contains pre-merge copies of qwen4exp history. A wholesale merge would create duplicate architecture changes and broad conflicts. Never merge it as a branch.
3. **MTP implementations:** EngramHalo commits `dc519925...` and `59ea5f93...`, upstream draft PR 27836, and `apepojken` commit `32af7090...` overlap in converter mappings, tensor names, loader rules, `t_h_nextn`, speculative state, and sidecar layout. Select one lineage. Do not stack them.
4. **Rollback and pooled QSA changes:** `32af7090...` and `472b7584...` both change hybrid-memory state operations. Port rollback first. Then rebase the pooled cache onto the accepted state API. Test clear, copy, remove, add, divide, save, restore, rejection, and slot reuse.
5. **GDN contiguous operand:** `51c0c10d...` touches the same qwen4exp graph file as EngramHalo's MTP and QSA work. The semantic change is small, but apply it manually to the accepted graph instead of cherry-picking the mixed commit.
6. **Server logits correction:** HaloFPX PR 35 comes from an older source tree. Reimplement the small provenance branch in the current server API and port its focused tests. Do not cherry-pick the complete historical commit.

## Ranked isolated-port list

The order balances correctness value, `gfx1151` benefit, review size, and state risk.

1. **HaloFPX sampled/raw logits provenance fix** — PR 35 / merge `167df62f...`. Small correctness fix. Low architecture coupling. Add focused sampled-row, raw-row, null-row, and count tests.
2. **Contiguous GDN convolution operand** — qwen4exp part of `51c0c10d...`. Very small graph change. Published prefill gain is plausible. Require greedy output identity and backend-operation tests.
3. **HIP wide top-k for RDNA 3.5** — `a8f7e226...`. Directly removes a known `gfx1151` CPU fallback in QSA. Keep an architecture gate. Test wide and fallback widths.
4. **PLE mapped-row prefetch and 160-value IQ4_NL gather** — split `c7e33834...` into two ports. This supports the model's unusually large PLE table. Test cold and warm reads, raw row identity, and non-PLE models.
5. **QSA selected-KV gather** — `62794305...`. High long-context value. Keep its off switch. Require dense-versus-gather logits, perplexity, slot reuse, and multi-sequence fallback tests.
6. **Recurrent rollback and PLE rejection history** — reviewed subchanges from `32af7090...` only. High correctness value for MTP rejection. High state risk. Do not include the donor's MTP graph or converter.
7. **Masked flash-attention skip and RDNA head-256 selection** — split `54d5baa8...`. It affects shared kernels. Require broad CUDA/HIP backend tests and a qwen4exp depth benchmark.
8. **Incremental pooled QSA summary keys** — `472b7584...`. Promising depth scaling, but it adds persistent watermarks to every state operation. Port only after rank 6 passes all state tests.
9. **One MTP lineage** — prefer a corrected and merged upstream PR 27836. Until then, retain the paired EngramHalo `dc519925...` + `59ea5f93...` implementation only in an isolated candidate. Pin the EasiiX artifact revision and exact file digest. Never mix MTP tensor formats.
10. **Chunked HIP GDN prefill** — `b744cd89...`. Last. It was not active in the donor's published `gfx1151` results. Keep opt-in until numerical and workload tests pass.

## License and provenance requirements

### Code

`llama.cpp`, EngramHalo, `apepojken/llama.cpp`, and HaloFPX declare the MIT License. For every adopted code segment:

1. keep the upstream MIT copyright and permission notice in distributions;
2. record the source repository, full commit SHA, file and hunk, human author, and local port commit;
3. preserve stated prior-art links and co-author or AI-assistance disclosures;
4. note whether the port is exact, adapted, or reimplemented;
5. keep third-party notices for bundled dependencies and copied kernels;
6. do not describe unsigned fork commits as verified releases.

### Weights and derived artifacts

The official model license is **Qwen Community License 1.0**. It requires the copyright and permission notice with copies or substantial portions. It also has commercial conditions for large products and for Model-as-a-Service or AI Work Assistant businesses. This report is not legal advice. A distributor or commercial service owner must review those terms.

For each GGUF or MTP artifact, store:

- official base repository and revision;
- conversion repository and full converter commit;
- exact conversion command and quantization command;
- input safetensor names and digests, where available;
- output file size and SHA-256 or LFS object ID;
- GGUF metadata and tensor manifest;
- model license file and source/model attribution;
- any importance matrix identity;
- the matching runtime commit and graph format.

Do not rely on a Hugging Face license tag alone. The `jockevaupptaget` repository's Apache-2.0 tag conflicts with the official Qwen license lineage and must not be copied into an intake manifest as authoritative.

## Acceptance gates for every port

Apply one port at a time to a fresh pinned candidate. Require:

1. build and focused unit tests;
2. backend-operation tests on HIP `gfx1151`;
3. base-model temperature-zero output comparison with the port off and on;
4. meaningful output checks above 718, 2,668, and 6,568 prompt tokens;
5. dense-versus-QSA and MTP-off-versus-MTP-on identity checks;
6. recurrent state remove, copy, clear, save, restore, rejection, and replay checks;
7. single-slot reuse with changed and restored prompt facts;
8. prompt processing and decode measurements at shallow and deep context;
9. a long tool-use conversation, not only `llama-bench`;
10. process, GPU-reset, memory-pressure, and rollback checks.

A token-rate gain does not pass the gate when output is empty, noisy, stale, or context-inconsistent.

## Known limits

- Source state is mutable. Recheck branch tips, PR 27836, and upstream master before implementation.
- GitHub compare divergence does not prove that a textual merge succeeds or fails. This intake did not run a merge simulation.
- Published performance and quality values were not reproduced during this source-only task.
- The public corruption report is detailed and hardware-specific, but it remains a third-party report without an attached automated harness.
- No exact file digest was fetched from Hugging Face during this pass. The implementation intake must lock each selected shard and sidecar file before use.
- This report does not approve deployment or commercial use.

## Direct links

- [Official model](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)
- [Qwen Community License 1.0](https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE)
- [Upstream qwen4exp PR 27742](https://github.com/ggml-org/llama.cpp/pull/27742)
- [Upstream MTP draft PR 27836](https://github.com/ggml-org/llama.cpp/pull/27836)
- [EngramHalo branch](https://github.com/Aristo94/EngramHalo.cpp/tree/strix-halo-qwen4exp)
- [Excluded Vulkan branch](https://github.com/apepojken/llama.cpp/tree/qwen4exp-spec-mtp)
- [Public corruption reproduction](https://github.com/ggml-org/llama.cpp/pull/27836#issuecomment-5456825600)
- [EasiiX matching MTP sidecar](https://huggingface.co/EasiiX/Qwen3.8-Flash-Next-MTP-Strix-Halo-GGUF)
- [Excluded incompatible MTP sidecar](https://huggingface.co/jockevaupptaget/Qwen3.8-Flash-Next-MTP-GGUF)
- [HaloFPX PR 35](https://github.com/JCFrags/HaloFPX/pull/35)
