# Status

Last update: 2026-09-29. All milestones of `docs/plan.md` are done, plus a round of fixes to
dispute detection and the LangSmith connection (see below). Now: a simplification round on the
branch `simplification` (less code, same results).

## Milestones

- [x] **M-1 Repo bootstrap**: remote, `.gitignore`, `STATUS.md`, `README.md`, `docs/decisions.md`,
      `docs/architecture.md`, `docs/research.md` (31 sources), `docs/models.md` +
      `docs/models_price_vs_score.png`, `requirements-dev.txt`.
- [x] **M0 Documents + index + retrieval test**: venv, pinned requirements, `.env.example`,
      `config.py`, 20 documents, `load_docs.py`, `embeddings.py`, `vectorstore.py`,
      `main.py config|index|search`, `docs/setup.md`, `docs/corpus.md`.
- [x] **M1 LLM + Jev + LangSmith tests**: `llm.py`, `jev.py`, `schemas.py`, `prompts.py`,
      `main.py llm-test|jev-test`. LangSmith traces checked later (see "LangSmith connected").
- [x] **M2 Graph v1**: `graph.py`, `render.py`, `main.py ask`.
- [x] **M3 Conflicts + replaced docs**: `questions.json`, `main.py demo [--all]`, number check,
      thresholds set from measured probabilities, real traces in `docs/pipeline.md`.
- [x] **M4 Eval**: `eval.py`, six shared checks, `docs/evaluation.md`.
- [x] **M5 Hardening + docs**: fallbacks tested, one bug fixed (`function_calling`), clear
      one-line errors, server mode tested, final README and docs.
- [x] **Dispute check round**: 13 targeted questions found 2 false disputes (D03/D04 agree on
      adoption and on pay, but the claims carried the disputed week counts) and one answer that
      quietly picked a side ("for the full 16 weeks [D03]"). Fixed: narrow claims, judge compares
      only the part that answers the question, answer written from the claims, number check on
      the answer, new eval check `answer_excludes`. `questions.json` grew from 7 to 18 questions.
- [x] **LangSmith connected**: key in `.env` as `LANGSMITH_API_KEY` (it was saved as
      `LANG_SMITH_API_KEY`, which nothing reads). Tracing stays off by default and is switched on
      with `LANGSMITH_TRACING=true`. Added: a warning when tracing is asked for without a key,
      a flush of queued traces at the end of each command, the LLM model in the run metadata.
- [x] **LangGraph Studio**: `langgraph.json` + `src/studio.py` (graph `helios_rag`), input schema
      with only `question`, `langgraph-cli[inmem]==0.4.32` in `requirements-dev.txt`.
      The last step also writes `output`, the result as plain text, because Studio's step view
      showed only `outdated []` of the nested `result` object (the answer was there, but hidden).
- [x] **Number check cleaned up**: moved out of `graph.py` into `src/quantities.py` (commented
      pattern, small named functions, docstring on what it is for). New unit tests in `tests/`
      (`python -m pytest`, 26 tests, no model calls); `pytest==9.1.1` in `requirements-dev.txt`.
- [ ] **Simplification** (branch `simplification`): remove code that is not needed, keep every
      result the same. Each step is checked with `pytest` and live runs.
  - Step 1, retrieval: the related docs are taken from the corpus in memory, by topic only. Gone:
    the Qdrant topic filter, the separate `supersedes` step, the server-mode keyword indexes and
    the `EXPAND_BY_TOPIC` / `EXPAND_BY_SUPERSEDES` flags. New corpus check instead: a doc and the
    doc it replaces must share a topic. New `tests/test_load_docs.py` (4 tests). Checked:
    retrieval gives the same docs as `main` for 25 questions; `pytest` 30 passed; `demo` 5/5.
  - Step 2, rules: removed checks that can never be true (two current docs are never in the same
    "replaces" chain, and a current doc is never also outdated). `_replaced_by` is built once.
    The unit test for "a replaced doc gives no number dispute" tested an input the pipeline never
    makes; it is replaced by 5 `reconcile` tests (outdated, judge dispute, number check, agree,
    abstain). Checked: `reconcile` and `disputed_numbers` give the same output as `main` on 2000
    random states (all three routes); `pytest` 34 passed.
  - Step 3, fallbacks: structured output uses `json_schema` only (it was used in every run).
    Gone: the `function_calling` and `json_mode` paths, the "method that worked last" memory, the
    claims fallback (start of each doc; it would bring back the false disputes), the plain-text
    answer fallback, `LLM_STRUCTURED_METHODS` and `JUDGE_FALLBACK` (Jev failing always hands over
    to the LLM judge). A parse or API error now stops the run with a one-line `ERROR`; the list
    of such errors is shared by `main.py` and `eval.py`. `src/llm.py` 209 → 142 lines. Checked:
    `pytest` 34 passed; `llm-test` OK; bad model id → one-line error, exit 2; Jev made to fail →
    LLM judges, Q3 still DISPUTED; `eval.py` (Jev) 18/18 PASS.

## Last verified outputs (2026-09-29)

- Number check refactor: old and new code give identical results on all 20 documents and 22
  sample sentences (42 texts, 231 sentence pairs, 16 clashes). `python -m pytest` → 26 passed.
  Through the Studio server: Q3 → DISPUTED D03/D04; Q14 → ANSWERED "paid at 100% of your base
  salary ... [D03]" with no week count. `eval.py` not rerun (the Studio server holds the index).

