# Helios RAG: answers that admit what they don't know

A small question-answering demo over 40 made-up documents about a fictional company, Helios
Dynamics. Some documents disagree. Some are old and replaced by newer ones.

The system:

- answers with citations when the documents give one current answer,
- shows **both** versions with dates when two documents disagree, and does not pick one,
- prefers the newer document only when the older one is marked as replaced, and still mentions
  the old one,
- says "I don't know" when no document answers the question.

The main rule: only an explicit `supersedes` link in the document metadata can make one source
win. A newer date never does.

## What it looks like

```
$ python main.py ask "How many weeks of paid parental leave does Helios Dynamics offer?"
STATUS: DISPUTED
Question: How many weeks of paid parental leave does Helios Dynamics offer?
The sources disagree. Both versions:
  - [D03] HR Handbook (created 2025-01-10): Helios Dynamics offers 16 weeks of fully paid parental leave.
  - [D04] People Ops wiki (created 2025-02-20): Employees receive 12 weeks of paid parental leave at full salary.
What differs:
  - [D03] (created 2025-01-10) vs [D04] (created 2025-02-20): D03 says 16 weeks, D04 says 12 weeks.
Neither document is marked as replacing the other; a newer date alone does not settle it.

$ python main.py ask "How many days per week can employees work remotely?"
STATUS: ANSWERED
Question: How many days per week can employees work remotely?
Employees may work remotely up to three days per week. [D02]
Sources:
  - [D02] HR Handbook (created 2025-06-15): Employees may work remotely up to three days per week.
Outdated:
  - [D01] (created 2024-03-01) said: "Employees may work remotely up to two days per week." It is
    replaced by [D02] (created 2025-06-15).

$ python main.py ask "What is the policy on bringing pets to the office?"
STATUS: ABSTAINED
Question: What is the policy on bringing pets to the office?
I don't know. The documents do not answer this question. None of the documents found says anything
that answers the question. Closest documents: D02 (created 2025-06-15, score 0.636), D01 (created
2024-03-01, score 0.587), D07 (created 2024-09-01, score 0.566).
```

(With `SHOW_SCORES=true`, the default, a short trace of every step follows each answer.)

## How it works

```
retrieve → extract_claims (LLM) → compare (LLM) → reconcile (Python rules) → answer (LLM + LLM check) | conflict_report | abstain
```

- **retrieve**: local embeddings (`BAAI/bge-small-en-v1.5`) and Qdrant. Weak hits are dropped,
  then every document with the same topic is added, so both sides of a dispute (and both ends of
  a `supersedes` link) are always seen.
- **extract_claims**: the LLM (`openai/gpt-6-luna` through OpenRouter) writes one sentence per
  document: what it says about the question, numbers copied exactly.
- **compare**: the LLM says which claims answer the question and, for every pair of documents
  not linked by `supersedes`, whether they give the same answer, a different one, or are
  unrelated. If different, it says what differs: "D03 says 16 weeks, D04 says 12 weeks".
  It never says which one is right.
- **reconcile**: plain Python. Applies `supersedes` links, keeps the disputes between current
  documents, and picks the route.
- **answer / conflict_report / abstain**: only the answer is written by the LLM, from the
  claims. Code checks its citations, and a second LLM call checks it for facts no claim states
  and for values the documents give differently (one more try, then a note). The dispute report,
  the outdated note and "I don't know" are built by code, so no model can blur "16 weeks vs
  12 weeks" into "about 12 to 16 weeks".

Full walkthrough with real traces: [`docs/pipeline.md`](docs/pipeline.md).

## Install

Python 3.12, CPU only.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # put your OpenRouter key in LLM_API_OR
python main.py index          # downloads the embedding model once (65 MB), builds the index
```

Details and troubleshooting: [`docs/setup.md`](docs/setup.md).

## Commands

```
python main.py config            # print every setting (secrets hidden)
python main.py index [--reindex] # build or refresh the Qdrant collection
python main.py search "<q>"      # retrieval test, no model calls
python main.py llm-test          # one structured-output call through OpenRouter
python main.py ask "<q>"         # run the full pipeline on one question
python main.py demo [--all]      # run the 5 demo questions (--all: all 34)
python eval.py                   # PASS/FAIL for all questions; exit code 1 on any FAIL
python -m pytest                 # unit tests, no model calls (pip install -r requirements-dev.txt)
langgraph dev                    # LangGraph Studio on 127.0.0.1:2024 (pip install -r requirements-dev.txt)
```

Every setting lives in `config.py` and can be changed in `.env` or the shell, for example
`LLM_MODEL=... python eval.py`. Token use and cost are printed after every run.

LangSmith tracing is off by default. With `LANGSMITH_API_KEY` in `.env`, add
`LANGSMITH_TRACING=true` to a command to trace it; `LANGSMITH_TRACING=true python eval.py` also
runs a LangSmith experiment on the same checks.

## Results

`python eval.py` passes all 34 questions (checked on two runs in a row). They cover every case:
documents that agree (also in different words), documents that disagree (in numbers, in words,
and three at once), one document that answers, no document that answers (also close to a real
topic), replaced documents (also a chain of three), and questions where the two sides of a
dispute agree on the point asked. A full eval costs about $0.01. The 35 unit tests
(`python -m pytest`) check the plain-code rules for free. See
[`docs/evaluation.md`](docs/evaluation.md).

## Documentation

To understand the system, read `docs/architecture.md` first (the parts and who does what), then
`docs/pipeline.md` (every step, with real traces).

| file | what |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | the big picture: parts, one question start to finish, who does what, modules, output, settings, failure handling |
| [`docs/pipeline.md`](docs/pipeline.md) | how the cases are told apart, the state, every step in detail, real traces, known limits |
| [`docs/decisions.md`](docs/decisions.md) | every design decision with its reason |
| [`docs/corpus.md`](docs/corpus.md) | the 40 documents, which case each one tests, and the rules they follow |
| [`docs/evaluation.md`](docs/evaluation.md) | the questions, the checks, the results, LangSmith |
| [`docs/setup.md`](docs/setup.md) | install, settings, server mode, problems |
| [`docs/research.md`](docs/research.md) | published work behind the design |
| [`docs/models.md`](docs/models.md) | why these models, prices, cost per run |
| [`docs/plan.md`](docs/plan.md) | the original plan (history, no longer up to date) |
| [`STATUS.md`](STATUS.md) | what is done, what is next, known issues, money spent |
