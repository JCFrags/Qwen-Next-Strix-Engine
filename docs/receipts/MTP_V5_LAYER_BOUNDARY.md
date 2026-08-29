# Qwen4Exp MTP v5 layer-boundary receipt

**Status:** `BLOCKED_AFTER_LAYER_0`

**Qualification date:** 2026-08-29

## Semantic candidate

| Item | Value |
|---|---|
| Candidate commit | `9817f8ce6423ebf724e8b8e60782e1af2a32bcc6` |
| Candidate tree | `81d661bca717c5fc9e1d48661237c17f21ddde63` |
| Candidate binary SHA-256 | `c305d250b472eb9ebe64da711efe200e53612dc652b218b5090b4aa9894e9ea7` |
| Parent correction | Candidate v3 `53a26438bee732b780df6d797f0bfd29cde68df6` |
| Draft sidecar | Exact EasiiX 34-tensor Q8_0 file |
| Backend | HIP `gfx1151` |

Candidate v5 sequences the Qwen4Exp GDN recurrent helper during multi-row target verification. A bounded activation trace confirmed that the live target verification graph used five tokens, five outputs, one sequence, and four recurrent state banks. All 36 recurrent layers met the v5 activation conditions. Candidate v5 is not a semantic no-op.

## Strict recurrent result

MTP-OFF passed the complete four-request 47.7K recurrent gate. Requests 2 through 4 each reused 45,670 prompt tokens. All strict output checks passed.

MTP-ON remained blocked:

- request 1 drafted 51 tokens, accepted 42, and rejected 9;
- its full completion first differed from OFF at byte offset 145;
- OFF content SHA-256 was `b263044afa2cf9890fd35bd6ff8f699a710addd3f9f41a1d34bd36dc61729a9a`;
- MTP content SHA-256 was `5e8f15ca2f7ee0e7774c8c67611a50c2a7757603877fe38597e6bdbf026a7714`;
- request 2 was byte-identical to OFF and reused 45,670 prompt tokens;
- the gate stopped when a later completion contained another configured marker.

The visible answers remained correct. Full completion identity is mandatory, so v5 cannot be deployed with MTP.

## First divergent layer boundary

A guarded diagnostic compared one complete Qwen4Exp hyper-connection row at a time. It used a fresh process, one slot, one request, the same deterministic profile, and separate MTP-OFF and MTP-ON captures.

The diagnostic used the full 10,240-float row width. It did not log prompt text, completion text, token IDs, or tensor values.

| Boundary | Result |
|---|---|
| Layer 0 input | `IDENTICAL` |
| Layer 1 input | `DIFFERENT` |

The layer 0 input is the shared input to the first trunk layer. The layer 1 input is the output of layer 0. Therefore, the first target-row difference is created inside complete layer 0 processing. Sequencing only the GDN helper does not preserve the same target row as one-token decoding.

Diagnostic identity:

| Item | Value |
|---|---|
| Final diagnostic commit | `e5a1a2bdabe4b1330dd00d916440819380aa2327` |
| Final diagnostic tree | `8b323559c18dc7bc7c996383349991ab819c191f` |
| Diagnostic binary SHA-256 | `146787a5ed62a629c1e9b8fe31dea3a8efe068d59b685be755656a66c3edb740` |
| Layer 0 result SHA-256 | `5f24582ebe8e9ceff172b261faf42d898cc5f812d6469e0fb9dd26681b7c9984` |
| Layer 1 result SHA-256 | `c977e1a01d79bd26f93d58d4d5aad56e1137cebc44c02db2ecfce3613a0cfa2f` |

The diagnostic commits are private debug work. They are not a deployment candidate.

## Decision

Keep MTP disabled in the working profile. Do not promote candidate v5.

The next narrow experiment must give each Qwen4Exp target verification row the same one-row graph shape and recurrent-state progression as normal decoding, or identify and sequence the exact layer 0 sub-boundary that changes the row. A complete multi-row target graph is not strict-output safe yet.

Both completed diagnostic captures stopped cleanly. Swap was restored. No fatal GPU event occurred. Private requests, markers, responses, tensor fingerprints, logs, process data, and machine paths remain outside the repository.
