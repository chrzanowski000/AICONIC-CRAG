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
- [ ] **M3 Conflicts + replaced docs**
- [ ] **M4 Eval**
- [ ] **M5 Hardening + docs**

## Last verified outputs

- `python main.py ask` on Q1 → ANSWERED, "A pull request needs 2 approvals ... [D14]", cites D14
  (Jev relevance 0.98; D15 and D20 gave no claim). Q5 (pets) → ABSTAINED: D02 and D01 gave no
  claim, judge skipped, closest D02 (0.636), D01 (0.587), D07 (0.566). Q2, Q3, Q4, Q6, Q7 also
  give the expected result already (details in M3).

- `python main.py llm-test` → method `json_schema`, 1.8 s, 951 in / 66 out tokens, $0.000128:
  `[D03] Helios Dynamics offers 16 weeks of fully paid parental leave.`,
  `[D04] Employees receive 12 weeks of paid parental leave at full salary.`, `[D13] None`.
- `python main.py jev-test` → 10/10 as expected (rel D03 0.98, D04 0.95, TX 0.93, D16 0.01;
  D03–D04 disagree 1.00; D03–TX agree 1.00; pairs with D16 unrelated 1.00). 0.4 s, $0.0000578.

- `python main.py index` → `Rebuilt collection 'helios_docs' (embedded mode): 20 points.`
  Second run → `Reused ... 20 points. Reason: index is up to date.`
- `python main.py search "parental leave"` → D03 0.7789 and D04 0.7479 both kept.
- Search on the demo questions (context after cutoff 0.58, margin 0.10, related docs):
  Q1 → D14 (+ D15, D20 by topic); Q2 → D02, D01; Q3 → D03 (+ D04 by topic, it was 0.0004 under
  the margin); Q4 → D05, D06; Q5 (pets) → D02, D01 (the judge must reject them);
  Q6 → D09, D10, D18; Q7 → D08, D07.
- Score gap: best hit of answerable questions (incl. paraphrases) ≥ 0.62; clearly off questions
  ≤ 0.54. Some off questions still score up to 0.70 ("vacation days" → remote work), so the judge
  is the real gate, as planned.
- Jev Decisions API test call works; format matches the plan (`noul` p, `choice` + probabilities).
- `openai/gpt-6-luna` on OpenRouter: $0.10 / $0.50 per million tokens (in / out), supports
  `response_format`, `structured_outputs`, `reasoning_effort`.

## Next step

M3: `questions.json`, `main.py demo`, check the number check, write the real traces into
`docs/pipeline.md`.

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
| **total** | | **0.00137** |
