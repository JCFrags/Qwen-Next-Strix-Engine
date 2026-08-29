# Working-base v1 qualification receipt

**Status:** `PASS_WORKING_BASE`

**Qualification date:** 2026-08-29

**Public source summary SHA-256:** `98bf7494ad63cefb3bac8cd2775207b9e3d19f4df63f8b0b493880e9bf26070f`

## Accepted identity

| Item | Accepted value |
|---|---|
| Source commit | `1baf32a24619aa8f6eac684308fc5852bb3cc3f9` |
| Source parent | llama.cpp `6c84c7d5d8833c6e0df69628f75a0f599797934e` |
| Binary SHA-256 | `496b5151f5be070ab4cfc24cbbd6fa62d3986b2fcc25aab019f29ed828c6ab8f` |
| Model | Exact Unsloth `UD-Q4_K_XL` four-shard manifest |
| Backend | HIP `gfx1151` |
| Context and scheduling | 65,536 tokens; one slot; one client; no continuous batching |
| Cache | Q8_0 K and V |
| Batch / microbatch | 4,096 / 2,052 |
| Load behavior | Automatic defaults by option omission |
| Optional model inputs | MTP disabled; vision disabled |

The accepted launch arguments are in [`../WORKING_BASE.md`](../WORKING_BASE.md). That document also records the 45,670-token checkpoint alignment that requires microbatch 2,052.

## Strict recurrent cache gate

The fixed four-request gate passed.

- Requests 2 through 4 each had 45,670 planned common-prefix tokens.
- Each request reused exactly 45,670 tokens.
- Their processed prompt tails were 2,056, 2,056, and 2,057 tokens.
- Each visible answer matched its configured marker exactly.
- Each full completion passed the configured-marker exclusion check.
- No stale marker, truncation, limit stop, cache-accounting error, reset, or fatal GPU event occurred.

Marker values, prompt text, rendered requests, completion bodies, and raw endpoint data remain private. They are not needed to reproduce the public profile.

## Real Pi gate

The real Pi loop passed.

- It completed 12 ordered tool turns with exact typed arguments and fixture order.
- The final prompt contained 45,841 tokens.
- Cumulative prompt input was 145,018 tokens.
- The final request reused 35,388 tokens, or 77.20%.
- The final answer matched exactly. Its safe SHA-256 was `44e4636913f340bc7d584f4a92a719a44aa4afbfa80b333a93b6dfa187d59f77`.
- No phantom marker or file appeared.
- Aggregate prompt processing was 222.97 tok/s. Aggregate generation was 16.68 tok/s.
- The final request measured 185.02 prompt tok/s and 11.44 generated tok/s.

The direct gate also passed at 72.22 prompt tok/s and 19.32 generated tok/s.

No crash, reset, fatal GPU event, server error, or client error occurred. Swap was restored on both qualification hosts after the campaign and was fully free at restoration.

## MTP decision

**MTP status:** `BLOCKED`; disabled in the working profile.

Candidate v1 MTP-ON used the exact EasiiX 34-tensor sidecar and exercised recurrent-state rejection. It diverged from MTP-OFF at generated tokens 32, 31, and 32 in the three recurrent comparisons. Request 3 also emitted another configured marker in completion content. Draft maxima 1 and 4 produced the same divergent bytes.

These results do not prove that the candidate's MTP rollback patch works. The exported candidate patch is inactive and experimental. Candidate v2 `rs0` is not exported because it did not change runtime behavior.

Candidate v3 corrected short multi-row target identity. It still failed the first 47.7K MTP request while MTP-OFF passed the complete four-request gate. Pure MTP reproduced the defect, including 42 accepted and 10 rejected drafts. Keep MTP disabled. See [`MTP_V3_BLOCKER.md`](MTP_V3_BLOCKER.md).

## Limits

- This receipt qualifies only the fixed base profile.
- MTP is blocked.
- Vision is unqualified.
- Context above 65,536 tokens is unqualified.
- The receipt does not qualify another binary, model quant, backend, load mode, batch shape, or microbatch value.
