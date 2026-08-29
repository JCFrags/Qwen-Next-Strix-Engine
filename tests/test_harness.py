from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "harness" / "qwen38_harness.py"
MATRIX_PATH = ROOT / "harness" / "qwen38_matrix.json"
FIXTURES = ROOT / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("qwen38_harness", MODULE_PATH)
harness = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(harness)


def put_metric(target: dict, dotted_name: str, value: object) -> None:
    parts = dotted_name.split(".")
    current = target
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def campaign(qsa_cache: bool = False) -> dict:
    return {
        "schema_version": 1,
        "profile_id": "qwen38-flash-next-strix-v1",
        "campaign_id": "offline-test",
        "features": {"qsa_cache": qsa_cache},
        "observed_run_noise_percent": {
            "prompt_tokens_per_second": 2.0,
            "generated_tokens_per_second": 2.0,
        },
    }


def static_result(case: dict) -> dict:
    metrics: dict = {}
    for name in case.get("required_metrics", []):
        value: object = 0
        if name.endswith("sha256"):
            value = "a" * 64
        elif name == "source.commit":
            value = "abcdef1"
        elif name == "mtp.drafted_tokens":
            value = 8
        elif name == "mtp.accepted_tokens":
            value = 4
        put_metric(metrics, name, value)
    return {
        "schema_version": 1,
        "profile_id": "qwen38-flash-next-strix-v1",
        "campaign_id": "offline-test",
        "case_id": case["case_id"],
        "gate": case["gate"],
        "status": "pass",
        "checks": {name: True for name in case["required_checks"]},
        "metrics": metrics,
    }


def comparison(depth: str, pair_number: int) -> dict:
    prompt_seed = f"{depth}-{pair_number}".encode()
    prompt_hash = __import__("hashlib").sha256(prompt_seed).hexdigest()
    fixed_hash = "1" * 64
    return {
        "backend": "offline-backend",
        "host_fingerprint": "2" * 64,
        "model_sha256": fixed_hash,
        "draft_sha256": "3" * 64,
        "projector_sha256": "disabled",
        "context_tokens": 65536,
        "slots": 1,
        "kv_type": "q8_0",
        "batch_size": 8192,
        "microbatch_size": 2048,
        "mtp_mode": "draft-mtp,ngram-mod",
        "mtp_draft_max": 4,
        "mtp_probability_threshold": 0.75,
        "sampling_sha256": "4" * 64,
        "prompt_sha256": prompt_hash,
        "power_state": "fixed-test-state",
        "server_environment_sha256": "5" * 64,
    }


def performance_result(depth: str, pair_number: int, variant: str, sequence: int) -> dict:
    is_on = variant == "on"
    prompt_tps = 363.0 if is_on else 330.0
    generation_tps = 28.6 if is_on else 26.0
    metrics = {
        "prompt_tokens": 1000,
        "prompt_tokens_per_second": prompt_tps,
        "generated_tokens": 100,
        "generated_tokens_per_second": generation_tps,
        "time_to_first_token_ms": 25.0,
        "inter_token_latency_ms": {"p50": 10.0, "p95": 15.0, "max": 20.0},
        "mtp": {"accepted_tokens": 60, "drafted_tokens": 80},
        "prompt": {"reused_tokens": 400, "new_tokens": 600},
        "gpu": {"utilization_percent": 90.0, "clock_mhz": 2800.0},
        "memory": {"gtt_bytes": 1000, "mem_available_bytes": 2000, "swap_bytes": 0},
        "server": {"warning_count": 0, "fallback_count": 0},
    }
    return {
        "schema_version": 1,
        "profile_id": "qwen38-flash-next-strix-v1",
        "campaign_id": "offline-test",
        "case_id": f"f_{depth}_{pair_number}_{variant}",
        "gate": "F",
        "status": "pass",
        "checks": {
            "request_completed": True,
            "output_matches_correctness_reference": True,
            "no_unexpected_warning_or_fallback": True,
        },
        "metrics": metrics,
        "performance": {
            "pair_id": f"pair-{pair_number}",
            "variant": variant,
            "depth": depth,
            "sequence": sequence,
            "comparison": comparison(depth, pair_number),
            "runtime_identity": {
                "source_commit": "abcdef1",
                "patchset_sha256": "6" * 64,
                "binary_sha256": "7" * 64,
                "backend_library_sha256": "8" * 64,
                "launch_sha256": "9" * 64,
                "feature_state": variant,
            },
        },
    }


