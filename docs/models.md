# Model comparison

Checked on 2026-09-29. This page explains why the pipeline uses `openai/gpt-6-luna`. It first
used Jev (`typesafe/jev-1.13`) to make decisions; Jev has since been removed and the LLM does
all the judging (see "The judge" below and `decisions.md` 7).

- Prices, context sizes and supported parameters come from the public OpenRouter model list
  (`https://openrouter.ai/api/v1/models`) and its per-model endpoint lists. Prices are in USD
  per 1 million tokens (the API gives USD per token; we multiplied by 1,000,000).
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
that is cheap, follows a JSON schema, and can copy facts without changing them. We do not need
top-level reasoning.

Hard requirements: OpenRouter must list `response_format` and `structured_outputs` for the
model, and the price must leave a large margin inside the $4 budget.

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

| model (OpenRouter id) | input $/M | output $/M | structured output | context (tokens) | score (setting) | note |
|---|---:|---:|---|---:|---|---|
| **`openai/gpt-6-luna`** | **0.10** | **0.50** | yes | 1,050,000 | **37 (max); 21 (low)** | **chosen**; reasoning can be set from `none` to `max`; no `temperature` |
| `openai/gpt-6-sol` | 2.00 | 10.00 | yes | 1,050,000 | 48 (max) | bigger sibling; 20× the price for +11 points |
| `openai/gpt-5.6-luna` | 0.20 | 1.20 | yes | 1,050,000 | 37 (max) | previous Luna; same score at 2–2.4× the price |
| `google/gemini-3.8-flash` | 0.75 | 3.75 | yes | 1,048,576 | 41 (high) | reasoning cannot be turned off |
| `google/gemini-3.5-flash-lite` | 0.30 | 2.50 | yes | 1,048,576 | 22 | costly output for its score |
| `z-ai/glm-5.3-flash` | 0.15 | 0.50 | yes | 1,310,720 | 42 | best score near our price; reasoning always on (default `max`); 34 hosts, 7 without structured output |
| `deepseek/deepseek-v4.1-flash` | 0.30 | 1.20 | yes | 1,048,576 | 39 (max) | good and fast; 3× our input price |
| `xiaomi/mimo-v2.6-flash` | 0.14 | 0.28 | yes | 1,048,576 | 38 | cheapest good score; no `reasoning_effort` control |
| `xiaomi/mimo-v2.6-pro` | 0.435 | 0.87 | yes | 1,050,000 | 46 | best value in the mid-price range |
| `qwen/qwen3.8-max-0902` | 2.00 | 6.00 | yes | 1,000,000 | 45 | reasoning always on (default `xhigh`) |
| `moonshotai/kimi-k3` | 3.00 | 15.00 | yes | 1,048,576 | 44 (max) | most expensive in the list |
| `mistralai/mistral-small-2603` | 0.15 | 0.60 | yes | 262,144 | 11 | Mistral Small 4; cheap but weak |
| `openai/gpt-oss-120b` | 0.037 | 0.17 | yes | 131,072 | 12 (high) | cheapest; weak; open weights |

Every candidate has a score, so none is marked "n/a". The score for `openai/gpt-5.6-luna` comes
from its model page, because the leaderboard marks it as deprecated and leaves it out of the
default table.

![Price vs score](models_price_vs_score.png)

The x axis uses a **blended price = 0.75 × input price + 0.25 × output price** per 1 million
tokens (a 3 to 1 mix of input and output tokens), on a log scale. Our own calls are even more
input-heavy (about 6 to 1), so the blended price slightly overstates models with costly output.
The blue stem shows gpt-6-luna at its best setting (filled dot) and at the `low` setting we use
(open dot). The price per token is the same for both. Only the number of reasoning tokens
changes.

## Cost of one demo run

Assumptions, stated so they can be checked:

