# Current status

## Working base

`PASS_WORKING_BASE`

The accepted public profile uses candidate commit `1baf32a24619aa8f6eac684308fc5852bb3cc3f9` with binary SHA-256 `496b5151f5be070ab4cfc24cbbd6fa62d3986b2fcc25aab019f29ed828c6ab8f`. It runs exact `UD-Q4_K_XL` at 65,536 context with one slot, Q8_0 K/V, batch 4,096, microbatch 2,052, automatic load behavior, MTP off, and vision off.

The strict four-request recurrent gate and the real 12-tool Pi loop passed. No crash, reset, or fatal GPU event occurred. See [`receipts/WORKING_BASE_V1.md`](receipts/WORKING_BASE_V1.md).

## Feature decisions

| Feature | State | Decision |
|---|---|---|
| Base text at 65,536 | `PASS` | Reproducible working base. |
| Recurrent cache reuse | `PASS` | Keep microbatch 2,052. |
| Real Pi loop | `PASS` | Exact 12-tool loop passed. |
| MTP | `BLOCKED` | Disabled. MTP-ON output diverged from OFF. |
| Vision | `UNQUALIFIED` | Do not enable in this profile. |
| Context above 65,536 | `UNQUALIFIED` | Needs a new full qualification. |
| Candidate v1 patch | `INACTIVE_EXPERIMENTAL` | Preserved only for review and future correction work. |
| Candidate v2 `rs0` | `OMITTED` | It did not change runtime behavior. |

The launch template is [`../scripts/launch-working-base.sh`](../scripts/launch-working-base.sh). It pins the accepted binary, model bytes, and inference arguments.
