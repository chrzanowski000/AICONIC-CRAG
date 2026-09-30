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
| 3a | When several current documents agree, all of them are listed as sources. Python adds every document the LLM marked `same` as a cited one. | The reader sees how many documents back the answer, and a document that agrees is never left out because the answer text named only one. Done in code, so it does not depend on the model remembering. |
| 3b | The answer answers only what is asked. Each source line shows the document's snippet (its claim) as extracted, even if it holds other information, and the system does not comment on that. | The answer stays exact, and the sources stay complete and checkable against the documents. Example: for "Do I keep my salary during parental leave?" the answer says only that pay is 100%; D04's source line also mentions 12 weeks, and that is left as it is. Decided 2026-09-30. |
| 4a | Every document shown carries its creation date ("created YYYY-MM-DD" from the `date` field), added by code: on sources, both versions of a dispute, "What differs", the outdated note and the closest documents of "I don't know". | The reader can see how old each version is and judge a dispute. Code adds the dates, so they cannot be wrong or missing. Dates are shown, never used to decide. |
| 5 | The LLM pulls out claims, compares them, and writes the final answer. It never decides who is right. | Which document wins is decided by Python from `supersedes` links, so a model can never settle a dispute. |
| 6 | The LLM compares each pair of claims as same / different / unrelated, and for "different" says what differs, with both values ("D03 says 16 weeks, D04 says 12 weeks"). That sentence is shown in the dispute report. | The user sees exactly where the documents disagree, not just that they do. One model reads numbers, dates, names and rules in context, so no fragile number parser is needed. |
| 7 | No Jev and no regex number check (both removed in the `llm-judge` round). | Jev only gave probabilities and needed an alpha API, a fallback and thresholds; the regex guessed units from the next word ("1 March" read as `{march: 1}`, no unit conversion). The LLM judge had already passed the full eval as Jev's fallback; with a prompt that asks for exact values it passes 18/18 on its own. |
| 8 | Two gates before an answer: the search score cutoff and the LLM's relevance. | Either one failing leads to "I don't know". |
| 8a | A claim keeps only the part of the document that answers the question, and the LLM compares only that part. | Two documents can disagree on one thing and agree on the rest. Without this, "Does parental leave cover adoption?" was reported as a dispute because the claims carried the disputed week counts. |
| 8b | The answer is written from the checked claims, not from the full documents. | From the full text the model added "for the full 16 weeks [D03]" to an answer about pay, quietly picking a side of a dispute the question did not ask about. |
| 8c | A second LLM call checks the answer against the claims and the full text of the current documents: facts no claim states, and values the documents give differently. One retry, then the answer is kept with a note. | A third safety net against picking a side by accident. It replaces a regex check. In `demo --all` it caught one "12 weeks" leak, the retry fixed it, and no good answer got a note. |

## Models and services

| # | decision | why |
|---|---|---|
| 9 | LLM: `openai/gpt-6-luna` through OpenRouter, with `ChatOpenAI(base_url=...)`. | Cheap ($0.10 / $0.50 per million tokens in / out), supports structured output. See `models.md`. |
| 10 | Never send `temperature`; send `reasoning_effort=low`; `use_responses_api=False`. | The GPT-6 family rejects `temperature`. Low effort keeps cost and time down. |
| 11 | `provider.require_parameters=true` on OpenRouter. | Only route to hosts that honour `response_format`. |
| 12 | Structured output uses `json_schema` (strict) only. If the reply cannot be parsed, the run stops with a clear error. | Until the simplification round it also tried `function_calling` and `json_mode`, and each step had its own fallback (start of each doc as the claim, plain-text answer). `json_schema` worked in every run, and the claims fallback would bring back the false disputes that narrow claims fixed, so all of it was removed. |
| 12a | (removed with the `function_calling` fallback) `function_calling` was done with `bind_tools` directly, not with LangChain's `with_structured_output`. | LangChain always sends `parallel_tool_calls=false`. The gpt-6-luna hosts on OpenRouter do not list that parameter, so with `require_parameters=true` OpenRouter found no host (HTTP 404). Worth knowing if `function_calling` is ever needed again. |
| 13 | (removed) The judge was Jev `typesafe/jev-1.13` through `POST /api/alpha/decisions`, with the LLM as fallback and thresholds of 0.5. | Replaced by the LLM judge, see 6 and 7. |
| 14 | Embeddings: `BAAI/bge-small-en-v1.5` with FastEmbed (ONNX, CPU). | Small, fast, local, free. 384 numbers, cosine. |
| 15 | Qdrant embedded (`./qdrant_data`) by default; server mode by config. | No Docker needed to run the demo. Server mode is one setting away. |
| 16 | LangSmith is optional and only switched on by env vars. | Everything must work with tracing off. |

## Retrieval

| # | decision | why |
|---|---|---|
| 17 | Vector search with k=6 and a score cutoff, then add every doc with the same `topic`. | Both sides of a dispute must be in context. Adding by topic makes that certain, not just likely. A doc and the doc it `supersedes` must share a topic (checked when the corpus is loaded), so no separate `supersedes` step is needed. |
| 17a | Cutoff 0.58, plus a margin: drop hits more than 0.10 below the best hit. | The embedding model scores even unrelated docs at 0.50 to 0.65, so the cutoff alone lets in lots of noise. The margin keeps the context to the docs about the question. Measured in M0, see `pipeline.md`. |
| 18 | No reranker, no BM25 / hybrid search. | 40 short documents. Plain vector search plus the topic expansion already finds everything. Fewer parts, fewer failures. |
| 19 | No NLI model. | The LLM already says same / different and what differs. An NLI model would be one more local model and is weak on numbers. |
| 20 | No web search. | The task is about what the documents say, not about the world. |

## Code and repo

| # | decision | why |
|---|---|---|
| 21 | `config.py` holds every setting. No other module reads `os.environ`. | One place to look, one place to change. `python main.py config` prints it all. |
| 22 | Point id = `uuid5(NAMESPACE_URL, doc_id)`. | Writing the same doc twice updates it instead of adding a copy. |
| 23 | The index is rebuilt when the corpus hash changes. | Editing a document can never leave a stale index behind. |
| 24 | Token use and cost are printed after every CLI run. | The budget is about $4. Cost must stay visible. |
| 25 | Pin every package version. | The demo must still install the same way later. |
