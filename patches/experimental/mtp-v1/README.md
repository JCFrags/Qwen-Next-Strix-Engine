# Experimental Qwen4Exp MTP candidate v1

**State:** `INACTIVE_EXPERIMENTAL`

**MTP-ON decision:** `BLOCKED_MTP_OUTPUT_IDENTITY`

Do not apply this patch to the working profile. The working profile uses the candidate binary with MTP disabled. This archive preserves the reviewed source change for future correction work. It does not state that MTP rollback works.

## Patch identity

- Candidate commit: `1baf32a24619aa8f6eac684308fc5852bb3cc3f9`
- Parent: llama.cpp `6c84c7d5d8833c6e0df69628f75a0f599797934e`
- Candidate author: `Temporary Implementation Agent <noreply@local.invalid>`
- Candidate author date: `2026-08-29T01:03:38-07:00`
- Stable patch ID: `a13a649157db5a5dfc112361146f4db6dc071e0c`
- Export SHA-256: `327d5088454a6b4f13d5149762e8273874321e5dd41a912fdd0f69272ad61bd3`
- File: [`0001-qwen4exp-mainline-6c84-EasiiX-MTP-candidate.patch`](0001-qwen4exp-mainline-6c84-EasiiX-MTP-candidate.patch)

The file is a one-commit `git format-patch` export. It preserves the candidate commit author, date, subject, message, parent relationship, and donor commit IDs.

## Donor provenance

The candidate narrowly replays two commits from [Aristo94/EngramHalo.cpp](https://github.com/Aristo94/EngramHalo.cpp):

- `dc519925ca91b9e487bd633c1636f553f06224ff`, `qwen4exp: MTP draft head and mtp-only sidecar loading`;
- `59ea5f93f810ceffec0d970b36336a5251f88022`, `convert: export the qwen4exp MTP block`.

Both donor commits identify the author as `Aristo94 <64758918+Aristo94@users.noreply.github.com>` and the date as `2026-08-27T21:46:21+02:00`. The candidate commit message preserves both exact donor IDs.

The base and donor repositories use the MIT License with the ggml authors' copyright notice. The export is license-compatible. The exact required notice is included in [`LICENSE`](LICENSE). Keep that notice when applying or redistributing the patch.

## Blocked result

The exact EasiiX 34-tensor sidecar loaded and recurrent-state rejection was exercised. MTP-ON still diverged from MTP-OFF at generated tokens 32, 31, and 32. Request 3 emitted another configured marker in completion content. Draft maxima 1 and 4 produced the same divergent bytes.

Candidate v2 `rs0` is intentionally absent because it did not change runtime behavior.
