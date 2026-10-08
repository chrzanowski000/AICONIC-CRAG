# Model comparison

Checked on 2026-09-29. This page explains why the pipeline uses `openai/gpt-6-luna`, the only
model it calls.

- Context sizes and supported parameters come from the public OpenRouter model list
  (`https://openrouter.ai/api/v1/models`) and its per-model endpoint lists.
- Quality scores come from one public leaderboard: the **Artificial Analysis Intelligence
  Index** (v4.3), read on 2026-09-29. Links are at the end.

## What the text model has to do

The model has four small jobs (see [pipeline.md](pipeline.md)), all with structured output:

1. `extract_claims`: for each retrieved document, write one sentence that says what the
   document says about the question, with numbers copied exactly.
2. `compare`: say which claims answer the question and, for each pair, same / different /
   unrelated, naming both values when different.
3. `answer`: write 2 to 4 sentences, each ending with a `[Dxx]` citation.
4. The check on the answer: list facts no claim states and values the documents give
   differently.

It never decides which document is right and never writes the dispute report. So we need a model
that follows a JSON schema and can copy facts without changing them. We do not need
top-level reasoning.

Hard requirement: OpenRouter must list `response_format` and `structured_outputs` for the
model.

## About the score

The Intelligence Index is a weighted average of 10 tests: agent tasks 30%, coding 20%,
science reasoning 20%, and general tasks (knowledge, documents, long context) 30%. It measures
hard, multi-step work. Our jobs are much easier than that, so read the score as a rough guide to
general quality, not as a measure of claim extraction.

The score depends on how much the model is allowed to "think" before answering (the reasoning
setting). For example, GPT-6 Luna scores 37 at `max`, 34 at `xhigh`, 32 at `high`, 29 at
`medium`, 21 at `low` and 18 with reasoning off. When the leaderboard lists several settings
for a model, the table shows the best one, so every model is shown at its best. We run
gpt-6-luna at `low`, which scores 21.

## Candidates

All 13 candidates list both `response_format` and `structured_outputs` on OpenRouter.

| model (OpenRouter id) | structured output | context (tokens) | score (setting) | note |
|---|---|---:|---|---|
| **`openai/gpt-6-luna`** | yes | 1,050,000 | **37 (max); 21 (low)** | **chosen**; reasoning can be set from `none` to `max`; no `temperature` |
| `openai/gpt-6-sol` | yes | 1,050,000 | 48 (max) | bigger sibling; +11 points |
| `openai/gpt-5.6-luna` | yes | 1,050,000 | 37 (max) | previous Luna; same score |
| `google/gemini-3.8-flash` | yes | 1,048,576 | 41 (high) | reasoning cannot be turned off |
| `google/gemini-3.5-flash-lite` | yes | 1,048,576 | 22 | – |
| `z-ai/glm-5.3-flash` | yes | 1,310,720 | 42 | reasoning always on (default `max`); 34 hosts, 7 without structured output |
| `deepseek/deepseek-v4.1-flash` | yes | 1,048,576 | 39 (max) | – |
| `xiaomi/mimo-v2.6-flash` | yes | 1,048,576 | 38 | no `reasoning_effort` control |
| `xiaomi/mimo-v2.6-pro` | yes | 1,050,000 | 46 | – |
| `qwen/qwen3.8-max-0902` | yes | 1,000,000 | 45 | reasoning always on (default `xhigh`) |
| `moonshotai/kimi-k3` | yes | 1,048,576 | 44 (max) | – |
| `mistralai/mistral-small-2603` | yes | 262,144 | 11 | Mistral Small 4; weak |
| `openai/gpt-oss-120b` | yes | 131,072 | 12 (high) | weak; open weights |

Every candidate has a score, so none is marked "n/a". The score for `openai/gpt-5.6-luna` comes
from its model page, because the leaderboard marks it as deprecated and leaves it out of the
default table.

## Why gpt-6-luna

- **Structured output.** OpenRouter lists `response_format` and `structured_outputs`. It has 7
  endpoints (`openai`, `openai/flex`, `openai/fast`, `azure`, `azure/us`, `azure/eu`,
  `amazon-bedrock/us-east-1`). Only the Bedrock one lacks structured output, and
  `LLM_REQUIRE_PARAMETERS=true` keeps our requests off it. By contrast, GLM-5.3 Flash is served
  by 34 endpoints with different quantizations (fp4, fp8), and 7 of them lack structured output.
- **Reasoning is optional and adjustable.** Settings go from `none` to `max`. We send
  `reasoning_effort=low`. On the leaderboard's speed test, gpt-6-luna at `low` took about 5.6 s
  per full response. At `max` it took about 99 s. GLM-5.3 Flash and MiMo-V2.6-Flash, which reason
  by default, took about 55 s and 49 s.
- **Large context.** 1,050,000 tokens. We need less than 10,000.
- **Good enough for the job.** Copying one fact per document and writing a short cited answer
  does not need a top-scoring model. The eval (`python eval.py`) is the real test.

To be fair: gpt-6-luna does **not** have the best score. GLM-5.3 Flash (42), MiMo-V2.6-Flash (38)
and MiMo-V2.6-Pro (46) score higher than its best (37). If gpt-6-luna fails the eval, these are
the first models to try.
Switching is one setting: `LLM_MODEL` in `.env`.

### Risks and what we do about them

- **No `temperature`.** OpenRouter lists no `temperature` support on any gpt-6-luna endpoint.
  `LLM_TEMPERATURE` is empty by default, so we never send it. Set it only for a model that
  supports it.
- **Low effort scores much lower.** At `low` the index score is 21, against 37 at `max`. If
  claims come out wrong, set `LLM_REASONING_EFFORT=medium` (score 29). Replies then take longer.
- **New model.** It was released on 2026-09-22. The id `openai/gpt-6-luna` points to
  `openai/gpt-6-luna-20260922` today and may move to a newer version later.

## Sources

- OpenRouter model list, read 2026-09-29: <https://openrouter.ai/api/v1/models>
- OpenRouter endpoint lists, read 2026-09-29:
  <https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints>,
  <https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints>,
  <https://openrouter.ai/api/v1/models/xiaomi/mimo-v2.6-flash/endpoints>
- Artificial Analysis, LLM leaderboard (scores, speed), read 2026-09-29:
  <https://artificialanalysis.ai/leaderboards/models>
- Artificial Analysis, Intelligence Index method (v4.3.2, list of tests and weights):
  <https://artificialanalysis.ai/methodology/intelligence-benchmarking>
- Artificial Analysis model pages: <https://artificialanalysis.ai/models/gpt-6-luna>,
  <https://artificialanalysis.ai/models/gpt-6-luna-low>,
  <https://artificialanalysis.ai/models/gpt-5-6-luna>

More background on these choices: [research.md](research.md).
