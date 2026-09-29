# CLAUDE.md

## Rules that come first

1. **Commits use Conventional Commits.** `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
   Imperative mood, subject line 72 characters or less.
2. **Never mention Claude, AI, assistants, or AI co-authorship** in commit messages, code,
   comments, docs, or any other text in this repo. Do not add a `Co-Authored-By` trailer.
3. **Use plain English.** Prefer simple, common words. If something can be said without fancy
   words, say it that way. This applies to docs, comments, commit messages, CLI output, prompts,
   and replies in chat. Short sentences beat long ones.
4. **Update `STATUS.md` before every commit** so progress is never lost.
5. **Push after every milestone** and after every `STATUS.md` update.

## What this project is

A small RAG system over 20 made-up documents about a fictional company (Helios Dynamics).
Some documents contradict each other. Some are old and replaced by newer ones.

The system must:
- answer with citations when there is one current answer,
- show **both** versions with dates when two sources disagree (never pick one),
- prefer the newer document only when the older one is explicitly marked as replaced,
- say "I don't know" when nothing in the documents answers the question.

It is judged on one thing: it must work. Simple and working beats pretty.

## Stack

- Python 3.12, CPU only.
- LangChain (`langchain-core`, `langchain-openai`, `langchain-qdrant`) for building blocks.
- LangGraph for the pipeline (a state graph with typed state and conditional edges).
- LangSmith for tracing and eval. Optional: everything works with tracing off. Tracing is off by
  default; turn it on with `LANGSMITH_TRACING=true` (key in `.env` as `LANGSMITH_API_KEY`).
- Qdrant as the vector store. Embedded mode by default (`./qdrant_data`), server mode by config.
- FastEmbed for local embeddings (`BAAI/bge-small-en-v1.5`).
- OpenRouter for the LLM (`openai/gpt-6-luna`). It is the only external service besides
  LangSmith.

## How it works (short)

`retrieve → extract_claims (LLM) → compare (LLM) → reconcile (Python rules) → answer (LLM + LLM check) | conflict_report | abstain`

- Retrieval: vector search (cutoff `SCORE_THRESHOLD` 0.58, and at most `SCORE_MARGIN` 0.10 below
  the best hit), then every doc with the same `topic` is added (a doc and the doc it
  `supersedes` always share a topic, so both ends of a link come in).
- The LLM extracts claims: a claim holds only the part of a doc that answers the question.
- The LLM compares: is each claim relevant, and for each pair not linked by `supersedes`, do the
  claims give the same answer, a different one, or are they unrelated? If different, it says
  what differs ("D03 says 16 weeks, D04 says 12 weeks"). It never decides who is right.
- The answer is written from the claims; a second LLM call checks it for facts no claim states
  and for values the docs give differently (one more try, then a note).
- Python rules apply `supersedes` links, keep the disputes between current docs, and pick the
  route. There is no regex number check and no other model.
- The dispute report and the "outdated" note are rendered by code, not by a model.

The big picture: `docs/architecture.md`. Every step with real traces: `docs/pipeline.md`.

## Commands

```
python main.py config            # print every setting (secrets masked)
python main.py index [--reindex] # build or refresh the Qdrant collection
python main.py search "<q>"      # retrieval smoke test, no LLM
python main.py llm-test          # one structured-output call through OpenRouter
python main.py ask "<q>"         # run the full pipeline on one question
python main.py demo [--all]      # run the 5 demo questions (--all: all 18)
python eval.py                   # local PASS/FAIL, exit 1 on FAIL; also LangSmith eval if tracing is on
python -m pytest                 # unit tests, no model calls (needs requirements-dev.txt)
langgraph dev                    # LangGraph Studio server on 127.0.0.1:2024 (needs requirements-dev.txt)
```

## Layout

```
config.py          the one place for every setting (models, URLs, thresholds, paths, flags)
main.py            CLI
eval.py            evaluation
questions.json     18 questions with expected results (Q1-Q5 are the demo)
langgraph.json     Studio config: graph `helios_rag` = src/studio.py:graph
data/corpus/       the 20 documents (markdown with frontmatter)
src/               load_docs, embeddings, vectorstore, llm, schemas, prompts, graph, render,
                   studio (Studio entry point)
tests/             unit tests: graph rules, citations, dates in the output, corpus checks (pytest)
docs/              documentation of the repo (architecture, pipeline, decisions, corpus, evaluation,
                   setup, research, models; plan.md is the original plan, kept as history)
STATUS.md          what is done, what is next, known issues, money spent
```

## Conventions

- All settings live in `config.py`. No other module reads `os.environ`.
- Secrets come from `.env` (`LLM_API_OR` is the OpenRouter key). Never commit `.env`.
- Every doc shown to the user carries its creation date: sources and dispute versions as
  `[doc_id] source (created date)`; "What differs" and the outdated note as `[doc_id] (created
  date)`; the closest docs of "I don't know" as `Dxx (created date, score ...)`.
- Pin versions in `requirements.txt`.
- Keep the budget in mind: about $4 of OpenRouter credit. Print token use and cost per run.
  The running total is kept in `.spend.json` (not committed); copy it into `STATUS.md`.
- After changing a document, a prompt, a threshold or the model: run `python eval.py` twice
  (the LLM can answer differently from run to run); both runs must pass.
- Documents: `data/corpus/Dxx_name.md` with frontmatter `id, title, source, date, topic, supersedes`.

## Working with this repo

- Read `STATUS.md` first to see where things stand.
- Small milestones. Each one ends in something you can run.
- When a milestone is done: update `STATUS.md` (and this file or `docs/` if anything changed),
  commit with a conventional message, push.