- 5 demo questions, and we count **2 LLM calls for every question = 10 calls**. This is an upper
  bound. In practice an answered question needs 2 calls, a disputed one needs 1, and a question
  that fails the retrieval cutoff needs 0, so the real count is about 6.
- Each call uses about **2,500 input tokens and 400 output tokens**. Reasoning tokens are billed
  as output, so they are inside the 400.
- Cost of a run = 10 × (2,500 × input price + 400 × output price) / 1,000,000.

| model | cost of one demo run | runs that fit in $4 |
|---|---:|---:|
| `openai/gpt-oss-120b` | $0.0016 | about 2,490 |
| **`openai/gpt-6-luna`** | **$0.0045** | **about 890** |
| `xiaomi/mimo-v2.6-flash` | $0.0046 | about 870 |
| `z-ai/glm-5.3-flash` | $0.0057 | about 700 |
| `mistralai/mistral-small-2603` | $0.0062 | about 650 |
| `openai/gpt-5.6-luna` | $0.0098 | about 410 |
| `deepseek/deepseek-v4.1-flash` | $0.0123 | about 325 |
| `xiaomi/mimo-v2.6-pro` | $0.0144 | about 280 |
| `google/gemini-3.5-flash-lite` | $0.0175 | about 230 |
| `google/gemini-3.8-flash` | $0.0338 | about 120 |
| `qwen/qwen3.8-max-0902` | $0.0740 | about 54 |
| `openai/gpt-6-sol` | $0.0900 | about 44 |
| `moonshotai/kimi-k3` | $0.1350 | about 30 |

**Measured** (M2, 2026-09-29, `reasoning_effort=low`): the 5 demo questions together used 7 LLM
calls and 4 Jev calls and cost **$0.0007**, about 6 times less than the upper bound above. Real
calls use 700 to 1,500 input tokens and 50 to 150 output tokens, because the margin in the
retrieval step keeps only 2 or 3 documents in the context.

With gpt-6-luna, one demo run costs less than half a cent. Even if reasoning tripled the output
tokens (1,200 per call), a run would cost about $0.0085, and $4 would still pay for more than 450
runs. (Measured after Jev was removed: the 5 demo questions take 13 LLM calls and cost about
$0.0011.)

## The judge: Jev vs the other options (history)

This section is the comparison made in M-1. Jev was the judge until the `llm-judge` round; now
the LLM judges (row 2 of the table below), with a prompt that asks for exact values and for
what differs. Reasons: one model and one API instead of two, no alpha API, no fallback path and
no thresholds to tune, and the LLM can say what differs, which Jev cannot. It passes the full
eval on its own.

The judge answers two kinds of questions: "does document D03 answer the question?" (yes/no) and
"do the claims of D03 and D04 agree, disagree, or is one unrelated?" (pick one of three).

**Jev** (`typesafe/jev-1.13`, dated `typesafe/jev-1.13-20260917`) is a decision model. It is
called through OpenRouter's Decisions API (`POST https://openrouter.ai/api/alpha/decisions`,
still marked alpha). It supports three question types: `choice`, `noul` (yes/no) and `score`. For
a `choice` question it returns the chosen option, a probability for every option and a
confidence value. For a `noul` question it returns the probability of "yes". It cannot write
free text. Price: $0.042 per 1 million input tokens, and output tokens are free. Context: 32,000
tokens, which is plenty for up to 10 short claims and 45 pair questions.

Measured on 2026-09-29: one call with 538 input and 67 output tokens cost **$0.0000226**
(538 × $0.042 / 1,000,000; the output was free). The probabilities in that test looked
plausible, but we have not measured how well they are calibrated. So the thresholds
(`JEV_RELEVANT_P`, `JEV_DISAGREE_P`) live in `config.py` and were set to 0.5 from the printed
values (see `pipeline.md`, `reconcile`).

