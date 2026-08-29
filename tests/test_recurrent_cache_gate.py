from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "harness" / "recurrent_cache_gate.py"

spec = importlib.util.spec_from_file_location("recurrent_cache_gate", MODULE_PATH)
gate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gate)

MARKERS = ["ALPHA_OK", "BRAVO_OK", "ALPHA_OK", "DELTA_OK"]
PROMPTS = [f"shared private prompt {index}" for index in range(1, 5)]
PREFIX_LENGTH = gate.MIN_REQUIRED_CACHED_TOKENS
SHARED_PREFIX = list(range(PREFIX_LENGTH))
TOKEN_LISTS = [SHARED_PREFIX + [200 + index] for index in range(1, 5)]


def timings() -> dict[str, int | float]:
    return {
        "prompt_n": 1,
        "prompt_ms": 2.0,
        "prompt_per_token_ms": 2.0,
        "prompt_per_second": 0.5,
        "predicted_n": 2,
        "predicted_ms": 4.0,
        "predicted_per_token_ms": 2.0,
        "predicted_per_second": 0.5,
    }


def completion(index: int) -> dict[str, Any]:
    return {
        "content": f"<think>private reasoning {index}</think>\n{MARKERS[index]}",
        "id_slot": 0,
        "stop": True,
        "stop_type": "eos",
        "truncated": False,
        "tokens_cached": 0 if index == 0 else PREFIX_LENGTH,
        "tokens_evaluated": len(TOKEN_LISTS[index]),
        "tokens_predicted": 2,
        "timings": timings(),
    }


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.completions = [completion(index) for index in range(4)]
        self.token_lists = [list(tokens) for tokens in TOKEN_LISTS]
        self.malformed_tokenize_index: int | None = None
        self.fail_path: tuple[str, int] | None = None
        self.path_counts: dict[str, int] = {}

    def __call__(
        self, method: str, url: str, body: bytes | None, _timeout: float
    ) -> tuple[int, bytes]:
        path = urlsplit(url).path
        payload = json.loads(body) if body is not None else None
        self.calls.append((method, path, payload))
        occurrence = self.path_counts.get(path, 0)
        self.path_counts[path] = occurrence + 1
        if self.fail_path == (path, occurrence):
            return 503, b'{"private":"endpoint body"}'

        if path == "/health":
            response: Any = {"status": "ok"}
        elif path == "/apply-template":
            response = {"prompt": PROMPTS[occurrence]}
        elif path == "/tokenize":
            response = {"tokens": self.token_lists[occurrence]}
            if occurrence == self.malformed_tokenize_index:
                response = {"tokens": [101, "bad-token"]}
        elif path == "/completion":
            response = self.completions[occurrence]
        else:
            return 404, b"{}"
        return 200, json.dumps(response).encode()


