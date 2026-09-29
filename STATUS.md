# Status

Last update: 2026-09-29

## Milestones

- [x] **M-1 Repo bootstrap**: remote, `.gitignore`, `STATUS.md`, `README.md` stub,
      `docs/decisions.md`, `docs/architecture.md`, `docs/research.md` (31 sources),
      `docs/models.md` + `docs/models_price_vs_score.png`, `requirements-dev.txt`.
- [x] **M0 Documents + index + retrieval test** (no LLM): venv, pinned requirements,
      `.env.example`, `config.py`, 20 documents, `load_docs.py`, `embeddings.py`,
      `vectorstore.py`, `main.py config|index|search`, `docs/setup.md`, `docs/corpus.md`.
- [x] **M1 LLM + Jev + LangSmith tests**: `llm.py` (client, `structured()` with fallbacks,
      tokens and cost, running total in `.spend.json`), `jev.py`, `schemas.py`, `prompts.py`,
      `main.py llm-test|jev-test`. LangSmith not checked yet: no key (see known issues).
- [x] **M2 Graph v1**: `graph.py` (all steps, incl. the reconcile rules and the conflict report),
      `render.py` (answer + a trace of every step when `SHOW_SCORES=true`), `main.py ask`.
- [x] **M3 Conflicts + replaced docs**: `questions.json` (Q1–Q5 demo, Q6–Q7 extra),
      `main.py demo [--all]`, number check tightened (ignores "X2", "7:00"), thresholds set from
      measured probabilities (`JEV_RELEVANT_P` and `JEV_DISAGREE_P` 0.6 → 0.5), real traces in
      `docs/pipeline.md`.
- [x] **M4 Eval**: `eval.py` with six shared checks (LangSmith evaluator signature), local
      PASS/FAIL table, exit code 1 on any FAIL, optional LangSmith dataset + experiment,
      `docs/evaluation.md`. The LangSmith part is written but not run yet (no key).
- [ ] **M5 Hardening + docs**

## Last verified outputs

- `python eval.py` → 7/7 PASS, exit 0, judge Jev, $0.00116.
- `JUDGE=llm python eval.py` → 7/7 PASS, exit 0, $0.00148.
- `JEV_DISAGREE_P=1.01 NUMERIC_BACKSTOP=false python eval.py` → Q3 and Q4 FAIL, exit 1 (the eval
  catches a system that gives one answer to a disputed question).

- `python main.py demo --all` (`JUDGE=jev`) → Q1 answered [D14]; Q2 answered [D02] + outdated
  D01 (2024-03-01) → D02 (2025-06-15); Q3 disputed D03/D04; Q4 disputed D05/D06; Q5 abstained;
  Q6 answered [D10] + outdated D09 → D10; Q7 answered [D08] + outdated D07 → D08.
  11 LLM calls + 6 Jev calls, $0.0012.
- `JUDGE=llm python main.py demo --all` → the same 7 results. 17 LLM calls, $0.0015.
- `JEV_DISAGREE_P=1.01 python main.py demo` (judge never reports a dispute) → Q3 and Q4 still
  disputed by the number check: "16 vs 12 week", "60 vs 75 $".
- 16 extra questions by hand: the spare dispute ("How often do I need to change my password?")
  → disputed D11/D12; paraphrases ("Who needs to approve my PR?", "How long is maternity leave?",
  "What's the per diem for food on business trips?", "Where is HQ?", ...) → right outcome;
  "How many vacation days do employees get?", "Who is the CEO?", "Can I bring my dog to work?"
  → abstained.
- Jev relevance: relevant docs 0.63–0.98, off topic 0.01–0.06. Disagree pairs 0.87–1.00.
- `python main.py llm-test` → method `json_schema`, 951 in / 66 out tokens, $0.000128.
- `python main.py jev-test` → 10/10 as expected, 0.4 s, $0.0000578.
- `python main.py index` → 20 points; reused on the next run.

## Next step

M5: force the structured-output fallbacks, point `JEV_URL` at a bad URL, check the stale-lock
message, run `QDRANT_MODE=server` against Docker Qdrant, final pass over README and docs.

## Known issues

- No LangSmith key in `.env` yet, so the traces cannot be checked. Tracing is off by default,
  and it is also turned off when `LANGSMITH_TRACING=true` is set without a key. Everything works
  without it. To check: add `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` to `.env`, run
  `llm-test` and `jev-test`, and look for the runs in the `rag-conflicts` project.
- Changed from the plan: cutoff 0.58 instead of 0.45, and a new `SCORE_MARGIN` (0.10). Reason in
  `docs/pipeline.md` and `docs/decisions.md` (17a).

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | one Jev test call (by hand, before M0) | 0.00002 |
| 2026-09-29 | M1: two small probe calls, `llm-test`, `jev-test` | 0.00020 |
| 2026-09-29 | M2: `ask` on 7 questions | 0.00115 |
| 2026-09-29 | M3: demo runs (jev, llm, soft judge) and 16 extra questions | 0.00693 |
| 2026-09-29 | M4: eval runs (jev, llm, negative test) + one ask | 0.00385 |
| **total** | | **0.01215** |
