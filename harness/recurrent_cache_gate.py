#!/usr/bin/env python3
"""Run the private four-turn recurrent prompt-cache gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

EXIT_PASS = 0
EXIT_USAGE = 2
EXIT_GATE_FAILED = 10
REQUEST_COUNT = 4
MIN_REQUIRED_CACHED_TOKENS = 45_000
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
TIMING_FIELDS = (
    "prompt_n",
    "prompt_ms",
    "prompt_per_token_ms",
    "prompt_per_second",
    "predicted_n",
    "predicted_ms",
    "predicted_per_token_ms",
    "predicted_per_second",
)


class GateError(ValueError):
    """A safe failure that does not contain private input or output."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class EndpointError(GateError):
    """A server endpoint did not return one usable response."""


Transport = Callable[[str, str, bytes | None, float], tuple[int, bytes]]


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise GateError("input_invalid")
        value[key] = item
    return value


def _reject_constant(_value: str) -> None:
    raise GateError("input_invalid")


def _loads_json(data: str | bytes, error_code: str) -> Any:
    try:
        return json.loads(
            data,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except GateError:
        raise GateError(error_code) from None
    except (UnicodeError, json.JSONDecodeError):
        raise GateError(error_code) from None


def load_private_json(path: Path) -> Any:
    try:
        data = path.read_bytes()
    except OSError:
        raise GateError("input_invalid") from None
    return _loads_json(data, "input_invalid")


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_object(value: Any, code: str = "input_invalid") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError(code)
    return value


def _require_nonnegative_int(value: Any, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise GateError(code)
    return value


def _require_number(value: Any, code: str) -> int | float:
    if not _is_number(value) or value < 0:
        raise GateError(code)
    return value


class OutputStore:
    """Write private response bytes and one public summary to one directory."""

    def __init__(self, path: Path):
        self.path = path
        try:
            if path.is_symlink():
                raise GateError("output_invalid")
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            if not path.is_dir() or any(path.iterdir()):
                raise GateError("output_invalid")
            os.chmod(path, 0o700)
        except GateError:
            raise
        except OSError:
            raise GateError("output_invalid") from None

    def write_bytes(self, name: str, data: bytes) -> None:
        self._atomic_write(name, data)

    def write_json(self, name: str, value: Any) -> None:
        try:
            data = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        except (TypeError, ValueError):
            raise GateError("summary_invalid") from None
        self._atomic_write(name, data)

    def _atomic_write(self, name: str, data: bytes) -> None:
        if Path(name).name != name:
            raise GateError("output_invalid")
        descriptor: int | None = None
        temporary = ""
        try:
            descriptor, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=self.path)
            os.fchmod(descriptor, stat.S_IRUSR | stat.S_IWUSR)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path / name)
        except OSError:
            raise GateError("output_invalid") from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if temporary:
                try:
                    os.unlink(temporary)
                except FileNotFoundError:
                    pass


def urllib_transport(method: str, url: str, body: bytes | None, timeout: float) -> tuple[int, bytes]:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(MAX_RESPONSE_BYTES + 1)
            status = response.status
    except urllib.error.HTTPError as exc:
        data = exc.read(MAX_RESPONSE_BYTES + 1)
        status = exc.code
    except (urllib.error.URLError, TimeoutError, OSError):
        raise EndpointError("endpoint_failure") from None
    if len(data) > MAX_RESPONSE_BYTES:
        raise EndpointError("endpoint_failure")
    return status, data


class ServerClient:
    def __init__(
        self,
        base_url: str,
        store: OutputStore,
        transport: Transport = urllib_transport,
        timeout: float = 3600.0,
    ):
        parsed = urllib.parse.urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise GateError("input_invalid")
        self.base_url = base_url.rstrip("/")
        self.store = store
        self.transport = transport
        self.timeout = timeout

    def get(self, path: str, raw_name: str) -> dict[str, Any]:
        return self._request("GET", path, None, raw_name)

    def post(self, path: str, payload: dict[str, Any], raw_name: str) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
        return self._request("POST", path, body, raw_name)

    def _request(
        self,
        method: str,
        path: str,
        body: bytes | None,
        raw_name: str,
    ) -> dict[str, Any]:
        try:
            status, data = self.transport(
                method,
                f"{self.base_url}{path}",
                body,
                self.timeout,
            )
        except GateError:
            raise
        except Exception:
            raise EndpointError("endpoint_failure") from None
        self.store.write_bytes(raw_name, data)
        if status != 200:
            raise EndpointError("endpoint_failure")
        return _require_object(_loads_json(data, "malformed_response"), "malformed_response")


def validate_markers(value: Any) -> list[str]:
    mapping = _require_object(value)
    required = {str(index) for index in range(1, REQUEST_COUNT + 1)}
    if set(mapping) != required:
        raise GateError("input_invalid")
    markers: list[str] = []
    for index in range(1, REQUEST_COUNT + 1):
        marker = mapping[str(index)]
        if not isinstance(marker, str) or not marker or marker != marker.strip():
            raise GateError("input_invalid")
        markers.append(marker)
    distinct_markers = set(markers)
    if len(distinct_markers) < 2:
        raise GateError("input_invalid")
    if any(
        left in right
        for left in distinct_markers
        for right in distinct_markers
        if left != right
    ):
        raise GateError("input_invalid")
    return markers