| option | what it returns | cost per question | used? | why |
|---|---|---|---|---|
| **Jev** (Decisions API) | a probability for each option | about $0.00002 | **removed** (was the default) | cannot write text, so it cannot blur a conflict; probabilities can be tuned with thresholds; one call covers every document and pair |
| LLM as judge (gpt-6-luna, structured `Comparison`) | true/false per document, same / different / unrelated per pair, and what differs | about $0.00045 (2,500 in, 400 out), about 20× Jev | **yes, now the judge** (was the fallback) | one model for everything and it can say what differs; LLM judges have known biases (Zheng et al. 2023) and give no probabilities, so the eval is the guard |
| NLI cross-encoder (a small local model) | entail / neutral / contradict per sentence pair | no API cost, but an extra model to download and run on CPU | **no** | does not see the question, so it cannot say "unrelated to this question"; NLI models are weak with numbers (Ravichander et al. 2019), and most of our disputes are about numbers |

Either way, Python still makes the final call (see [pipeline.md](pipeline.md), `reconcile`).

## Why gpt-6-luna

- **Cheap.** $0.10 in and $0.50 out per million tokens. About $0.0045 per demo run, even with the
  upper-bound count of calls.
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

To be fair: gpt-6-luna is **not** the best score per dollar. GLM-5.3 Flash (42) and
MiMo-V2.6-Flash (38) score higher than its best (37) at about the same price, and MiMo-V2.6-Pro (46)
costs about 3 times more per run. If gpt-6-luna fails the eval, these are the first models to try.
Switching is one setting: `LLM_MODEL` in `.env`.

### Risks and what we do about them

- **No `temperature`.** OpenRouter lists no `temperature` support on any gpt-6-luna endpoint.
  `LLM_TEMPERATURE` is empty by default, so we never send it. Set it only for a model that
  supports it.
- **Low effort scores much lower.** At `low` the index score is 21, against 37 at `max`. If
  claims come out wrong, set `LLM_REASONING_EFFORT=medium` (score 29). This costs more output
  tokens but stays far inside the budget.
- **New model.** It was released on 2026-09-22. The id `openai/gpt-6-luna` points to
  `openai/gpt-6-luna-20260922` today and may move to a newer version later.
- **Cheaper option not used.** The `openai/flex` endpoint costs half ($0.05 / $0.25). We do not
  need it at this budget.

## Sources

- OpenRouter model list, read 2026-09-29: <https://openrouter.ai/api/v1/models>
- OpenRouter endpoint lists, read 2026-09-29:
  <https://openrouter.ai/api/v1/models/openai/gpt-6-luna/endpoints>,
  <https://openrouter.ai/api/v1/models/z-ai/glm-5.3-flash/endpoints>,
  <https://openrouter.ai/api/v1/models/xiaomi/mimo-v2.6-flash/endpoints>,
  <https://openrouter.ai/api/v1/models/typesafe/jev-1.13/endpoints>
- Artificial Analysis, LLM leaderboard (scores, speed), read 2026-09-29:
  <https://artificialanalysis.ai/leaderboards/models>
- Artificial Analysis, Intelligence Index method (v4.3.2, list of tests and weights):
  <https://artificialanalysis.ai/methodology/intelligence-benchmarking>
- Artificial Analysis model pages: <https://artificialanalysis.ai/models/gpt-6-luna>,
  <https://artificialanalysis.ai/models/gpt-6-luna-low>,
  <https://artificialanalysis.ai/models/gpt-5-6-luna>
- OpenRouter, Jev guide (question types, outputs, Decisions API):
  <https://openrouter.ai/docs/guides/community/jev>; model page:
  <https://openrouter.ai/typesafe/jev-1.13>
- Zheng et al. (2023), Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena:
  <https://arxiv.org/abs/2306.05685>
- Ravichander et al. (2019), EQUATE, a benchmark for quantitative reasoning in natural language
  inference: <https://arxiv.org/abs/1901.03735>

More background on these choices: [research.md](research.md).
