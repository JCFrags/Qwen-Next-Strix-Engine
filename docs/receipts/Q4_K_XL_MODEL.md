# UD-Q4_K_XL model manifest

**Status:** `VERIFIED_MODEL_BYTES`

This manifest pins the quality-reference model bytes used by the project. Model files are not stored in this repository.

## Source

- Repository: <https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF>
- Revision: `c8b5954a88c2775c546b92593eda40ea041d3176`
- Quant directory: `UD-Q4_K_XL`
- Shards: 4
- Total bytes: `111334654784`

## Shards

| Shard | Size in bytes | SHA-256 | File |
|---:|---:|---|---|
| 1 | 10,946,624 | `4448186216b3af4cc558bbce2c3213f01608f8f8b2e5267a9767971dd3ec8082` | `Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` |
| 2 | 49,859,583,136 | `3f342f1c1580473f1ee94ddd5b28206e8c07a70fa1a366f59d1d6c922919a6c9` | `Qwen3.8-Flash-Next-UD-Q4_K_XL-00002-of-00004.gguf` |
| 3 | 49,376,141,504 | `56758f40269cad5cd9b0d3d6fbae0f40f6d5be6de49e4ab392dbe83157d9cbd3` | `Qwen3.8-Flash-Next-UD-Q4_K_XL-00003-of-00004.gguf` |
| 4 | 12,087,983,520 | `753bda48b98ba4f1636134a90a967de1b2d3908a236c026e464777342e53510a` | `Qwen3.8-Flash-Next-UD-Q4_K_XL-00004-of-00004.gguf` |

Two independent local copies were checked against these four hashes. Each copy matched all four values and the total byte count.

## Scope

- This is the base-model manifest.
- The MTP sidecar and vision projector are separate artifacts and are not part of this manifest.
- Matching bytes do not prove runtime correctness, output quality, context safety, or performance.
