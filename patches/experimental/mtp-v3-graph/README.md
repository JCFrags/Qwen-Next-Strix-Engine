# Experimental Qwen4Exp MTP graph correction v3

**State:** `INACTIVE_EXPERIMENTAL`

**MTP-ON decision:** `BLOCKED_LONG_CONTEXT_OUTPUT_IDENTITY`

Do not apply this patch to the working profile. It corrects the short multi-row target graph, but it does not preserve long-context MTP output. The qualified working profile keeps MTP disabled.

## Patch identity

- Candidate commit: `53a26438bee732b780df6d797f0bfd29cde68df6`
- Parent: candidate v1 `1baf32a24619aa8f6eac684308fc5852bb3cc3f9`
- Parent base: llama.cpp `6c84c7d5d8833c6e0df69628f75a0f599797934e`
- Candidate author: `Home Services Lead <noreply@local.invalid>`
- Candidate author date: `2026-08-29T05:12:25-07:00`
- Stable patch ID: `a53dd227066fe631422ad809e4e1b3c10bdb794b`
- Export SHA-256: `ce1219a206b687a5970a5139aa841d27674ba2a2c3d7ec69bbaf45b3f8eca71f`
- Candidate binary SHA-256: `c91576fb1779160645db5d3ff3b4e6eaafef5e6c95587e66bfebd7beb358e4f0`
- File: [`0001-qwen4exp-align-EasiiX-MTP-graph-with-upstream-corrections.patch`](0001-qwen4exp-align-EasiiX-MTP-graph-with-upstream-corrections.patch)

Apply the v1 patch first. Then apply this one-commit `git format-patch` export. A clean application to v1 produced the exact candidate tree `1c2db8ae0d2740ba50d7ec57cbfd2f57249fb8d5`.

## Source and license

The correction keeps the exact EasiiX 34-tensor sidecar layout. It adapts relevant graph behavior from upstream llama.cpp pull request 27836, reviewed at head `1d8de7c1b0c7d2febf8f983174d8e6a711e2b1af`. The commit message names upstream correction commit `d72620018f612bb05d16e585108e3440947a1f9f`.

The patch:

- normalizes each hidden-state group independently;
- materializes both next-token hidden exports;
- removes the invalid narrow MTP embedding export;
- exposes target hidden rows only when extraction is enabled.

The base and donor code use the MIT License. Keep the notice in [`LICENSE`](LICENSE) when applying or redistributing the patch.

## Verified behavior

The candidate compiled successfully. HIP backend operations and backend sampler tests passed. The Qwen4Exp HIP architecture row passed with roundtrip `OK` and NMSE `9.92e-14`. The broad architecture executable still reported failures in unrelated architecture rows, so this archive does not claim a complete architecture-suite pass.

Short controls passed:

- target-only n-gram verification: 32 drafted and 32 accepted tokens, mean speculative length 17.0, exact OFF bytes;
- pure MTP maximum 1: 19 drafted and 19 accepted tokens, mean speculative length 2.0, exact OFF bytes;
- pure MTP maximum 4: 32 drafted and 32 accepted tokens, mean speculative length 5.0, exact OFF bytes.

The strict 47.7K recurrent gate remained blocked. MTP-OFF passed all four requests and reused 45,670 tokens on requests 2 through 4. Pure MTP diverged from OFF on the first long request at byte offset 145. It drafted 52 tokens, accepted 42, and rejected 10. The visible answer remained correct, but hidden completion content contained another configured marker. An `ngram-mod` control made no drafts on that request and was byte-identical to OFF. This isolates the remaining defect to the long-context MTP path.

See [`../../../docs/receipts/MTP_V3_BLOCKER.md`](../../../docs/receipts/MTP_V3_BLOCKER.md) for the public-safe qualification receipt.
