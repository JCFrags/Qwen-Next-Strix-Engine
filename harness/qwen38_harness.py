#!/usr/bin/env python3
"""Validate backend-neutral Qwen3.8-Flash-Next result files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from statistics import median
from typing import Any, Iterable

EXIT_QUALIFIED = 0
EXIT_USAGE = 2
EXIT_INVALID_EVIDENCE = 10
EXIT_CORRECTNESS_FAILED = 20
EXIT_PERFORMANCE_NOT_QUALIFIED = 30

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DEPTHS = ("shallow", "8k", "32k", "47.7k")
VARIANTS = ("off", "on")
RESULT_FIELDS = {
    "schema_version",
    "profile_id",
    "campaign_id",
    "case_id",
    "gate",
    "status",
    "checks",
    "metrics",
    "performance",
}
COMPARISON_FIELDS = {
    "backend",
    "host_fingerprint",
    "model_sha256",
    "draft_sha256",
    "projector_sha256",
    "context_tokens",
    "slots",
    "kv_type",
    "batch_size",
    "microbatch_size",
    "mtp_mode",
    "mtp_draft_max",
    "mtp_probability_threshold",
    "sampling_sha256",
    "prompt_sha256",
    "power_state",
    "server_environment_sha256",
}
RUNTIME_IDENTITY_FIELDS = {
    "source_commit",
    "patchset_sha256",
    "binary_sha256",
    "backend_library_sha256",
    "launch_sha256",
    "feature_state",
}
PERFORMANCE_METRICS = {
    "prompt_tokens",
    "prompt_tokens_per_second",
    "generated_tokens",
    "generated_tokens_per_second",
    "time_to_first_token_ms",
    "inter_token_latency_ms.p50",
    "inter_token_latency_ms.p95",
    "inter_token_latency_ms.max",
    "mtp.accepted_tokens",
    "mtp.drafted_tokens",
    "prompt.reused_tokens",
    "prompt.new_tokens",
    "gpu.utilization_percent",
    "gpu.clock_mhz",
    "memory.gtt_bytes",
    "memory.mem_available_bytes",
    "memory.swap_bytes",
    "server.warning_count",
    "server.fallback_count",
}
STATIC_METRIC_KINDS = {
    "backend_library.sha256": "sha256",
    "binary.sha256": "sha256",
    "compile.command_sha256": "sha256",
    "expected_runtime.sha256": "sha256",
    "gpu.reset_count": "nonnegative_integer",
    "launch.sha256": "sha256",
    "memory.growth_bytes": "nonnegative_integer",
    "memory.gtt_bytes": "nonnegative_integer",
    "memory.mem_available_bytes": "nonnegative_integer",
    "memory.owners_snapshot_sha256": "sha256",
    "memory.swap_bytes": "nonnegative_integer",
    "mtp.accepted_tokens": "nonnegative_integer",
    "mtp.drafted_tokens": "nonnegative_integer",
    "ports.snapshot_sha256": "sha256",
    "processes.snapshot_sha256": "sha256",
    "projector.sha256": "sha256",
    "server.crash_count": "nonnegative_integer",
    "server.fallback_count": "nonnegative_integer",
    "server.warning_count": "nonnegative_integer",
    "source.commit": "commit",
    "source.patchset_sha256": "sha256",
}


class EvidenceError(ValueError):
    """An input is malformed, incomplete, or ambiguous."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise EvidenceError(f"non-finite JSON number: {value}")


