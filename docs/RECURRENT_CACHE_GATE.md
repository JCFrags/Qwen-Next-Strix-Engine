# Recurrent prompt-cache gate

`harness/recurrent_cache_gate.py` runs one fixed four-request check against a running `llama-server`. It checks the native `/apply-template` -> `/tokenize` -> `/completion` path. It does not change the evaluator in `qwen38_harness.py`.

The request files, expected markers, rendered prompts, model output, and raw endpoint responses are private. Use a new private output directory for each run. Do not commit that directory.

## Inputs

Pass exactly four chat request JSON files as positional arguments. Their command-line order is their execution order. Each file must contain:

```json
{
  "messages": [{"role": "user", "content": "private text"}],
  "chat_template_kwargs": {},
  "max_tokens": 32,
  "temperature": 0,
  "seed": 7,
  "top_k": 1,
  "top_p": 1.0,
  "min_p": 0.0,
  "stream": false,
  "stop": ["private stop text"]
}
```

`messages`, `chat_template_kwargs`, one positive token limit, `temperature: 0`, and a nonnegative `seed` are required. The token limit can be `max_tokens` or `max_completion_tokens`, but not both. `top_k`, `top_p`, `min_p`, and `stop` are optional. If `stream` is present, it must be a Boolean. The runner always uses a non-streaming native completion so it can validate the final timing and stop fields. Other chat request fields are not sent to `/completion`.

The expected-marker file is a JSON object keyed by the fixed one-based request position:

```json
{
  "1": "private expected value one",
  "2": "private expected value two",
  "3": "private expected value three",
  "4": "private expected value four"
}
```

Each value must be a nonempty string. Values can repeat because the third request returns to the first value. The file must contain at least two distinct markers. One distinct marker cannot contain another distinct marker. These rules make the stale-marker check unambiguous.

## Exact endpoint sequence

The runner uses one base URL and slot zero. It performs these calls in order:

1. `GET /health`. The response must be HTTP 200 with `{"status":"ok"}`.
2. For each request, in fixed order:
   1. `POST /apply-template` with only `messages` and `chat_template_kwargs` from that request. The response must contain a nonempty string `prompt`.
   2. `POST /tokenize` with the rendered prompt as `content`, `add_special: true`, and `parse_special: true`. The response must contain a nonempty array of nonnegative integer token IDs.
   3. `POST /completion` with the same rendered prompt. The runner maps `max_tokens` or `max_completion_tokens` to `n_predict`. It copies the validated deterministic `temperature`, `seed`, and optional `top_k`, `top_p`, `min_p`, and `stop` settings. It also sets `stream: false`, `cache_prompt: true`, `id_slot: 0`, and `timings_per_token: true`.
3. `GET /health` again, including after a request failure when the first health call started.

The completion response must report slot zero, a completed stop, `truncated: false`, a stop type other than `limit`, nonnegative token counts, and the standard cache, prompt, and prediction timing fields. `tokens_evaluated` must equal the separate `/tokenize` token count. `timings.cache_n` is the number of prompt tokens that the server reused. `timings.prompt_n` is the number of prompt tokens that it processed. Their sum must equal `tokens_evaluated`. The native top-level `tokens_cached` field is the resulting slot cache size after generation. It is recorded as `slot_cache_tokens`, but it is not a prompt-reuse count. The runner rejects missing, incorrectly typed, non-finite, or inconsistent fields.

For output validation, the runner takes the text after the last `</think>` and removes outer whitespace. That visible text must equal the request's expected marker. It must not contain any other configured marker.

The runner records the SHA-256 of the exact UTF-8 rendered prompt. It also records the token count and the common-prefix token count against only the immediately previous request. Requests two, three, and four must each have a planned common prefix and a `timings.cache_n` reuse count at or above `--minimum-cached-tokens`. The runner rejects a threshold below 45,000 tokens. A prompt-reuse count cannot exceed the planned common prefix.

## Run

```text
python3 harness/recurrent_cache_gate.py \
  private/request-1.json \
  private/request-2.json \
  private/request-3.json \
  private/request-4.json \
  --expected-markers private/expected-markers.json \
  --base-url http://127.0.0.1:8080 \
  --output-dir private/run-001 \
  --minimum-cached-tokens 45000
```

The output directory must be empty or absent. The runner sets directory mode `0700` and file mode `0600` where the operating system supports these modes. It writes raw health, template, tokenize, and completion responses only there.

`public-summary.json` and standard output contain no request path, base URL, prompt text, visible output, expected marker, or raw response. The public summary contains only the decision, safe failure codes, health booleans, prompt SHA-256 values, prompt-reuse counts, slot cache counts, prefix counts, and numeric timings.

Exit code `0` means all checks passed. Exit code `2` means local input or output setup was invalid. Exit code `10` means an endpoint, response, output, cache, truncation, or health check failed.

## Offline tests

The tests use an injected mock transport. They do not open a network connection or run inference.

```text
python3 -m unittest discover -s tests -v
```

The cases cover success, low cache reuse, a wrong marker, an extra configured marker, malformed response data, truncation, and endpoint failure.
