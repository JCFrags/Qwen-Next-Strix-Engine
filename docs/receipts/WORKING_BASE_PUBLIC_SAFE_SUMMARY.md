# Working-base v1 public-safe summary

**Status:** `PASS_WORKING_BASE`

**Reviewed source summary SHA-256:** `98bf7494ad63cefb3bac8cd2775207b9e3d19f4df63f8b0b493880e9bf26070f`

This is a privacy-reviewed copy of the qualification summary. Private machine paths, process data, prompts, marker values, response bodies, logs, model paths, and session data are intentionally absent.

- Source commit: `1baf32a24619aa8f6eac684308fc5852bb3cc3f9`.
- Binary SHA-256: `496b5151f5be070ab4cfc24cbbd6fa62d3986b2fcc25aab019f29ed828c6ab8f`.
- Model: exact Unsloth `Qwen3.8-Flash-Next-UD-Q4_K_XL` four-shard hash gate passed.
- Profile: HIP `gfx1151`; 65,536 context; one slot and client; Q8_0 K/V; batch 4,096; microbatch 2,052; automatic load mode; MTP off; vision off.
- Base recurrent gate: PASS. Requests 2 through 4 planned and reused 45,670 tokens. Their processed prompt tails were 2,056, 2,056, and 2,057 tokens. Exact visible-marker and full-completion marker checks passed.
- Real Pi gate: PASS. The loop made 12 ordered tool turns. The final prompt was 45,841 tokens. Cumulative prompt input was 145,018 tokens. The final cache reuse was 35,388 tokens, or 77.20%. The final answer was exact. No phantom marker or file appeared.
- Pi performance: aggregate prompt processing was 222.97 tok/s. Aggregate generation was 16.68 tok/s. The final request measured 185.02 prompt tok/s and 11.44 generated tok/s.
- Direct gate: 72.22 prompt tok/s and 19.32 generated tok/s.
- Stability: no crash, reset, fatal GPU event, server error, or client error occurred.
- Restoration: swap was restored on both qualification hosts and was fully free when restoration completed.

MTP remains disabled and `BLOCKED`. Vision and context above 65,536 tokens remain unqualified.
