# Status

Last update: 2026-09-29

## Milestones

- [x] **M-1 Repo bootstrap**: remote, `.gitignore`, `STATUS.md`, `README.md` stub,
      `docs/decisions.md`, `docs/architecture.md`.
      `docs/research.md` and `docs/models.md` are being written and land in the next commit.
- [ ] **M0 Documents + index + retrieval test** (no LLM)
- [ ] **M1 LLM + Jev + LangSmith tests**
- [ ] **M2 Graph v1** (answer and abstain)
- [ ] **M3 Conflicts + replaced docs**
- [ ] **M4 Eval**
- [ ] **M5 Hardening + docs**

## Last verified outputs

- One test call to the Jev Decisions API (`typesafe/jev-1.13`) worked. The answer format matches
  the plan: `rel_D03` → `noul: 0.95`; `pair_D03_D04` → `disagree` with p = 1.0.
  Cost $0.0000226 (538 input, 67 output tokens).
- `openai/gpt-6-luna` is listed on OpenRouter at $0.10 / $0.50 per million tokens (in / out)
  and supports `response_format`, `structured_outputs` and `reasoning_effort`.

## Next step

M0: venv, requirements, `config.py`, the 20 documents, loader, embeddings, Qdrant index,
`main.py index|search|config`.

## Known issues

- No LangSmith key in `.env` yet, so tracing cannot be checked. Everything must work without it.

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | one Jev test call | 0.00002 |
| **total** | | **0.00002** |