def complete_results(matrix: dict, qsa_cache: bool = False) -> list[dict]:
    results = [
        static_result(case)
        for case in matrix["static_cases"]
        if qsa_cache or case.get("condition") != "qsa_cache_enabled"
    ]
    sequence = 1
    for depth in harness.DEPTHS:
        for pair_number in range(1, 4):
            for variant in harness.VARIANTS:
                results.append(performance_result(depth, pair_number, variant, sequence))
                sequence += 1
    return results


class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = harness.validate_matrix(harness.load_json(MATRIX_PATH))
        cls.campaign = harness.validate_campaign(campaign(), cls.matrix)

    def test_valid_fixture_parses_and_validates(self) -> None:
        result = harness.validate_result(
            harness.load_json(FIXTURES / "valid_admission.json"),
            self.matrix,
            self.campaign,
        )
        self.assertEqual(result["status"], "pass")

    def assert_invalid_admission_metric_exit(self, name: str, value: object) -> None:
        result = harness.load_json(FIXTURES / "valid_admission.json")
        put_metric(result["metrics"], name, value)
        with tempfile.TemporaryDirectory() as temporary:
            result_path = Path(temporary) / "result.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "validate-result",
                    "--matrix",
                    str(MATRIX_PATH),
                    str(result_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, harness.EXIT_INVALID_EVIDENCE)
        self.assertEqual(json.loads(completed.stdout)["decision"], "invalid_evidence")

    def test_required_admission_memory_rejects_nonnumeric_values(self) -> None:
        for name in (
            "memory.mem_available_bytes",
            "memory.swap_bytes",
            "memory.gtt_bytes",
        ):
            with self.subTest(metric=name):
                self.assert_invalid_admission_metric_exit(name, "unknown")

    def test_required_admission_memory_rejects_negative_values(self) -> None:
        for name in (
            "memory.mem_available_bytes",
            "memory.swap_bytes",
            "memory.gtt_bytes",
        ):
            with self.subTest(metric=name):
                self.assert_invalid_admission_metric_exit(name, -1)

    def test_every_required_static_metric_has_an_exact_rule(self) -> None:
        required = {
            name
            for case in self.matrix["static_cases"]
            for name in case.get("required_metrics", [])
        }
        self.assertEqual(required, set(harness.STATIC_METRIC_KINDS))

    def test_duplicate_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(harness.EvidenceError, "duplicate JSON key"):
            harness.load_json(FIXTURES / "duplicate_keys.json")

    def test_nonfinite_number_is_rejected(self) -> None:
        with self.assertRaisesRegex(harness.EvidenceError, "non-finite JSON number"):
            harness.load_json(FIXTURES / "nonfinite.json")

    def test_ambiguous_pass_is_rejected(self) -> None:
        with self.assertRaisesRegex(harness.EvidenceError, "claims pass"):
            harness.validate_result(
                harness.load_json(FIXTURES / "ambiguous_pass.json"),
                self.matrix,
                self.campaign,
            )

    def test_missing_metric_is_rejected(self) -> None:
        with self.assertRaisesRegex(harness.EvidenceError, "missing metric"):
            harness.validate_result(
                harness.load_json(FIXTURES / "missing_metric.json"),
                self.matrix,
                self.campaign,
            )


class EvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = harness.validate_matrix(harness.load_json(MATRIX_PATH))

    def validated_results(self, qsa_cache: bool = False) -> tuple[dict, list[dict]]:
        campaign_value = harness.validate_campaign(campaign(qsa_cache), self.matrix)
        results = [
            harness.validate_result(result, self.matrix, campaign_value)
            for result in complete_results(self.matrix, qsa_cache)
        ]
        return campaign_value, results

    def test_complete_campaign_qualifies(self) -> None:
        campaign_value, results = self.validated_results()
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_QUALIFIED)
        self.assertEqual(summary["decision"], "qualified")
        self.assertTrue(all(item["met"] for item in summary["performance"]["targets"].values()))

    def test_qsa_cases_are_required_only_when_enabled(self) -> None:
        campaign_value, results = self.validated_results(qsa_cache=True)
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_QUALIFIED)
        self.assertTrue(summary["correctness"]["qsa_cache_enabled"])

    def test_correctness_failure_overrides_speed(self) -> None:
        campaign_value, results = self.validated_results()
        failed = results[0]
        failed["status"] = "fail"
        first_check = next(iter(failed["checks"]))
        failed["checks"][first_check] = False
        harness.validate_result(failed, self.matrix, campaign_value)
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_CORRECTNESS_FAILED)
        self.assertEqual(summary["decision"], "correctness_failed")

    def test_missing_required_case_is_invalid(self) -> None:
        campaign_value, results = self.validated_results()
        results = [result for result in results if result["case_id"] != "c_47_7k_a_b_a_slot_sequence"]
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_INVALID_EVIDENCE)
        self.assertIn("missing required results", summary["errors"][0])

    def test_pair_mismatch_is_invalid(self) -> None:
        campaign_value, results = self.validated_results()
        target = next(result for result in results if result["case_id"] == "f_47.7k_1_on")
        target["performance"]["comparison"]["prompt_sha256"] = "9" * 64
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_INVALID_EVIDENCE)
        self.assertTrue(any("fingerprints do not match" in error for error in summary["errors"]))

    def test_failed_performance_result_overrides_speed(self) -> None:
        campaign_value, results = self.validated_results()
        failed = next(result for result in results if result["case_id"] == "f_47.7k_1_on")
        failed["status"] = "fail"
        failed["checks"]["output_matches_correctness_reference"] = False
        harness.validate_result(failed, self.matrix, campaign_value)
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_CORRECTNESS_FAILED)
        self.assertEqual(summary["decision"], "correctness_failed")

    def test_passing_performance_result_rejects_warning_count(self) -> None:
        campaign_value, results = self.validated_results()
        result = next(item for item in results if item["gate"] == "F")
        result["metrics"]["server"]["warning_count"] = 1
        with self.assertRaisesRegex(harness.EvidenceError, "requires zero metric"):
            harness.validate_result(result, self.matrix, campaign_value)

    def test_inside_noise_does_not_qualify(self) -> None:
        campaign_value, results = self.validated_results()
        for result in results:
            if result["gate"] == "F" and result["performance"]["variant"] == "on":
                result["metrics"]["prompt_tokens_per_second"] = 333.0
                result["metrics"]["generated_tokens_per_second"] = 26.2
        exit_code, summary = harness.evaluate(self.matrix, campaign_value, results)
        self.assertEqual(exit_code, harness.EXIT_PERFORMANCE_NOT_QUALIFIED)
        self.assertEqual(summary["decision"], "performance_not_qualified")

    def test_cli_writes_invalid_summary_with_stable_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            campaign_path = temporary_path / "campaign.json"
            results_dir = temporary_path / "results"
            output_path = temporary_path / "summary.json"
            results_dir.mkdir()
            campaign_path.write_text(json.dumps(campaign()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "evaluate",
                    "--matrix",
                    str(MATRIX_PATH),
                    "--campaign",
                    str(campaign_path),
                    "--results-dir",
                    str(results_dir),
                    "--output",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, harness.EXIT_INVALID_EVIDENCE)
            summary = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["decision"], "invalid_evidence")


if __name__ == "__main__":
    unittest.main()
