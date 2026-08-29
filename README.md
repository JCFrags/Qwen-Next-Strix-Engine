# Qwen Next Strix Engine

An experimental runtime project for Qwen3.8-Flash-Next on AMD Strix Halo (`gfx1151`).

## Goals

- Improve useful single-user prompt processing and generation speed.
- Compare HIP/ROCm, Vulkan, and other credible local backends with matched tests.
- Support one or two matching 128 GB Strix Halo hosts when evidence justifies it.
- Preserve output, recurrent state, prompt reuse, MTP rollback, and Pi tool-loop correctness.

## Initial reference profile

- Model: Unsloth `Qwen3.8-Flash-Next-UD-Q4_K_XL`
- Draft: EasiiX Q8_0 MTP
- Vision: F16 projector
- Context: 65,536
- K/V cache: Q8_0
- Scheduling: one slot and one client
- Hardware: AMD Strix Halo `gfx1151`

The project is experimental. A high configured context limit or coherent short output is not proof of correctness. Candidate runtimes must pass matched output, state, cache-reuse, long-prompt, GPU-stability, and real agent tool-loop tests.

## Repository state

The repository now contains:

- reviewed source-intake and backend-matrix documents;
- a correctness-first evidence evaluator and offline tests;
- public build-validation receipts for the pinned mainline HIP and Vulkan builds.

The build receipts prove clean source, artifact identity, and backend-operation tests only. Model correctness and matched performance qualification remain in progress.
