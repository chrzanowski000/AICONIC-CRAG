# Decisions

Each decision below is fixed for this project, with its reason in one or two lines. If a decision
changes, change it here first.

## What decides the outcome

| # | decision | why |
|---|---|---|
| 1 | Only an explicit `supersedes` link in document metadata can settle a conflict. | A newer date is not proof. A chat digest from May is not more right than a handbook from April. |
| 2 | Even when a document is replaced, the old value is still shown with its date. | The user should see that the fact changed and when. |
| 3 | When current documents disagree, show every version and give no answer. | Picking one would hide the problem. The user must decide or ask the owner. |
| 4 | The dispute report, the "outdated" note and the "I don't know" text are built by Python. | A model could soften "16 weeks vs 12 weeks" into "around 12 to 16 weeks". Code cannot. |
| 5 | Every document shown carries its creation date ("created YYYY-MM-DD" from the `date` field), added by code: on sources, every version of a dispute, "What differs", the outdated note and the closest documents of "I don't know". | The reader can see how old each version is. Code adds the dates, so they cannot be wrong or missing. Dates are shown, never used to decide. |
| 6 | When several current documents agree, all of them are sources. Python adds every document the LLM marked `same` as a cited one. | The reader sees every document that backs the answer. Done in code, so it does not depend on the model remembering. |
| 7 | The answer answers only what is asked. Each source line shows the document's claim as extracted, even if it holds other information, and nothing comments on that. | The answer stays exact and the sources stay checkable. Example: for "Do I keep my salary during parental leave?" the answer says only that pay is 100%; D04's source line also mentions 12 weeks, and that is left as it is. |

## Reading and comparing

| # | decision | why |
|---|---|---|
| 8 | The LLM pulls out claims, compares them, writes the answer and checks it. It never decides who is right. | Which document wins is decided by Python from `supersedes` links, so a model can never settle a dispute. |
| 9 | The LLM compares each pair of claims as same / different / unrelated, and for "different" says what differs, with both values ("D03 says 16 weeks, D04 says 12 weeks"). That sentence is shown in the dispute report. | The user sees exactly where the documents disagree. The LLM reads numbers, dates, names and rules in context. |
| 10 | One model only: no separate decision model and no regex number parser. | One model, one API and one path are simpler to run and to test. A number parser has to guess units from the next word ("1 March" read as an amount) and misses disputes in words; the LLM does not. |
| 11 | Two gates before an answer: the search score cutoff and the LLM's relevance. | Either one failing leads to "I don't know". |
| 12 | A claim keeps only the part of the document that answers the question, and the LLM compares only that part. | Two documents can disagree on one thing and agree on the rest. Without this, "Does parental leave cover adoption?" was reported as a dispute because the claims carried the disputed week counts. |
| 13 | The answer is written from the claims, not from the full documents. | From the full text the model added "for the full 16 weeks [D03]" to an answer about pay, quietly picking a side of a dispute the question did not ask about. |
| 14 | A second LLM call checks the answer against the claims and the full text of the current documents: facts no claim states, and values the documents give differently. One retry, then the answer is kept with a note. | A safety net against picking a side by accident. |

## Models and services

| # | decision | why |
|---|---|---|
| 15 | LLM: `openai/gpt-6-luna` through OpenRouter, with `ChatOpenAI(base_url=...)`. | Supports structured output and scored well on the test claims. See `models.md`. |
| 16 | Never send `temperature`; send `reasoning_effort=low`; `use_responses_api=False`. | The GPT-6 family rejects `temperature`. Low effort keeps the replies fast. |
| 17 | `provider.require_parameters=true` on OpenRouter. | Only route to hosts that honour `response_format`. |
| 18 | Structured output uses `json_schema` (strict) only. If the reply cannot be parsed, the run stops with a clear error. | It works in every run. A fallback that used the start of each document as the claim would bring back false disputes. |
| 19 | When OpenRouter answers HTTP 200 with an error inside instead of a reply, wait and retry (2, 4, 8 s). | It happens about once in 20 calls (a short upstream rate limit); the OpenAI client does not retry it by itself. |
| 20 | Embeddings: `BAAI/bge-small-en-v1.5` with FastEmbed (ONNX, CPU). | Small, fast, local, free. 384 numbers, cosine. |
| 21 | Qdrant embedded (`./qdrant_data`) by default; server mode by config. | No Docker needed to run the demo. Server mode is one setting away. |
| 22 | LangSmith is optional and only switched on by env vars. | Everything must work with tracing off. |

## Retrieval

| # | decision | why |
|---|---|---|
| 23 | Vector search with k=6 and a score cutoff, then add every doc with the same `topic`. | Both sides of a dispute must be in context. Adding by topic makes that certain, not just likely. A doc and the doc it `supersedes` must share a topic (checked when the corpus is loaded), so both ends of a link come in too. |
| 24 | Cutoff 0.58, plus a margin: drop hits more than 0.10 below the best hit. | The embedding model scores even unrelated docs at 0.50 to 0.65, so the cutoff alone lets in lots of noise. The margin keeps the context to the docs about the question. See `pipeline.md`. |
| 25 | No reranker, no BM25 / hybrid search. | 40 short documents. Plain vector search plus the topic expansion already finds everything. Fewer parts, fewer failures. |
| 26 | No NLI model. | The LLM already says same / different and what differs. An NLI model would be one more local model and is weak on numbers. |
| 27 | No web search. | The task is about what the documents say, not about the world. |

## Code, repo and evaluation

| # | decision | why |
|---|---|---|
| 28 | `config.py` holds every setting. No other module reads `os.environ`. | One place to look, one place to change. `python main.py config` prints it all. |
| 29 | Point id = `uuid5(NAMESPACE_URL, doc_id)`. | Writing the same doc twice updates it instead of adding a copy. |
| 30 | The index is rebuilt when the corpus hash changes. | Editing a document can never leave a stale index behind. |
| 32 | Pin every package version. | The demo must still install the same way later. |
| 33 | The eval checks disputes and "I don't know" by the output's `dispute` and `no_answer` flags and the linked documents (code only). Questions with one answer have a hand-written reference answer, and an LLM grader compares the answer with it. | Disputes and "I don't know" are built by code, so a structure check is exact. Only a free-text answer needs a grader, and the reference answer holds only what the question asks. |
| 34 | Each dataset is a folder `data/<name>/` (documents and questions) with its own Qdrant collection (`<name>_docs`) and LangSmith dataset (`rag-conflicts-<name>-<fingerprint>`). It is chosen with `--dataset` or `DATASET`; the prompts, rules, thresholds and model are shared. | Datasets can never mix, switching is one flag, and a second company shows that nothing in the code is tuned to the first one. |
