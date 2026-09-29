# Decisions

Each decision below is fixed for this project. The reason is given in one or two lines. If a
decision changes, change it here first.

## What decides the outcome

| # | decision | why |
|---|---|---|
| 1 | Only an explicit `supersedes` link in document metadata can settle a conflict. | A newer date is not proof. A chat digest from May is not more right than a handbook from April. |
| 2 | Even when a document is replaced, the old value is still shown with its date. | The user should see that the fact changed and when. |
| 3 | When two current documents disagree, show both and give no answer. | Picking one would hide the problem. The user must decide or ask the owner. |
| 4 | The dispute report, the "outdated" note and the "I don't know" text are built by Python. | A model could soften "16 weeks vs 12 weeks" into "around 12 to 16 weeks". Code cannot. |
| 5 | The LLM only pulls out claims and writes the final answer. It never decides who is right. | Keeps text-writing and deciding apart, so each part can be checked. |
| 6 | Jev only answers yes/no and multiple-choice questions and returns probabilities. | It cannot write text, so it cannot write a vague middle answer. Probabilities make thresholds easy to tune. |
| 7 | A number check backs up the judge. | If two current same-topic claims have different numbers and the judge saw no dispute, we add one. A soft judge cannot hide a clear clash. |
| 8 | Two gates before an answer: the search score cutoff and the judge's relevance. | Either one failing leads to "I don't know". |

## Models and services

| # | decision | why |
|---|---|---|
| 9 | LLM: `openai/gpt-6-luna` through OpenRouter, with `ChatOpenAI(base_url=...)`. | Cheap ($0.10 / $0.50 per million tokens in / out), supports structured output. See `models.md`. |
| 10 | Never send `temperature`; send `reasoning_effort=low`; `use_responses_api=False`. | The GPT-6 family rejects `temperature`. Low effort keeps cost and time down. |
| 11 | `provider.require_parameters=true` on OpenRouter. | Only route to hosts that honour `response_format`. |
| 12 | Structured output tries `json_schema` (strict), then `function_calling`, then `json_mode` + Pydantic. | If one method is not supported, the next one still gives a checked object. |
| 13 | Judge: Jev `typesafe/jev-1.13` through `POST /api/alpha/decisions`. If it fails, the LLM judges. | One cheap call per question (about $0.00002). The fallback keeps the demo working if the alpha API changes. |
| 14 | Embeddings: `BAAI/bge-small-en-v1.5` with FastEmbed (ONNX, CPU). | Small, fast, local, free. 384 numbers, cosine. |
| 15 | Qdrant embedded (`./qdrant_data`) by default; server mode by config. | No Docker needed to run the demo. Server mode is one setting away. |
| 16 | LangSmith is optional and only switched on by env vars. | Everything must work with tracing off. |

## Retrieval

| # | decision | why |
|---|---|---|
| 17 | Vector search with k=6 and a score cutoff, then add every doc with the same `topic` and every doc linked by `supersedes`. | Both sides of a dispute must be in context. A metadata filter makes that certain, not just likely. |
| 18 | No reranker, no BM25 / hybrid search. | 20 short documents. Plain vector search plus the topic expansion already finds everything. Fewer parts, fewer failures. |
| 19 | No NLI model. | Jev already gives agree / disagree probabilities. An NLI model would be one more local model and is weak on numbers. |
| 20 | No web search. | The task is about what the documents say, not about the world. |

## Code and repo

| # | decision | why |
|---|---|---|
| 21 | `config.py` holds every setting. No other module reads `os.environ`. | One place to look, one place to change. `python main.py config` prints it all. |
| 22 | Point id = `uuid5(NAMESPACE_URL, doc_id)`. | Writing the same doc twice updates it instead of adding a copy. |
| 23 | The index is rebuilt when the corpus hash changes. | Editing a document can never leave a stale index behind. |
| 24 | Token use and cost are printed after every CLI run. | The budget is about $4. Cost must stay visible. |
| 25 | Pin every package version. | The demo must still install the same way later. |
