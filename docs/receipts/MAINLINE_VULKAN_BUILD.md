# Mainline Vulkan build-validation receipt

**Status:** `PASS_BUILD_VALIDATION`

This receipt records a clean Vulkan/RADV build on Strix Halo. It does not record model inference or a matched performance result.

## Source and host class

- Upstream: <https://github.com/ggml-org/llama.cpp>
- Commit: `6c84c7d5d8833c6e0df69628f75a0f599797934e`
- Subject: `model: add Qwen3.8-Flash-Next (qwen4exp) (#27742)`
- Source state after validation: clean detached checkout
- Host class: AMD Strix Halo `gfx1151`
- Selected device: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
- RADV: Mesa `26.2.1-arch3.1`
- Vulkan API: `1.4.354`
- RADV driver ID: `DRIVER_ID_MESA_RADV`

Receipt recovery validated the existing build and preserved logs. It did not rebuild, reconfigure, rerun the backend test, or start model inference.

## Configure controls

```text
BUILD_SHARED_LIBS=ON
CMAKE_BUILD_TYPE=Release
GGML_BACKEND_DL=OFF
GGML_BLAS=OFF
GGML_CUDA=OFF
GGML_HIP=OFF
GGML_METAL=OFF
GGML_NATIVE=ON
GGML_OPENCL=OFF
GGML_RPC=OFF
GGML_SYCL=OFF
GGML_VULKAN=ON
GGML_VULKAN_RUN_TESTS=OFF
LLAMA_BUILD_EXAMPLES=OFF
LLAMA_BUILD_SERVER=ON
LLAMA_BUILD_TESTS=ON
LLAMA_BUILD_TOOLS=ON
CMAKE_GENERATOR=Ninja
Vulkan_GLSLC_EXECUTABLE=/usr/bin/glslc
Vulkan_INCLUDE_DIR=/usr/include
Vulkan_LIBRARY=/usr/lib/libvulkan.so
```

The build selected RADV through the system Radeon ICD. HIP was disabled.

`CMakeCache.txt` SHA-256:

```text
dfb74fa392e0a07ec90282c631d9f80a1c70081389b724da3b10b35c95114622
```

## Artifact identities

| Artifact | Size in bytes | SHA-256 |
|---|---:|---|
| `llama-server` | 16,000 | `b537dc6eae2a0157a23038323a7a1a43e323873fdf781c0c5e9b1652a345c790` |
| `llama-bench` | 15,992 | `f29063a5d817e3f117a3c4393625df9b617e0450e3044e9117ace066de260231` |
| `test-backend-ops` | 1,275,936 | `88c56d653802ce1e718c17924aaab1e101770f8511e4f5c995c203e7f37dccf5` |
| `test-backend-sampler` | 173,040 | `76cd5680b6e5f320183fa590ddc643121547ae4d08f9a457918e6e7886ee3c3d` |
| `libggml-vulkan.so.0.22.0` | 55,922,600 | `7f59ea7be3569a7f26a4dfe177818b03fa00e82e831b1b7b27ee8c8dbec1d2e2` |

A live `ldd` check found no unresolved library for `llama-server`, `llama-bench`, `test-backend-ops`, or `libggml-vulkan.so.0.22.0`. No HIP library resolved into these checked artifacts.

## Backend test

```text
17251/17251 tests passed
Backend Vulkan0: OK
2/2 backends passed
1/1 Test #44: test-backend-ops ... Passed 380.80 sec
100% tests passed out of 1
TEST_EXIT_CODE=0
```

The raw case count differs from the HIP backend. Do not use these raw case counts as a speed or completeness comparison.

## Limits

- This is a build and backend-operation receipt only.
- It does not prove model load, output correctness, context safety, MTP correctness, vision support, or performance.
- It is not a matched HIP-versus-Vulkan performance result.
- This build used `GGML_NATIVE=ON`.