def _validate_stop(value: Any) -> str | list[str]:
    if isinstance(value, str) and value:
        return value
    if (
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item for item in value)
    ):
        return value
    raise GateError("input_invalid")


def validate_request(value: Any) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    request = _require_object(value)
    messages = request.get("messages")
    if not isinstance(messages, list) or not messages:
        raise GateError("input_invalid")
    for message in messages:
        if not isinstance(message, dict):
            raise GateError("input_invalid")
        if not isinstance(message.get("role"), str) or not message["role"]:
            raise GateError("input_invalid")
        if "content" not in message:
            raise GateError("input_invalid")

    template_kwargs = request.get("chat_template_kwargs")
    if not isinstance(template_kwargs, dict):
        raise GateError("input_invalid")

    token_limit_keys = [
        key for key in ("max_tokens", "max_completion_tokens") if key in request
    ]
    if len(token_limit_keys) != 1:
        raise GateError("input_invalid")
    n_predict = _require_nonnegative_int(request[token_limit_keys[0]], "input_invalid")
    if n_predict == 0:
        raise GateError("input_invalid")

    temperature = request.get("temperature")
    if not _is_number(temperature) or temperature != 0:
        raise GateError("input_invalid")
    seed = _require_nonnegative_int(request.get("seed"), "input_invalid")
    if "stream" in request and not isinstance(request["stream"], bool):
        raise GateError("input_invalid")

    settings: dict[str, Any] = {
        "n_predict": n_predict,
        "temperature": temperature,
        "seed": seed,
    }
    if "top_k" in request:
        settings["top_k"] = _require_nonnegative_int(request["top_k"], "input_invalid")
    for name in ("top_p", "min_p"):
        if name in request:
            setting = request[name]
            if not _is_number(setting) or not 0 <= setting <= 1:
                raise GateError("input_invalid")
            settings[name] = setting
    if "stop" in request:
        settings["stop"] = _validate_stop(request["stop"])
    return messages, template_kwargs, settings


def validate_health(value: dict[str, Any]) -> None:
    if value.get("status") != "ok":
        raise GateError("health_failed")


def validate_template(value: dict[str, Any]) -> str:
    prompt = value.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise GateError("malformed_response")
    return prompt


def validate_tokens(value: dict[str, Any]) -> list[int]:
    tokens = value.get("tokens")
    if not isinstance(tokens, list) or not tokens:
        raise GateError("malformed_response")
    if any(
        not isinstance(token, int) or isinstance(token, bool) or token < 0
        for token in tokens
    ):
        raise GateError("malformed_response")
    return tokens


def common_prefix_count(previous: list[int] | None, current: list[int]) -> int:
    if previous is None:
        return 0
    count = 0
    for left, right in zip(previous, current):
        if left != right:
            break
        count += 1
    return count


def validate_completion(
    value: dict[str, Any],
    token_count: int,
) -> tuple[str, int, dict[str, int | float]]:
    content = value.get("content")
    if not isinstance(content, str):
        raise GateError("malformed_response")
    if value.get("id_slot") != 0 or value.get("stop") is not True:
        raise GateError("malformed_response")

    truncated = value.get("truncated")
    stop_type = value.get("stop_type")
    if not isinstance(truncated, bool) or stop_type not in {"eos", "word", "limit"}:
        raise GateError("malformed_response")
    if truncated or stop_type == "limit":
        raise GateError("truncated")

    tokens_cached = _require_nonnegative_int(
        value.get("tokens_cached"), "malformed_response"
    )
    tokens_evaluated = _require_nonnegative_int(
        value.get("tokens_evaluated"), "malformed_response"
    )
    tokens_predicted = _require_nonnegative_int(
        value.get("tokens_predicted"), "malformed_response"
    )
    if tokens_evaluated != token_count or tokens_cached > tokens_evaluated:
        raise GateError("malformed_response")

    timings_value = _require_object(value.get("timings"), "malformed_response")
    timings: dict[str, int | float] = {}
    for name in TIMING_FIELDS:
        if name in {"prompt_n", "predicted_n"}:
            timings[name] = _require_nonnegative_int(
                timings_value.get(name), "malformed_response"
            )
        else:
            timings[name] = _require_number(
                timings_value.get(name), "malformed_response"
            )
    if timings["predicted_n"] != tokens_predicted:
        raise GateError("malformed_response")
    return content, tokens_cached, timings


def validate_visible_output(content: str, expected: str, markers: list[str]) -> None:
    visible = content.rsplit("</think>", 1)[-1].strip()
    if any(marker != expected and marker in content for marker in set(markers)):
        raise GateError("unexpected_marker")
    if visible != expected:
        raise GateError("wrong_marker")


