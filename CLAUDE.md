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
- LangSmith for tracing and eval. Optional: everything works with tracing off.
- Qdrant as the vector store. Embedded mode by default (`./qdrant_data`), server mode by config.
- FastEmbed for local embeddings (`BAAI/bge-small-en-v1.5`).
- OpenRouter for the LLM (`openai/gpt-6-luna`) and for the Jev decision model
  (`typesafe/jev-1.13`). These are the only external services besides LangSmith.

## How it works (short)

`retrieve → extract_claims (LLM) → judge (Jev) → reconcile (Python rules) → answer | conflict_report | abstain`

- The LLM only extracts claims and writes the final answer. It never decides who is right.
- Jev only answers yes/no and multiple-choice questions (is this doc relevant? do these two
  claims agree or disagree?). It never writes text.
- Python rules apply `supersedes` links, keep real disputes, and pick the route.
- The dispute report and the "outdated" note are rendered by code, not by a model.

Full description with a diagram and worked examples: `docs/pipeline.md`.

## Commands

```
python main.py config            # print every setting (secrets masked)
python main.py index [--reindex] # build or refresh the Qdrant collection
python main.py search "<q>"      # retrieval smoke test, no LLM
python main.py llm-test          # one structured-output call through OpenRouter
python main.py jev-test          # one Jev decision call
python main.py ask "<q>"         # run the full pipeline on one question
python main.py demo              # run the 5 demo questions
python eval.py                   # local PASS/FAIL; also LangSmith eval if tracing is on
```

## Layout

```
config.py          the one place for every setting (models, URLs, thresholds, paths, flags)
main.py            CLI
eval.py            evaluation
questions.json     demo questions and expected results
data/corpus/       the 20 documents (markdown with frontmatter)
src/               load_docs, embeddings, vectorstore, llm, jev, schemas, prompts, graph, render
docs/              documentation of the repo (plan, setup, architecture, pipeline, corpus, evaluation,
                   research, models, decisions)
STATUS.md          what is done, what is next, known issues, money spent
```

## Conventions

- All settings live in `config.py`. No other module reads `os.environ`.
- Secrets come from `.env` (`LLM_API_OR` is the OpenRouter key). Never commit `.env`.
- Every claim shown to the user carries `[doc_id] source (date)`.
- Pin versions in `requirements.txt`.
- Keep the budget in mind: about $4 of OpenRouter credit. Print token use and cost per run.
- Documents: `data/corpus/Dxx_name.md` with frontmatter `id, title, source, date, topic, supersedes`.

## Working with this repo

- Read `STATUS.md` first to see where things stand.
- Small milestones. Each one ends in something you can run.
- When a milestone is done: update `STATUS.md` (and this file or `docs/` if anything changed),
  commit with a conventional message, push.
