# Status

Last update: 2026-09-29. All milestones of `docs/plan.md` are done.

## Milestones

- [x] **M-1 Repo bootstrap**: remote, `.gitignore`, `STATUS.md`, `README.md`, `docs/decisions.md`,
      `docs/architecture.md`, `docs/research.md` (31 sources), `docs/models.md` +
      `docs/models_price_vs_score.png`, `requirements-dev.txt`.
- [x] **M0 Documents + index + retrieval test**: venv, pinned requirements, `.env.example`,
      `config.py`, 20 documents, `load_docs.py`, `embeddings.py`, `vectorstore.py`,
      `main.py config|index|search`, `docs/setup.md`, `docs/corpus.md`.
- [x] **M1 LLM + Jev tests**: `llm.py`, `jev.py`, `schemas.py`, `prompts.py`,
      `main.py llm-test|jev-test`. LangSmith not checked (no key, see known issues).
- [x] **M2 Graph v1**: `graph.py`, `render.py`, `main.py ask`.
- [x] **M3 Conflicts + replaced docs**: `questions.json`, `main.py demo [--all]`, number check,
      thresholds set from measured probabilities, real traces in `docs/pipeline.md`.
- [x] **M4 Eval**: `eval.py`, six shared checks, `docs/evaluation.md`.
- [x] **M5 Hardening + docs**: fallbacks tested, one bug fixed (`function_calling`), clear
      one-line errors, server mode tested, final README and docs.

## Last verified outputs (2026-09-29)

- `python eval.py` → 7/7 PASS, exit 0 (judge Jev). 11 LLM calls + 6 Jev calls, $0.00115.
- `JUDGE=llm python eval.py` → 7/7 PASS, exit 0. 17 LLM calls, $0.00148.
- `JEV_DISAGREE_P=1.01 NUMERIC_BACKSTOP=false python eval.py` → Q3, Q4 FAIL, exit 1 (the eval
  catches a system that gives one answer to a disputed question).
- `JEV_DISAGREE_P=1.01 python main.py demo` → Q3, Q4 still disputed by the number check alone.
- `python main.py demo` → Q1 answered [D14]; Q2 answered [D02] + outdated D01 (2024-03-01) →
  D02 (2025-06-15); Q3 disputed D03/D04; Q4 disputed D05/D06; Q5 abstained.
- Structured output: `json_schema` (default), `function_calling` and `json_mode` each work alone
  with `LLM_STRUCTURED_METHODS=<method> python main.py llm-test`; an unknown method is skipped;
  with every method failing, `ask` still gives the right answer (claims = start of each doc,
  plain-text answer).
- Judge fallback: `JEV_URL=<bad path>` (HTTP 404) and `JEV_URL=<unreachable host>` with
  `JEV_TIMEOUT_S=3` → warning, LLM judges, right result. With `JUDGE_FALLBACK=none` →
  `ERROR (JevError): HTTP 404 ...`, exit 2.
- Lock: a second process on embedded Qdrant → `ERROR (LockedStorageError)` with the three ways
  out, exit 2.
- `QDRANT_MODE=server` against `qdrant/qdrant:latest` (1.19.1) in Docker → 20 points, keyword
  indexes on `metadata.topic` and `metadata.id`, index reused on the next run, same demo
  results. An older server (1.16.3) works too but prints a version warning.
- `python main.py jev-test` → 10/10 as expected, 0.4 s, $0.0000578.
- `python main.py llm-test` → method `json_schema`, about 1.5 s, $0.00013.
- `python main.py index` → 20 points; `search "parental leave"` → D03 0.7789, D04 0.7479.
- Retrieval scores and Jev probabilities used for the thresholds: see `docs/pipeline.md`.

## Next step

Nothing required. Open items, if wanted:

1. Add a LangSmith key and run `python eval.py` with `LANGSMITH_TRACING=true` to check the traces
   and the LangSmith experiment (the code is written, not yet run).
2. More questions in `questions.json` (for example the spare password dispute and paraphrases
   that were checked by hand in M3).

## Known issues

- **LangSmith not verified.** No `LANGSMITH_API_KEY` in `.env`, so neither the traces nor the
  LangSmith part of `eval.py` has been run. Tracing is off by default, and it is also turned off
  when `LANGSMITH_TRACING=true` is set without a key. Everything else works without it.
- **Changed from the plan** (all written down in `docs/decisions.md` and `docs/pipeline.md`):
  - retrieval cutoff 0.58 instead of 0.45, plus a new `SCORE_MARGIN` (0.10);
  - `JEV_RELEVANT_P` and `JEV_DISAGREE_P` 0.5 instead of 0.6;
  - `function_calling` does not use `with_structured_output` (it sent `parallel_tool_calls`,
    which made OpenRouter find no host);
  - the state has a `closest` field (for "I don't know"), and `judge_used` can be `none`;
  - running spend total in `.spend.json`.
- The score cutoff cannot separate every off-topic question from an answerable one (off-topic
  questions reach 0.70, answerable paraphrases go down to 0.62). The judge is the real gate; it
  rejected every off-topic doc in the tests.
- The system is tested on this corpus and these questions only.

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | two probe calls by hand (Jev, gpt-6-luna) | 0.00004 |
| 2026-09-29 | all app runs, M1–M5 (from `.spend.json`, 40+ runs) | 0.01809 |
| **total** | | **0.01813** |

Budget: $4.00. Left: about $3.98.
