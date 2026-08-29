# Qwen3.8-Flash-Next harness

This harness evaluates result files. It does not start a server or call a model. A HIP, Vulkan, CPU, remote, or future backend adapter can produce the same JSON format.

The fixed profile is [`harness/qwen38_matrix.json`](../harness/qwen38_matrix.json). It maps the private test matrix to explicit cases for admission, build identity, deterministic output, the 47.7K A/B/A sequence, MTP rollback, optional QSA cache state, performance, real Pi use, vision, stability, and rollback.

## Safety and privacy

Do not put a credential, private host name, user name, absolute private path, model path, prompt text, expected answer, or Pi session data in a result file. Use a lowercase SHA-256 receipt for private source evidence. Use a SHA-256 host fingerprint instead of a host name. Keep raw private logs outside the harness output.

The harness uses only the Python standard library. It does not use the network.

## Files

- `harness/qwen38_harness.py`: strict parser, validator, pair evaluator, and CLI.
- `harness/qwen38_matrix.json`: versioned fixed gate profile.
- `tests/`: offline parser and evaluator tests.

An adapter owns these generated files:

- one campaign JSON file;
- one result JSON file for each static case;
- one result JSON file for each performance OFF or ON run;
- one summary JSON file written by the evaluator.

Keep the summary outside the result directory. The evaluator reads every `*.json` file in the result directory as a result.

## Campaign format

```json
{
  "schema_version": 1,
  "profile_id": "qwen38-flash-next-strix-v1",
  "campaign_id": "candidate-001",
  "features": {
    "qsa_cache": false
  },
  "observed_run_noise_percent": {
    "prompt_tokens_per_second": 2.0,
    "generated_tokens_per_second": 2.0
  }
}
```

Set `qsa_cache` to `true` only when the pooled QSA cache is enabled. All Gate E cases then become required. Supply measured noise from matched baseline repeats. The validator rejects a missing noise value.

## Static result format

Each required check has an explicit Boolean value. `status` must be `pass` if and only if all supplied checks are true. A false check with `status: pass`, or all true checks with `status: fail`, is ambiguous and is rejected.

```json
{
  "schema_version": 1,
  "profile_id": "qwen38-flash-next-strix-v1",
  "campaign_id": "candidate-001",
  "case_id": "b_short_133",
  "gate": "B",
  "status": "pass",
  "checks": {
    "exact_expected_answer": true,
    "no_malformed_text": true
  },
  "metrics": {}
}
```

Read the matrix profile for the exact case IDs, checks, and required metrics. Gate A requires source, patch set, compile command, binary, loaded backend library, and launch receipts. Admission requires process, memory-owner, port, and expected-runtime receipts. The vision case requires the projector receipt.

## Performance result format

Use one file for one variant in one pair. The corresponding OFF and ON files must have the same `pair_id`, `depth`, and `comparison` object. Their runtime identities can differ. The `feature_state` must match the variant.

```json
{
  "schema_version": 1,
  "profile_id": "qwen38-flash-next-strix-v1",
  "campaign_id": "candidate-001",
  "case_id": "f_47k_pair1_on",
  "gate": "F",
  "status": "pass",
  "checks": {
    "request_completed": true,
    "output_matches_correctness_reference": true,
    "no_unexpected_warning_or_fallback": true
  },
  "metrics": {
    "prompt_tokens": 47700,
    "prompt_tokens_per_second": 350.0,
    "generated_tokens": 256,
    "generated_tokens_per_second": 28.2,
    "time_to_first_token_ms": 140000.0,
    "inter_token_latency_ms": {"p50": 34.0, "p95": 39.0, "max": 55.0},
    "mtp": {"accepted_tokens": 180, "drafted_tokens": 230},
    "prompt": {"reused_tokens": 0, "new_tokens": 47700},
    "gpu": {"utilization_percent": 96.0, "clock_mhz": 2800.0},
    "memory": {"gtt_bytes": 1, "mem_available_bytes": 1, "swap_bytes": 0},
    "server": {"warning_count": 0, "fallback_count": 0}
  },
  "performance": {
    "pair_id": "pair-1",
    "variant": "on",
    "depth": "47.7k",
    "sequence": 2,
    "comparison": {
      "backend": "backend-family",
      "host_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "model_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "draft_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "projector_sha256": "disabled",
      "context_tokens": 65536,
      "slots": 1,
      "kv_type": "q8_0",
      "batch_size": 8192,
      "microbatch_size": 2048,
      "mtp_mode": "draft-mtp,ngram-mod",
      "mtp_draft_max": 4,
      "mtp_probability_threshold": 0.75,
      "sampling_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "prompt_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "power_state": "fixed-profile",
      "server_environment_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
    },
    "runtime_identity": {
      "source_commit": "abcdef1",
      "patchset_sha256": "1111111111111111111111111111111111111111111111111111111111111111",
      "binary_sha256": "2222222222222222222222222222222222222222222222222222222222222222",
      "backend_library_sha256": "3333333333333333333333333333333333333333333333333333333333333333",
      "launch_sha256": "4444444444444444444444444444444444444444444444444444444444444444",
      "feature_state": "on"
    }
  }
}
```

The validator requires all fixed comparison fields. It rejects changed context, slot count, K/V type, batch sizes, or MTP settings. It also rejects unmatched pairs, duplicate sequence numbers, non-finite numbers, negative metrics, unordered latency summaries, and inconsistent token counts.

Collect at least three complete OFF/ON pairs at each depth: `shallow`, `8k`, `32k`, and `47.7k`. Use sequence numbers to preserve counterbalanced execution order.

## Commands

Validate one file:

```text
python3 harness/qwen38_harness.py validate-result \
  --matrix harness/qwen38_matrix.json \
  --campaign campaign.json \
  results/b_short_133.json
```

Evaluate a complete campaign:

```text
python3 harness/qwen38_harness.py evaluate \
  --matrix harness/qwen38_matrix.json \
  --campaign campaign.json \
  --results-dir results \
  --output summary.json
```

Run offline tests:

```text
python3 -m unittest discover -s tests -v
```

## Stable exit codes

| Code | Meaning |
|---:|---|
| 0 | Complete evidence. All correctness results pass. Performance is outside noise with no beyond-noise regression. |
| 2 | CLI usage error. |
| 10 | Evidence is malformed, incomplete, unmatched, duplicated, or ambiguous. |
| 20 | Complete evidence contains an explicit correctness failure. This result overrides speed. |
| 30 | Correctness passes, but performance does not qualify outside measured noise. |

A single-file validation also returns 20 for a structurally valid failed result.

## Decision rules

The evaluator first requires every applicable static result and three complete matched pairs at every depth. It rejects missing metrics and ambiguous status/check combinations.

For performance, it computes each pair's relative throughput change. It then computes the median change at each depth. A candidate qualifies when at least one 47.7K throughput median is above its measured noise and neither throughput metric regresses beyond noise at any depth.

The evaluator reports the 345 prompt tok/s and 28 generated tok/s project targets. These targets are warnings, not permission to accept incorrect output. A complete explicit correctness failure always returns code 20, even when speed targets pass.

## Known limits

- The harness validates result evidence. It cannot prove that an adapter reported honest measurements.
- Raw GPU logs, tool traces, prompts, expected values, and private state remain outside this patch. Store only their safe receipts in results.
- Counterbalanced order is recorded but not statistically tested.
- The evaluator uses medians and measured noise bounds. It does not run a significance test.
- Gate E is not required when the campaign declares the QSA cache disabled.
