# Qwen4Exp MTP v3 blocker receipt

**Status:** `BLOCKED_LONG_CONTEXT_OUTPUT_IDENTITY`

**Qualification date:** 2026-08-29

## Candidate identity

| Item | Value |
|---|---|
| Candidate commit | `53a26438bee732b780df6d797f0bfd29cde68df6` |
| Parent | Candidate v1 `1baf32a24619aa8f6eac684308fc5852bb3cc3f9` |
| Mainline base | llama.cpp `6c84c7d5d8833c6e0df69628f75a0f599797934e` |
| Candidate binary SHA-256 | `c91576fb1779160645db5d3ff3b4e6eaafef5e6c95587e66bfebd7beb358e4f0` |
| Correction export SHA-256 | `ce1219a206b687a5970a5139aa841d27674ba2a2c3d7ec69bbaf45b3f8eca71f` |
| Stable patch ID | `a53dd227066fe631422ad809e4e1b3c10bdb794b` |
| Applied tree | `1c2db8ae0d2740ba50d7ec57cbfd2f57249fb8d5` |
| Draft sidecar | Exact EasiiX 34-tensor Q8_0 file |
| Backend | HIP `gfx1151` |

The correction keeps the EasiiX sidecar format. It changes only `src/models/qwen4exp.cpp`. The exported patch applies cleanly after candidate v1 and produces the exact candidate tree.

## Build and focused tests

- The candidate compiled successfully.
- HIP backend operations passed.
- The backend sampler test passed.
- The Qwen4Exp HIP architecture row passed with roundtrip `OK` and NMSE `9.92e-14`.
- The broad architecture executable reported unrelated architecture failures. This receipt does not claim that the complete architecture suite passed.

## Short identity controls

All short controls used deterministic greedy output and compared full completion bytes with MTP-OFF.

| Control | Drafted | Accepted | Rejected | Mean speculative length | Full bytes |
|---|---:|---:|---:|---:|---|
| Target-only n-gram | 32 | 32 | 0 | 17.0 | `PASS` |
| Pure MTP, maximum 1 | 19 | 19 | 0 | 2.0 | `PASS` |
| Pure MTP, maximum 4 | 32 | 32 | 0 | 5.0 | `PASS` |

These results show that the corrected target multi-row graph works for the short control. They do not qualify long-context MTP.

## Strict recurrent result

MTP-OFF passed the four-request 47.7K A/B/A gate:

- all four strict visible and full-content checks passed;
- requests 2 through 4 reused exactly 45,670 prompt tokens;
- their processed tails were 2,056, 2,056, and 2,057 tokens;
- the server remained healthy.

MTP-ON stopped at request 1:

- 52 tokens were drafted;
- 42 were accepted and 10 were rejected;
- full completion bytes first differed from OFF at byte offset 145;
- OFF content SHA-256 was `b263044afa2cf9890fd35bd6ff8f699a710addd3f9f41a1d34bd36dc61729a9a`;
- MTP content SHA-256 was `8ec9177f8a0a7e9f5d15adcbe325c32ea3488f88ac63703bcb4d67204eecd9d2`;
- the visible answer remained correct;
- hidden completion content contained the marker assigned to request 4.

A bounded source disambiguation used the same first long request:

- `ngram-mod` made no drafts and was byte-identical to OFF;
- pure MTP reproduced the exact blocked content hash, byte offset, and 42-of-52 acceptance result.

The remaining defect is in the long-context Qwen4Exp MTP path. It is not caused by `ngram-mod` on this request.

## Safety and decision

Both bounded campaigns disabled swap during model execution and restored it afterward. The servers stopped cleanly. Required ports and model processes were clear. No fatal AMDGPU event occurred.

The real Pi gate did not run because the strict recurrent gate failed first. Keep MTP disabled in the working profile. Do not deploy candidate v3 as an MTP runtime.

Private prompts, marker values, responses, logs, process data, and machine paths remain outside the repository.