class GateTests(unittest.TestCase):
    def make_inputs(self, root: Path) -> tuple[list[Path], Path, Path]:
        requests: list[Path] = []
        for index in range(4):
            request = {
                "messages": [
                    {"role": "system", "content": "private system text"},
                    {"role": "user", "content": f"private turn {index + 1}"},
                ],
                "chat_template_kwargs": {
                    "enable_thinking": True,
                    "private_option": index,
                },
                "max_tokens": 16,
                "temperature": 0,
                "seed": 7,
                "top_k": 1,
                "top_p": 1.0,
                "min_p": 0.0,
                "stream": True,
                "stop": ["<end>"],
            }
            path = root / f"request-{index + 1}.json"
            path.write_text(json.dumps(request), encoding="utf-8")
            requests.append(path)
        marker_path = root / "markers.json"
        marker_path.write_text(
            json.dumps({str(index + 1): marker for index, marker in enumerate(MARKERS)}),
            encoding="utf-8",
        )
        return requests, marker_path, root / "raw-output"

    def execute(
        self, fake: FakeTransport, minimum: int = PREFIX_LENGTH
    ) -> tuple[int, dict[str, Any], Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        requests, markers, output = self.make_inputs(root)
        exit_code, summary = gate.run_gate(
            requests,
            markers,
            "http://mock.invalid:8080",
            output,
            minimum,
            transport=fake,
        )
        return exit_code, summary, output

    def test_success_uses_exact_protocol_and_public_summary_is_private_free(self) -> None:
        fake = FakeTransport()
        exit_code, summary, output = self.execute(fake)

        self.assertEqual(exit_code, gate.EXIT_PASS)
        self.assertEqual(summary["decision"], "pass")
        self.assertEqual(
            [item["previous_common_prefix_tokens"] for item in summary["requests"]],
            [0, PREFIX_LENGTH, PREFIX_LENGTH, PREFIX_LENGTH],
        )
        self.assertEqual(
            [item["cached_tokens"] for item in summary["requests"]],
            [0, PREFIX_LENGTH, PREFIX_LENGTH, PREFIX_LENGTH]
        )
        self.assertTrue(all(len(item["prompt_sha256"]) == 64 for item in summary["requests"]))

        paths = [path for _method, path, _payload in fake.calls]
        self.assertEqual(paths[0], "/health")
        self.assertEqual(paths[-1], "/health")
        self.assertEqual(paths.count("/apply-template"), 4)
        self.assertEqual(paths.count("/tokenize"), 4)
        self.assertEqual(paths.count("/completion"), 4)

        first_template = next(payload for _, path, payload in fake.calls if path == "/apply-template")
        self.assertEqual(set(first_template), {"messages", "chat_template_kwargs"})
        first_tokenize = next(payload for _, path, payload in fake.calls if path == "/tokenize")
        self.assertEqual(
            first_tokenize,
            {"content": PROMPTS[0], "add_special": True, "parse_special": True},
        )
        first_completion = next(payload for _, path, payload in fake.calls if path == "/completion")
        self.assertEqual(first_completion["prompt"], PROMPTS[0])
        self.assertEqual(first_completion["n_predict"], 16)
        self.assertEqual(first_completion["temperature"], 0)
        self.assertEqual(first_completion["seed"], 7)
        self.assertEqual(first_completion["top_k"], 1)
        self.assertEqual(first_completion["top_p"], 1.0)
        self.assertEqual(first_completion["min_p"], 0.0)
        self.assertEqual(first_completion["stop"], ["<end>"])
        self.assertIs(first_completion["cache_prompt"], True)
        self.assertEqual(first_completion["id_slot"], 0)
        self.assertIs(first_completion["timings_per_token"], True)
        self.assertIs(first_completion["stream"], False)

        public_text = json.dumps(summary)
        for private_value in MARKERS + PROMPTS + ["private system text", "private reasoning"]:
            self.assertNotIn(private_value, public_text)
        self.assertEqual(
            json.loads((output / "public-summary.json").read_text(encoding="utf-8")),
            summary,
        )
        self.assertIn(MARKERS[0], (output / "01-completion.json").read_text(encoding="utf-8"))
        self.assertIn(PROMPTS[0], (output / "01-apply-template.json").read_text(encoding="utf-8"))

    def test_low_cache_reuse_fails(self) -> None:
        fake = FakeTransport()
        fake.completions[2]["tokens_cached"] = PREFIX_LENGTH - 1
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["cache_below_threshold"])
        self.assertTrue(summary["health"]["after"])

    def test_wrong_marker_fails(self) -> None:
        fake = FakeTransport()
        fake.completions[1]["content"] = "<think>hidden</think>NOT_CONFIGURED"
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["wrong_marker"])

    def test_extra_configured_marker_in_reasoning_fails(self) -> None:
        fake = FakeTransport()
        fake.completions[1]["content"] = (
            f"<think>{MARKERS[2]}</think>{MARKERS[1]}"
        )
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["unexpected_marker"])

    def test_common_prefix_below_threshold_fails(self) -> None:
        fake = FakeTransport()
        fake.token_lists[1][PREFIX_LENGTH - 1] = PREFIX_LENGTH + 999
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["common_prefix_below_threshold"])

    def test_cache_cannot_exceed_common_prefix(self) -> None:
        fake = FakeTransport()
        fake.completions[1]["tokens_cached"] = PREFIX_LENGTH + 1
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["cache_exceeds_common_prefix"])

    def test_malformed_endpoint_data_fails_closed(self) -> None:
        fake = FakeTransport()
        fake.completions[0]["timings"].pop("prompt_ms")
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["malformed_response"])

        fake = FakeTransport()
        fake.malformed_tokenize_index = 0
        exit_code, summary, _output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["malformed_response"])

    def test_truncation_fails(self) -> None:
        for field, value in (("truncated", True), ("stop_type", "limit")):
            with self.subTest(field=field):
                fake = FakeTransport()
                fake.completions[1][field] = value
                exit_code, summary, _output = self.execute(fake)
                self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
                self.assertEqual(summary["failures"], ["truncated"])

    def test_endpoint_failure_still_checks_final_health(self) -> None:
        fake = FakeTransport()
        fake.fail_path = ("/tokenize", 1)
        exit_code, summary, output = self.execute(fake)
        self.assertEqual(exit_code, gate.EXIT_GATE_FAILED)
        self.assertEqual(summary["failures"], ["endpoint_failure"])
        self.assertTrue(summary["health"]["after"])
        self.assertEqual([path for _, path, _ in fake.calls][-1], "/health")
        self.assertTrue((output / "02-tokenize.json").is_file())


if __name__ == "__main__":
    unittest.main()