- `langgraph dev --no-browser` → up in 3 s on `127.0.0.1:2024`; `/ok` answers from WSL and from
  Windows (`curl.exe`, PowerShell). Assistant `helios_rag` has input schema `{question}` and nodes
  retrieve, extract_claims, judge, reconcile, answer, conflict_report, abstain. `POST /runs/wait`
  with Q3 → `disputed`, versions D03 (2025-01-10) and D04 (2025-02-20), `judge_used=jev`.
  While it runs, `main.py` gives the Qdrant "in use" message (expected, documented).
- After adding `output`: three runs through the dev server → Q1 `STATUS: ANSWERED ... 2 approvals
  [D14]`, Q4 `STATUS: DISPUTED` with D05 $60 / D06 $75, "What is the company's stock price?" →
  `STATUS: ABSTAINED` at the search (best 0.541 < 0.58). `eval.py` not rerun for this change
  (the Studio server holds the index); the change only adds a field, `result` is unchanged.

- LangSmith (US server, project `rag-conflicts`):
  - `LANGSMITH_TRACING=true python main.py jev-test` / `llm-test` → runs `jev_judge` (with
    `cost` in metadata) and `RunnableSequence` → ChatOpenAI show up.
  - `LANGSMITH_TRACING=true python main.py ask "<Q3>"` → one trace `ask` (19 runs): retrieve,
    extract_claims → ChatOpenAI, judge → jev_judge, reconcile, conflict_report; metadata
    `judge=jev`, `llm=openai/gpt-6-luna`.
  - `LANGSMITH_TRACING=true python eval.py` → local 18/18, dataset `rag-conflicts-demo` created
    (18 examples), experiment `rag-conflicts-jev-4af5fc19`: 18 runs, 0 errors, 126/126 feedback
    scores are 1. Exit 0.
  - `LANGSMITH_TRACING=true JUDGE=llm python eval.py` → dataset reused (still one), experiment
    `rag-conflicts-llm-07eb37b5`: 18 runs, 0 errors, 126/126 scores are 1. Exit 0.
  - Tracing off (default) → no "Traces sent" line, nothing sent. Tracing on without a key →
    warning, `TRACING_ON False`.
  - LangSmith shows tokens and cost for each ChatOpenAI call (it matches the OpenRouter price,
    e.g. 239 in / 40 out tokens → $0.0000439). Jev's cost is in the `jev_judge` metadata.

- `python eval.py` → 18/18 PASS, exit 0 (judge Jev). 33 LLM calls + 17 Jev calls, $0.0031.
- `JUDGE=llm python eval.py` → 18/18 PASS, exit 0. 50 LLM calls, $0.0041.
- In both runs the number check on the answer fired once (a parental leave answer restated
  "12 weeks") and the retry was clean.
- `JEV_DISAGREE_P=1.01 python eval.py` (judge never reports a dispute) → only Q8 FAIL, exit 1:
  the number check still catches Q3 and Q4, but not the word dispute Q8.
- `JEV_DISAGREE_P=1.01 NUMERIC_BACKSTOP=false python eval.py` → Q3, Q4, Q8 FAIL, exit 1.
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

Nothing required. Open item, if wanted: more questions in `questions.json` (for example the
paraphrases checked by hand in M3). After changing `questions.json`, delete the LangSmith dataset
`rag-conflicts-demo` so the next traced eval creates it again.

## Known issues

- **Changed from the plan** (all written down in `docs/decisions.md` and `docs/pipeline.md`):
  - retrieval cutoff 0.58 instead of 0.45, plus a new `SCORE_MARGIN` (0.10);
  - `JEV_RELEVANT_P` and `JEV_DISAGREE_P` 0.5 instead of 0.6;
  - `function_calling` does not use `with_structured_output` (it sent `parallel_tool_calls`,
    which made OpenRouter find no host);
  - the state has a `closest` field (for "I don't know"), and `judge_used` can be `none`;
  - running spend total in `.spend.json`.
- Disputes in words (not two numbers for the same thing), like Q8, are caught only by the judge.
  The number checks cannot see them.
- The number check on the answer only knows about numbers. If an answer adds a disputed detail in
  words, only the claims-only rule stops it.
- The score cutoff cannot separate every off-topic question from an answerable one (off-topic
  questions reach 0.70, answerable paraphrases go down to 0.62). The judge is the real gate; it
  rejected every off-topic doc in the tests.
- The system is tested on this corpus and these questions only.

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | two probe calls by hand (Jev, gpt-6-luna) | 0.00004 |
| 2026-09-29 | all app runs, M1–M5 (from `.spend.json`, 40+ runs) | 0.01809 |
| 2026-09-29 | dispute check round: app runs (from `.spend.json`) | 0.01392 |
| 2026-09-29 | dispute check round: 3 test-script runs (not in `.spend.json`) | 0.00958 |
| 2026-09-29 | fresh eval + LangSmith round (traced tests, ask, two traced evals) | 0.01814 |
| 2026-09-29 | Studio setup: demo check + one run through the dev server | 0.00084 |
| 2026-09-29 | review + simplification round: evals, demos, probe questions (from `.spend.json`) | 0.00898 |
| **total** | | **0.06959** |

Budget: $4.00. Left: about $3.93.
