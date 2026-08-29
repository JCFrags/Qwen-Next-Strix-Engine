# Experiment ledger

Public entries contain decisions and safe aggregate evidence only. Private prompts, markers, responses, logs, machine paths, process data, and session data stay outside this repository.

| Date | Candidate | Profile | Result | Public decision |
|---|---|---|---|---|
| 2026-08-28 | Mainline `6c84c7d…` | HIP and Vulkan build validation | `PASS_BUILD_VALIDATION` | Build operation only. Model qualification was still pending. |
| 2026-08-29 | Candidate v1 `1baf32a…` | HIP, exact Q4_K_XL, 65,536, one slot, Q8_0 K/V, 4,096/2,052, MTP off, vision off | `PASS_WORKING_BASE` | Strict recurrent cache gate and real Pi loop passed. |
| 2026-08-29 | Candidate v1 `1baf32a…` | Same base plus exact EasiiX 34-tensor MTP sidecar | `BLOCKED_MTP_OUTPUT_IDENTITY` | MTP-ON diverged from OFF at generated tokens 32/31/32. Request 3 emitted another configured marker. Draft maxima 1 and 4 gave the same divergent bytes. Keep MTP disabled. |
| 2026-08-29 | Candidate v2 `rs0` | MTP rollback experiment | `NO_RUNTIME_CHANGE` | Do not export. Do not claim a rollback correction. |
| 2026-08-29 | Candidate v3 `53a2643…` | Corrected Qwen4Exp multi-row graph; short n-gram and pure-MTP controls | `PASS_SHORT_IDENTITY` | Full bytes matched OFF at MTP maxima 1 and 4. This result did not qualify long context. |
| 2026-08-29 | Candidate v3 `53a2643…` | Exact Q4_K_XL, 65,536, 4,096/2,052, strict 47.7K MTP OFF/ON | `BLOCKED_LONG_CONTEXT_OUTPUT_IDENTITY` | OFF passed four requests. Pure MTP diverged on request 1 at byte offset 145 after 42 accepted and 10 rejected drafts. Keep MTP disabled. |
| 2026-08-29 | Candidate v5 `9817f8c…` | Sequential GDN helper, exact Q4_K_XL, strict 47.7K MTP OFF/ON | `BLOCKED_LONG_CONTEXT_OUTPUT_IDENTITY` | The v5 guard ran in all recurrent layers. Request 1 still diverged at byte offset 145 after 42 accepted and 9 rejected drafts. |
| 2026-08-29 | Candidate v5 layer diagnostic `e5a1a2b…` | Complete 10,240-float target row, fresh OFF/ON processes, one selected layer per run | `BLOCKED_AFTER_LAYER_0` | Layer 0 input matched. Layer 1 input differed. Complete layer 0 processing creates the first hidden-row difference. |
| 2026-08-29 | Vision | Working-base runtime | `UNQUALIFIED` | Projector omitted. |
| 2026-08-29 | Higher context | Above 65,536 | `UNQUALIFIED` | Requires a new strict campaign. |

## Working-base evidence

- Recurrent requests 2 through 4 planned and reused 45,670 prompt tokens.
- Their processed tails were 2,056, 2,056, and 2,057 tokens.
- Exact visible-marker and full-completion marker checks passed.
- The real Pi loop made 12 ordered tool turns.
- Its final prompt was 45,841 tokens. Cumulative prompt input was 145,018 tokens.
- Its final cache reuse was 35,388 tokens, or 77.20%.
- The final answer matched exactly. No phantom marker or file appeared.
- Pi aggregate rates were 222.97 prompt tok/s and 16.68 generated tok/s.
- Final-request rates were 185.02 prompt tok/s and 11.44 generated tok/s.
- Direct rates were 72.22 prompt tok/s and 19.32 generated tok/s.
- No crash, reset, or fatal GPU event occurred.
- Swap was restored on both qualification hosts and was fully free at restoration.