def load_json(path: Path) -> Any:
    """Load strict JSON. Reject duplicate keys and non-finite numbers."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceError(f"cannot read {path}: {exc}") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except EvidenceError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid JSON in {path}: {exc}") from exc


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be an object")
    return value


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise EvidenceError(f"{label} must be a lowercase SHA-256")
    return value


def _metric(metrics: dict[str, Any], dotted_name: str) -> Any:
    value: Any = metrics
    for part in dotted_name.split("."):
        if not isinstance(value, dict) or part not in value:
            raise EvidenceError(f"missing metric: {dotted_name}")
        value = value[part]
    if value is None:
        raise EvidenceError(f"null metric: {dotted_name}")
    return value


def _validate_json_values(value: Any, label: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if _is_number(value):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_values(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _require_nonempty_string(key, f"{label} key")
            _validate_json_values(item, f"{label}.{key}")
        return
    raise EvidenceError(f"{label} contains an unsupported value")


def validate_matrix(matrix: Any) -> dict[str, Any]:
    matrix = _require_object(matrix, "matrix")
    if matrix.get("schema_version") != 1:
        raise EvidenceError("matrix.schema_version must be 1")
    _require_nonempty_string(matrix.get("profile_id"), "matrix.profile_id")
    cases = matrix.get("static_cases")
    if not isinstance(cases, list) or not cases:
        raise EvidenceError("matrix.static_cases must be a non-empty array")
    seen: set[str] = set()
    for index, case in enumerate(cases):
        case = _require_object(case, f"matrix.static_cases[{index}]")
        case_id = _require_nonempty_string(case.get("case_id"), f"static case {index} case_id")
        if case_id in seen:
            raise EvidenceError(f"duplicate matrix case_id: {case_id}")
        seen.add(case_id)
        gate = _require_nonempty_string(case.get("gate"), f"matrix case {case_id} gate")
        if gate not in {"admission", "A", "B", "C", "D", "E", "G", "H"}:
            raise EvidenceError(f"matrix case {case_id} has invalid gate: {gate}")
        checks = case.get("required_checks")
        if not isinstance(checks, list) or not checks or len(checks) != len(set(checks)):
            raise EvidenceError(f"matrix case {case_id} has invalid required_checks")
        for check in checks:
            _require_nonempty_string(check, f"matrix case {case_id} check")
        metrics = case.get("required_metrics", [])
        if not isinstance(metrics, list) or len(metrics) != len(set(metrics)):
            raise EvidenceError(f"matrix case {case_id} has invalid required_metrics")
        for metric in metrics:
            _require_nonempty_string(metric, f"matrix case {case_id} metric")
            if metric not in STATIC_METRIC_KINDS:
                raise EvidenceError(f"matrix case {case_id} metric {metric} has no static metric rule")
        condition = case.get("condition")
        if condition is not None and condition != "qsa_cache_enabled":
            raise EvidenceError(f"matrix case {case_id} has unsupported condition")
    performance = _require_object(matrix.get("performance"), "matrix.performance")
    if performance.get("depths") != list(DEPTHS):
        raise EvidenceError("matrix.performance.depths must use the fixed depth names")
    minimum_pairs = performance.get("minimum_usable_pairs_per_depth")
    if not isinstance(minimum_pairs, int) or isinstance(minimum_pairs, bool) or minimum_pairs < 3:
        raise EvidenceError("minimum usable pairs must be at least 3")
    if set(performance.get("required_metrics", [])) != PERFORMANCE_METRICS:
        raise EvidenceError("matrix.performance.required_metrics is not the fixed metric set")
    return matrix


def validate_campaign(campaign: Any, matrix: dict[str, Any]) -> dict[str, Any]:
    campaign = _require_object(campaign, "campaign")
    allowed = {
        "schema_version",
        "profile_id",
        "campaign_id",
        "features",
        "observed_run_noise_percent",
    }
    unknown = set(campaign) - allowed
    if unknown:
        raise EvidenceError(f"unknown campaign fields: {sorted(unknown)}")
    if campaign.get("schema_version") != 1:
        raise EvidenceError("campaign.schema_version must be 1")
    if campaign.get("profile_id") != matrix["profile_id"]:
        raise EvidenceError("campaign profile_id does not match the matrix")
    _require_nonempty_string(campaign.get("campaign_id"), "campaign.campaign_id")
    features = _require_object(campaign.get("features"), "campaign.features")
    if set(features) != {"qsa_cache"} or not isinstance(features["qsa_cache"], bool):
        raise EvidenceError("campaign.features must contain one qsa_cache boolean")
    noise = _require_object(campaign.get("observed_run_noise_percent"), "campaign noise")
    if set(noise) != {"prompt_tokens_per_second", "generated_tokens_per_second"}:
        raise EvidenceError("campaign noise must contain both throughput metrics")
    for name, value in noise.items():
        if not _is_number(value) or value < 0 or value >= 100:
            raise EvidenceError(f"campaign noise {name} must be in [0, 100)")
    return campaign


def _validate_checks(
    checks: Any,
    required: Iterable[str],
    status: str,
    case_id: str,
) -> dict[str, bool]:
    checks = _require_object(checks, f"result {case_id} checks")
    required_set = set(required)
    missing = required_set - set(checks)
    if missing:
        raise EvidenceError(f"result {case_id} missing checks: {sorted(missing)}")
    if not checks:
        raise EvidenceError(f"result {case_id} checks cannot be empty")
    for check_id, passed in checks.items():
        _require_nonempty_string(check_id, f"result {case_id} check id")
        if not isinstance(passed, bool):
            raise EvidenceError(f"result {case_id} check {check_id} must be boolean")
    all_pass = all(checks.values())
    if status == "pass" and not all_pass:
        raise EvidenceError(f"result {case_id} claims pass with a failed check")
    if status == "fail" and all_pass:
        raise EvidenceError(f"result {case_id} claims fail without a failed check")
    return checks


def _validate_metrics(metrics: Any, required: Iterable[str], case_id: str) -> dict[str, Any]:
    metrics = _require_object(metrics, f"result {case_id} metrics")
    _validate_json_values(metrics, f"result {case_id} metrics")
    for name in required:
        _metric(metrics, name)
    return metrics


def _validate_static_metrics(
    metrics: dict[str, Any],
    required: Iterable[str],
    case_id: str,
) -> None:
    for name in required:
        value = _metric(metrics, name)
        kind = STATIC_METRIC_KINDS.get(name)
        if kind == "sha256":
            _require_sha256(value, f"result {case_id} metric {name}")
        elif kind == "commit":
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{7,64}", value):
                raise EvidenceError(f"result {case_id} metric {name} must be lowercase hexadecimal")
        elif kind == "nonnegative_integer":
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise EvidenceError(f"result {case_id} metric {name} must be a non-negative integer")
        else:
            raise EvidenceError(f"result {case_id} metric {name} has no static metric rule")


def _validate_static_metric_semantics(
    metrics: dict[str, Any],
    case_id: str,
    status: str,
) -> None:
    if case_id.startswith("d_"):
        accepted = _metric(metrics, "mtp.accepted_tokens")
        drafted = _metric(metrics, "mtp.drafted_tokens")
        for name, value in (("mtp.accepted_tokens", accepted), ("mtp.drafted_tokens", drafted)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise EvidenceError(f"result {case_id} metric {name} must be a non-negative integer")
        if accepted > drafted:
            raise EvidenceError(f"result {case_id} accepted more MTP tokens than drafted")
    if status != "pass":
        return
    zero_metrics: dict[str, tuple[str, ...]] = {
        "a_build_and_feature_off": ("server.fallback_count",),
        "g_server_log_review": ("server.fallback_count",),
        "h_stability_and_rollback": (
            "memory.swap_bytes",
            "server.crash_count",
            "gpu.reset_count",
        ),
    }
    for name in zero_metrics.get(case_id, ()):
        value = _metric(metrics, name)
        if not _is_number(value) or value != 0:
            raise EvidenceError(f"passing result {case_id} requires zero metric {name}")


def _validate_comparison(comparison: Any, case_id: str) -> dict[str, Any]:
    comparison = _require_object(comparison, f"result {case_id} comparison")
    if set(comparison) != COMPARISON_FIELDS:
        missing = sorted(COMPARISON_FIELDS - set(comparison))
        extra = sorted(set(comparison) - COMPARISON_FIELDS)
        raise EvidenceError(f"result {case_id} comparison fields differ; missing={missing}, extra={extra}")
    _require_nonempty_string(comparison["backend"], f"result {case_id} comparison.backend")
    for field in (
        "host_fingerprint",
        "model_sha256",
        "draft_sha256",
        "sampling_sha256",
        "prompt_sha256",
        "server_environment_sha256",
    ):
        _require_sha256(comparison[field], f"result {case_id} comparison.{field}")
    projector = comparison["projector_sha256"]
    if projector != "disabled":
        _require_sha256(projector, f"result {case_id} comparison.projector_sha256")
    for field in ("context_tokens", "slots", "batch_size", "microbatch_size", "mtp_draft_max"):
        value = comparison[field]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise EvidenceError(f"result {case_id} comparison.{field} must be a positive integer")
    if comparison["context_tokens"] != 65536 or comparison["slots"] != 1:
        raise EvidenceError(f"result {case_id} changed fixed context or slot count")
    if comparison["batch_size"] != 8192 or comparison["microbatch_size"] != 2048:
        raise EvidenceError(f"result {case_id} changed fixed batch settings")
    if comparison["kv_type"] != "q8_0":
        raise EvidenceError(f"result {case_id} changed fixed K/V type")
    if comparison["mtp_mode"] != "draft-mtp,ngram-mod" or comparison["mtp_draft_max"] != 4:
        raise EvidenceError(f"result {case_id} changed fixed MTP settings")
    threshold = comparison["mtp_probability_threshold"]
    if not _is_number(threshold) or threshold != 0.75:
        raise EvidenceError(f"result {case_id} changed fixed MTP threshold")
    _require_nonempty_string(comparison["power_state"], f"result {case_id} power_state")
    return comparison


def _validate_runtime_identity(identity: Any, case_id: str, variant: str) -> dict[str, Any]:
    identity = _require_object(identity, f"result {case_id} runtime_identity")
    if set(identity) != RUNTIME_IDENTITY_FIELDS:
        missing = sorted(RUNTIME_IDENTITY_FIELDS - set(identity))
        extra = sorted(set(identity) - RUNTIME_IDENTITY_FIELDS)
        raise EvidenceError(f"result {case_id} runtime identity fields differ; missing={missing}, extra={extra}")
    commit = _require_nonempty_string(identity["source_commit"], f"result {case_id} source_commit")
    if not re.fullmatch(r"[0-9a-f]{7,64}", commit):
        raise EvidenceError(f"result {case_id} source_commit must be lowercase hexadecimal")
    for field in ("patchset_sha256", "binary_sha256", "backend_library_sha256", "launch_sha256"):
        _require_sha256(identity[field], f"result {case_id} runtime_identity.{field}")
    if identity["feature_state"] != variant:
        raise EvidenceError(f"result {case_id} runtime feature_state does not match its variant")
    return identity


def _validate_performance_metrics(metrics: dict[str, Any], case_id: str) -> None:
    positive = (
        "prompt_tokens",
        "prompt_tokens_per_second",
        "generated_tokens",
        "generated_tokens_per_second",
    )
    nonnegative = PERFORMANCE_METRICS - set(positive)
    for name in positive:
        value = _metric(metrics, name)
        if not _is_number(value) or value <= 0:
            raise EvidenceError(f"result {case_id} metric {name} must be positive")
    for name in nonnegative:
        value = _metric(metrics, name)
        if not _is_number(value) or value < 0:
            raise EvidenceError(f"result {case_id} metric {name} must be non-negative")
    integer_metrics = (
        "prompt_tokens",
        "generated_tokens",
        "mtp.accepted_tokens",
        "mtp.drafted_tokens",
        "prompt.reused_tokens",
        "prompt.new_tokens",
        "memory.gtt_bytes",
        "memory.mem_available_bytes",
        "memory.swap_bytes",
        "server.warning_count",
        "server.fallback_count",
    )
    for name in integer_metrics:
        value = _metric(metrics, name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise EvidenceError(f"result {case_id} metric {name} must be an integer")
    if _metric(metrics, "mtp.accepted_tokens") > _metric(metrics, "mtp.drafted_tokens"):
        raise EvidenceError(f"result {case_id} accepted more MTP tokens than drafted")
    prompt_parts = _metric(metrics, "prompt.reused_tokens") + _metric(metrics, "prompt.new_tokens")
    if prompt_parts != _metric(metrics, "prompt_tokens"):
        raise EvidenceError(f"result {case_id} reused and new prompt tokens do not sum to prompt tokens")
    utilization = _metric(metrics, "gpu.utilization_percent")
    if utilization > 100:
        raise EvidenceError(f"result {case_id} GPU utilization exceeds 100 percent")
    p50 = _metric(metrics, "inter_token_latency_ms.p50")
    p95 = _metric(metrics, "inter_token_latency_ms.p95")
    maximum = _metric(metrics, "inter_token_latency_ms.max")
    if not p50 <= p95 <= maximum:
        raise EvidenceError(f"result {case_id} latency summary is not ordered")


def validate_result(
    result: Any,
    matrix: dict[str, Any],
    campaign: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = _require_object(result, "result")
    unknown = set(result) - RESULT_FIELDS
    if unknown:
        raise EvidenceError(f"unknown result fields: {sorted(unknown)}")
    required_top = RESULT_FIELDS - {"performance"}
    missing_top = required_top - set(result)
    if missing_top:
        raise EvidenceError(f"missing result fields: {sorted(missing_top)}")
    if result.get("schema_version") != 1:
        raise EvidenceError("result.schema_version must be 1")
    if result.get("profile_id") != matrix["profile_id"]:
        raise EvidenceError("result profile_id does not match the matrix")
    if campaign is not None and result.get("campaign_id") != campaign["campaign_id"]:
        raise EvidenceError("result campaign_id does not match the campaign")
    _require_nonempty_string(result.get("campaign_id"), "result.campaign_id")
    case_id = _require_nonempty_string(result.get("case_id"), "result.case_id")
    status = result.get("status")
    if status not in {"pass", "fail"}:
        raise EvidenceError(f"result {case_id} status must be pass or fail")
    gate = result.get("gate")
    static_by_id = {case["case_id"]: case for case in matrix["static_cases"]}
    if gate == "F":
        performance_rule = matrix["performance"]
        required_checks = performance_rule["required_checks"]
        required_metrics = performance_rule["required_metrics"]
    else:
        if case_id not in static_by_id:
            raise EvidenceError(f"unknown static case_id: {case_id}")
        case = static_by_id[case_id]
        if gate != case["gate"]:
            raise EvidenceError(f"result {case_id} gate does not match the matrix")
        required_checks = case["required_checks"]
        required_metrics = case.get("required_metrics", [])
    _validate_checks(result["checks"], required_checks, status, case_id)
    metrics = _validate_metrics(result["metrics"], required_metrics, case_id)
    if gate == "F":
        performance = _require_object(result.get("performance"), f"result {case_id} performance")
        if set(performance) != {"pair_id", "variant", "depth", "sequence", "comparison", "runtime_identity"}:
            raise EvidenceError(f"result {case_id} has invalid performance fields")
        _require_nonempty_string(performance["pair_id"], f"result {case_id} pair_id")
        if performance["variant"] not in VARIANTS:
            raise EvidenceError(f"result {case_id} has invalid performance variant")
        if performance["depth"] not in DEPTHS:
            raise EvidenceError(f"result {case_id} has invalid performance depth")
        sequence = performance["sequence"]
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise EvidenceError(f"result {case_id} sequence must be a positive integer")
        _validate_comparison(performance["comparison"], case_id)
        _validate_runtime_identity(performance["runtime_identity"], case_id, performance["variant"])
        _validate_performance_metrics(metrics, case_id)
        if status == "pass":
            for name in ("memory.swap_bytes", "server.warning_count", "server.fallback_count"):
                if _metric(metrics, name) != 0:
                    raise EvidenceError(f"passing result {case_id} requires zero metric {name}")
    elif "performance" in result and result["performance"] is not None:
        raise EvidenceError(f"static result {case_id} cannot contain performance data")
    else:
        _validate_static_metrics(metrics, required_metrics, case_id)
        _validate_static_metric_semantics(metrics, case_id, status)
    return result


def _required_static_cases(matrix: dict[str, Any], campaign: dict[str, Any]) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    for case in matrix["static_cases"]:
        if case.get("condition") == "qsa_cache_enabled" and not campaign["features"]["qsa_cache"]:
            continue
        required.append(case)
    return required


def _percent_change(off_value: float, on_value: float) -> float:
    return ((on_value - off_value) / off_value) * 100.0


def evaluate(
    matrix: dict[str, Any],
    campaign: dict[str, Any],
    results: list[dict[str, Any]],
) -> tuple[int, dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    by_case: dict[str, dict[str, Any]] = {}
    for result in results:
        case_id = result["case_id"]
        if case_id in by_case:
            errors.append(f"duplicate result case_id: {case_id}")
        else:
            by_case[case_id] = result
    required_static = _required_static_cases(matrix, campaign)
    required_ids = {case["case_id"] for case in required_static}
    missing = sorted(required_ids - set(by_case))
    if missing:
        errors.append(f"missing required results: {missing}")
    disabled_qsa_ids = {
        case["case_id"]
        for case in matrix["static_cases"]
        if case.get("condition") == "qsa_cache_enabled"
    }
    if not campaign["features"]["qsa_cache"]:
        unexpected = sorted(disabled_qsa_ids & set(by_case))
        if unexpected:
            errors.append(f"QSA results supplied while QSA is disabled: {unexpected}")
    static_ids = {case["case_id"] for case in matrix["static_cases"]}
    performance_results = [result for result in results if result["gate"] == "F"]
    unknown_nonperformance = sorted(
        result["case_id"] for result in results if result["gate"] != "F" and result["case_id"] not in static_ids
    )
    if unknown_nonperformance:
        errors.append(f"unknown non-performance results: {unknown_nonperformance}")
    failed_results = sorted(result["case_id"] for result in results if result["status"] == "fail")

    pairs: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    seen_sequences: set[int] = set()
    for result in performance_results:
        performance = result["performance"]
        sequence = performance["sequence"]
        if sequence in seen_sequences:
            errors.append(f"duplicate performance sequence: {sequence}")
        seen_sequences.add(sequence)
        key = (performance["depth"], performance["pair_id"])
        variants = pairs.setdefault(key, {})
        variant = performance["variant"]
        if variant in variants:
            errors.append(f"duplicate {variant} result for pair {key}")
        variants[variant] = result

    pair_changes: dict[str, dict[str, list[float]]] = {
        depth: {
            "prompt_tokens_per_second": [],
            "generated_tokens_per_second": [],
        }
        for depth in DEPTHS
    }
    complete_pair_counts = {depth: 0 for depth in DEPTHS}
    usable_pair_counts = {depth: 0 for depth in DEPTHS}
    for (depth, pair_id), variants in sorted(pairs.items()):
        if set(variants) != set(VARIANTS):
            errors.append(f"pair {depth}/{pair_id} must contain one OFF and one ON result")
            continue
        off = variants["off"]
        on = variants["on"]
        if off["performance"]["comparison"] != on["performance"]["comparison"]:
            errors.append(f"pair {depth}/{pair_id} comparison fingerprints do not match")
            continue
        complete_pair_counts[depth] += 1
        if off["status"] != "pass" or on["status"] != "pass":
            continue
        usable_pair_counts[depth] += 1
        for metric in ("prompt_tokens_per_second", "generated_tokens_per_second"):
            pair_changes[depth][metric].append(
                _percent_change(float(_metric(off["metrics"], metric)), float(_metric(on["metrics"], metric)))
            )
    minimum_pairs = matrix["performance"]["minimum_usable_pairs_per_depth"]
    for depth, complete_count in complete_pair_counts.items():
        usable_count = usable_pair_counts[depth]
        if complete_count < minimum_pairs:
            errors.append(f"depth {depth} has {complete_count} complete pairs; {minimum_pairs} required")
        elif usable_count < minimum_pairs and not failed_results:
            errors.append(f"depth {depth} has {usable_count} usable pairs; {minimum_pairs} required")

    performance_summary: dict[str, Any] = {
        "complete_pair_counts": complete_pair_counts,
        "usable_pair_counts": usable_pair_counts,
        "median_change_percent": {},
        "decision_depth": matrix["performance"]["decision_depth"],
        "outside_noise": {},
        "regressions_beyond_noise": [],
        "targets": {},
    }
    performance_qualified = False
    if not errors and all(count >= minimum_pairs for count in usable_pair_counts.values()):
        for depth in DEPTHS:
            medians: dict[str, float] = {}
            for metric, values in pair_changes[depth].items():
                medians[metric] = median(values)
                noise = campaign["observed_run_noise_percent"][metric]
                if medians[metric] < -noise:
                    performance_summary["regressions_beyond_noise"].append(
                        {"depth": depth, "metric": metric, "change_percent": medians[metric], "noise_percent": noise}
                    )
            performance_summary["median_change_percent"][depth] = medians
        decision_depth = matrix["performance"]["decision_depth"]
        outside_noise: dict[str, bool] = {}
        for metric in ("prompt_tokens_per_second", "generated_tokens_per_second"):
            change = performance_summary["median_change_percent"][decision_depth][metric]
            noise = campaign["observed_run_noise_percent"][metric]
            outside_noise[metric] = change > noise
        performance_summary["outside_noise"] = outside_noise
        on_at_depth = [
            result for result in performance_results
            if result["performance"]["depth"] == decision_depth
            and result["performance"]["variant"] == "on"
            and result["status"] == "pass"
        ]
        for metric, target in matrix["performance"]["targets"].items():
            observed = median(float(_metric(result["metrics"], metric)) for result in on_at_depth)
            performance_summary["targets"][metric] = {
                "target": target,
                "observed_median": observed,
                "met": observed >= target,
            }
        if not all(item["met"] for item in performance_summary["targets"].values()):
            warnings.append("one or more project performance targets were not met")
        performance_qualified = (
            any(outside_noise.values())
            and not performance_summary["regressions_beyond_noise"]
        )

    if errors:
        decision = "invalid_evidence"
        exit_code = EXIT_INVALID_EVIDENCE
    elif failed_results:
        decision = "correctness_failed"
        exit_code = EXIT_CORRECTNESS_FAILED
    elif not performance_qualified:
        decision = "performance_not_qualified"
        exit_code = EXIT_PERFORMANCE_NOT_QUALIFIED
    else:
        decision = "qualified"
        exit_code = EXIT_QUALIFIED
    summary = {
        "schema_version": 1,
        "profile_id": matrix["profile_id"],
        "campaign_id": campaign["campaign_id"],
        "decision": decision,
        "exit_code": exit_code,
        "correctness": {
            "failed_result_ids": failed_results,
            "required_static_results": len(required_static),
            "qsa_cache_enabled": campaign["features"]["qsa_cache"],
        },
        "performance": performance_summary,
        "errors": errors,
        "warnings": warnings,
        "input_result_count": len(results),
    }
    return exit_code, summary


def _load_results(directory: Path, matrix: dict[str, Any], campaign: dict[str, Any]) -> list[dict[str, Any]]:
    if not directory.is_dir():
        raise EvidenceError(f"results directory does not exist: {directory}")
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise EvidenceError(f"results directory has no JSON files: {directory}")
    results: list[dict[str, Any]] = []
    for path in paths:
        try:
            result = validate_result(load_json(path), matrix, campaign)
        except EvidenceError as exc:
            raise EvidenceError(f"{path.name}: {exc}") from exc
        results.append(result)
    return results


def _input_receipt(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        digest.update(str(path.name).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def command_validate_result(args: argparse.Namespace) -> int:
    matrix = validate_matrix(load_json(args.matrix))
    campaign = validate_campaign(load_json(args.campaign), matrix) if args.campaign else None
    result = validate_result(load_json(args.result), matrix, campaign)
    output = {
        "schema_version": 1,
        "valid": True,
        "case_id": result["case_id"],
        "status": result["status"],
        "exit_code": EXIT_QUALIFIED if result["status"] == "pass" else EXIT_CORRECTNESS_FAILED,
    }
    print(json.dumps(output, sort_keys=True, allow_nan=False))
    return output["exit_code"]


def command_evaluate(args: argparse.Namespace) -> int:
    output_path = args.output
    try:
        matrix = validate_matrix(load_json(args.matrix))
        campaign = validate_campaign(load_json(args.campaign), matrix)
        result_paths = sorted(args.results_dir.glob("*.json")) if args.results_dir.is_dir() else []
        results = _load_results(args.results_dir, matrix, campaign)
        exit_code, summary = evaluate(matrix, campaign, results)
        summary["input_receipt_sha256"] = _input_receipt([args.matrix, args.campaign, *result_paths])
    except EvidenceError as exc:
        exit_code = EXIT_INVALID_EVIDENCE
        summary = {
            "schema_version": 1,
            "decision": "invalid_evidence",
            "exit_code": exit_code,
            "errors": [str(exc)],
            "warnings": [],
        }
    atomic_write_json(output_path, summary)
    print(json.dumps({"decision": summary["decision"], "exit_code": exit_code, "output": str(output_path)}, sort_keys=True))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate-result", help="validate one result file")
    validate_parser.add_argument("--matrix", type=Path, required=True)
    validate_parser.add_argument("--campaign", type=Path)
    validate_parser.add_argument("result", type=Path)
    validate_parser.set_defaults(function=command_validate_result)
    evaluate_parser = subparsers.add_parser("evaluate", help="evaluate one complete campaign")
    evaluate_parser.add_argument("--matrix", type=Path, required=True)
    evaluate_parser.add_argument("--campaign", type=Path, required=True)
    evaluate_parser.add_argument("--results-dir", type=Path, required=True)
    evaluate_parser.add_argument("--output", type=Path, required=True)
    evaluate_parser.set_defaults(function=command_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.function(args)
    except EvidenceError as exc:
        print(json.dumps({"decision": "invalid_evidence", "exit_code": EXIT_INVALID_EVIDENCE, "errors": [str(exc)]}, sort_keys=True))
        return EXIT_INVALID_EVIDENCE
    except OSError as exc:
        print(json.dumps({"decision": "invalid_evidence", "exit_code": EXIT_INVALID_EVIDENCE, "errors": [str(exc)]}, sort_keys=True))
        return EXIT_INVALID_EVIDENCE


if __name__ == "__main__":
    sys.exit(main())
