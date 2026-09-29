# Status

Last update: 2026-09-29

## Milestones

- [x] **M-1 Repo bootstrap**: remote, `.gitignore`, `STATUS.md`, `README.md` stub,
      `docs/decisions.md`, `docs/architecture.md`.
      `docs/research.md` and `docs/models.md` are still being written; they land in their own commit.
- [x] **M0 Documents + index + retrieval test** (no LLM): venv, pinned requirements,
      `.env.example`, `config.py`, 20 documents, `load_docs.py`, `embeddings.py`,
      `vectorstore.py`, `main.py config|index|search`, `docs/setup.md`, `docs/corpus.md`.
- [ ] **M1 LLM + Jev + LangSmith tests**
- [ ] **M2 Graph v1** (answer and abstain)
- [ ] **M3 Conflicts + replaced docs**
- [ ] **M4 Eval**
- [ ] **M5 Hardening + docs**

## Last verified outputs

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

M1: `llm.py`, `jev.py`, `schemas.py`, `main.py llm-test` and `jev-test`.

## Known issues

- No LangSmith key in `.env` yet, so tracing cannot be checked. Everything must work without it.
- Changed from the plan: cutoff 0.58 instead of 0.45, and a new `SCORE_MARGIN` (0.10). Reason in
  `docs/pipeline.md` and `docs/decisions.md` (17a).

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | one Jev test call | 0.00002 |
| **total** | | **0.00002** |
