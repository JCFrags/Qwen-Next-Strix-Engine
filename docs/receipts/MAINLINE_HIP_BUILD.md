# Mainline HIP build-validation receipt

**Status:** `PASS_BUILD_VALIDATION`

This receipt records a clean `gfx1151` HIP build. It does not record model inference or a matched performance result.

## Source and host class

- Upstream: <https://github.com/ggml-org/llama.cpp>
- Commit: `6c84c7d5d8833c6e0df69628f75a0f599797934e`
- Subject: `model: add Qwen3.8-Flash-Next (qwen4exp) (#27742)`
- Source state after testing: clean detached checkout
- Host class: AMD Strix Halo `gfx1151`
- Operating system: CachyOS
- Kernel: `7.2.2-1-cachyos`

The isolated source and build directories were new for this work. No model was downloaded. No inference server was started, and no model inference was run.

## Toolchain

- CMake: `4.4.2`
- Ninja: `1.13.2`
- GCC/G++: `16.2.1 20260810`
- Host Clang: `22.1.8`
- HIP: `7.2.53211-3d9ef42`
- ROCm AMD Clang: `22.0.0git` from `f58b06dce1f9c15707c5f808fd002e18c2accf7e`
- Main ROCm packages: `7.2.4` series; `rocm-smi-lib` was `7.2.0`
- Detected GPU agent: `gfx1151`

## Configure controls

```text
CMAKE_BUILD_TYPE=Release
GGML_HIP=ON
GGML_VULKAN=OFF
AMDGPU_TARGETS=gfx1151
CMAKE_HIP_ARCHITECTURES=gfx1151
LLAMA_BUILD_TESTS=ON
LLAMA_BUILD_TOOLS=ON
LLAMA_BUILD_SERVER=ON
```

The build graph contained only `--offload-arch=gfx1151`. The built HIP library contained only the `gfx1151` architecture token.

`CMakeCache.txt` SHA-256:

```text
25a8c143ceda98347c3efc49c1691b2d28c022993b1301557d48be894aedce7f
```

## Artifact identities

| Artifact | SHA-256 |
|---|---|
| `llama-server` | `c427038c103ed289296e6417a9a3da33a5338c8b38971bbe1c1c7a06902f7d4e` |
| `llama-bench` | `2488abf16a2c20f5cf090b7ae05c9d7e20cfee70424f736aaadd935cec674dd0` |
| `test-backend-ops` | `f12ee79fadf8b3bf7ad4c6c45d8425b4137bffc50086ca13e816de4e250b5ee4` |
| `test-backend-sampler` | `464a40fa3e364e872a1f74d8405450d33f23a98a50d4da534274722368bc5a8b` |
| `libggml-hip.so.0.22.0` | `bb27f1348b2a00c0b59a7d60144420d4b77fa4d82423fcd37bd50c13d28d234a` |

The checked executables resolved their HIP backend from the isolated build. The backend library resolved ROCm libraries from the installed ROCm `7.2.4` stack.

## Backend test

```text
13245/13245 tests passed
Backend ROCm0: OK
2/2 backends passed
1/1 Test #44: test-backend-ops: Passed
100% tests passed out of 1
Total Test time (real): 138.12 seconds
```

Unsupported operation variants were reported as unsupported. They were not test failures.

## Limits

- This is a build and backend-operation receipt only.
- It does not prove model load, output correctness, context safety, MTP correctness, vision support, or performance.
- It is not a matched HIP-versus-Vulkan performance result.