def _request_summary(
    position: int,
    prompt: str,
    tokens: list[int],
    prefix_count: int,
    cached_tokens: int,
    threshold: int,
    timings: dict[str, int | float],
) -> dict[str, Any]:
    return {
        "position": position,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_tokens": len(tokens),
        "previous_common_prefix_tokens": prefix_count,
        "cached_tokens": cached_tokens,
        "cache_threshold_applies": position > 1,
        "common_prefix_threshold_met": position == 1 or prefix_count >= threshold,
        "cache_threshold_met": position == 1 or cached_tokens >= threshold,
        "cache_within_common_prefix": position == 1 or cached_tokens <= prefix_count,
        "visible_output_valid": True,
        "timings": timings,
    }


def run_gate(
    request_paths: list[Path],
    marker_path: Path,
    base_url: str,
    output_dir: Path,
    minimum_cached_tokens: int,
    transport: Transport = urllib_transport,
) -> tuple[int, dict[str, Any]]:
    if (
        len(request_paths) != REQUEST_COUNT
        or minimum_cached_tokens < MIN_REQUIRED_CACHED_TOKENS
    ):
        raise GateError("input_invalid")
    store = OutputStore(output_dir)
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    health_before = False
    health_after = False
    network_started = False

    try:
        markers = validate_markers(load_private_json(marker_path))
        requests = [validate_request(load_private_json(path)) for path in request_paths]
        client = ServerClient(base_url, store, transport)
        network_started = True
        validate_health(client.get("/health", "health-before.json"))
        health_before = True

        previous_tokens: list[int] | None = None
        for position, ((messages, template_kwargs, settings), marker) in enumerate(
            zip(requests, markers), start=1
        ):
            template = client.post(
                "/apply-template",
                {
                    "messages": messages,
                    "chat_template_kwargs": template_kwargs,
                },
                f"{position:02d}-apply-template.json",
            )
            prompt = validate_template(template)
            tokenized = client.post(
                "/tokenize",
                {
                    "content": prompt,
                    "add_special": True,
                    "parse_special": True,
                },
                f"{position:02d}-tokenize.json",
            )
            tokens = validate_tokens(tokenized)
            prefix_count = common_prefix_count(previous_tokens, tokens)

            completion_body = dict(settings)
            completion_body.update(
                {
                    "prompt": prompt,
                    "stream": False,
                    "cache_prompt": True,
                    "id_slot": 0,
                    "timings_per_token": True,
                }
            )
            completion = client.post(
                "/completion",
                completion_body,
                f"{position:02d}-completion.json",
            )
            content, cached_tokens, timings = validate_completion(
                completion, len(tokens)
            )
            validate_visible_output(content, marker, markers)
            records.append(
                _request_summary(
                    position,
                    prompt,
                    tokens,
                    prefix_count,
                    cached_tokens,
                    minimum_cached_tokens,
                    timings,
                )
            )
            if position > 1 and prefix_count < minimum_cached_tokens:
                raise GateError("common_prefix_below_threshold")
            if position > 1 and cached_tokens < minimum_cached_tokens:
                raise GateError("cache_below_threshold")
            if position > 1 and cached_tokens > prefix_count:
                raise GateError("cache_exceeds_common_prefix")
            previous_tokens = tokens
    except GateError as exc:
        failures.append(exc.code)
    finally:
        if network_started:
            try:
                validate_health(client.get("/health", "health-after.json"))
                health_after = True
            except GateError as exc:
                if exc.code not in failures:
                    failures.append(exc.code)

    passed = not failures and len(records) == REQUEST_COUNT and health_before and health_after
    summary = {
        "schema_version": 1,
        "decision": "pass" if passed else "fail",
        "request_count": REQUEST_COUNT,
        "completed_request_count": len(records),
        "minimum_cached_tokens": minimum_cached_tokens,
        "health": {"before": health_before, "after": health_after},
        "requests": records,
        "failures": failures,
    }
    store.write_json("public-summary.json", summary)
    return (EXIT_PASS if passed else EXIT_GATE_FAILED), summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the four-request recurrent prompt-cache gate."
    )
    parser.add_argument(
        "requests",
        metavar="REQUEST",
        nargs=REQUEST_COUNT,
        type=Path,
        help="private chat request JSON files in fixed execution order",
    )
    parser.add_argument("--expected-markers", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--minimum-cached-tokens",
        required=True,
        type=int,
        help="cache floor; values below 45000 are rejected",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        exit_code, summary = run_gate(
            args.requests,
            args.expected_markers,
            args.base_url,
            args.output_dir,
            args.minimum_cached_tokens,
        )
    except GateError as exc:
        summary = {
            "schema_version": 1,
            "decision": "fail",
            "request_count": REQUEST_COUNT,
            "completed_request_count": 0,
            "health": {"before": False, "after": False},
            "requests": [],
            "failures": [exc.code],
        }
        exit_code = EXIT_USAGE if exc.code in {"input_invalid", "output_invalid"} else EXIT_GATE_FAILED
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
