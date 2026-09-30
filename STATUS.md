# Status

Last update: 2026-09-30. The system works end to end on `main`: 40 documents, 34 eval questions,
34/34 PASS, 40 unit tests pass. Read `docs/architecture.md` for how it works. Detailed history of
every round is in the git log.

## What is done

- **Build (M-1 to M5):** corpus, config, Qdrant index and retrieval; LLM client; the LangGraph
  pipeline and `ask`; demo questions; `eval.py`; fallbacks and clear errors; README and docs.
- **Dispute round:** claims keep only the part that answers the question; the answer is written
  from the claims; questions where a disputed pair agrees on the point asked (Q11, Q13, Q14).
- **LangSmith and LangGraph Studio:** optional tracing and a LangSmith eval; `langgraph dev`
  with the graph `helios_rag`.
- **Simplification:** less code, same results (one structured-output method, no dead checks,
  related docs by topic from memory, fewer settings).
- **LLM-only judge:** Jev and the regex number check removed. The LLM compares the claims (same /
  different / unrelated, and what differs) and a second LLM call checks the answer.
- **Creation dates:** every document shown carries "created YYYY-MM-DD", added by code.
- **40 documents, 34 questions:** every case is covered at least twice (agree, disagree, three
  documents disagree, one document answers, no answer, a chain of three replaced documents,
  reworded questions, stopped at the search). Table in `docs/corpus.md`, "The cases".
- **Cite every agreeing document:** code adds every document the LLM marked `same`.
- **Answer only what is asked:** source lines show each claim as extracted, with no comment
  (`docs/decisions.md` 7).
- **Test coverage:** eval checks match whole words; unit tests for the rules, the eval checks,
  retrieval and the corpus.
- **Eval by outcome:** the output has `dispute` and `no_answer` flags. Disputes and "I don't
  know" are checked by the flags and the linked documents; one-answer questions by a reference
  answer and an LLM grader.
- **Retry fix:** OpenRouter sometimes answers HTTP 200 with an error inside; the client now
  waits and retries.
- **Merged into `main`** (2026-09-30) and checked there: one eval run, 34/34, flags right for all
  34, every output read by hand against the documents.
- **Docs cleanup:** obsolete history removed (the original plan, Jev material, old results);
  new pipeline diagram.

## Next steps

1. Decide and fix the "newer doc is silent" case (see Known issues), then add that question to
   the eval.
2. Optional: run the eval with another grader model (`EVAL_JUDGE_MODEL`) for a second opinion.

## Known issues

- If only a replaced document answers the question and the document that replaces it says
  nothing about it, the result is an answer that says the information is missing, with the
  source line "(no claim extracted)". Seen with "Is the HQ office open on weekends?" (D07
  answers, D08 replaces it and is silent). Cause: `reconcile` adds the newest document of a
  chain even when it has no claim.
- One model reads everything: there is no second opinion and no probability to tune, and it can
  answer differently from run to run. Run the eval twice after a change to a prompt, a threshold,
  a document or the model.
- The score cutoff cannot separate every off-topic question from an answerable one (off-topic
  questions reach 0.70). The LLM's relevance check is the real gate.
- Tested on this corpus and these questions only.

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | two probe calls by hand (Jev, gpt-6-luna) | 0.00004 |
| 2026-09-29 | all app runs, M1–M5 (from `.spend.json`, 40+ runs) | 0.01809 |
| 2026-09-29 | dispute check round: app runs (from `.spend.json`) | 0.01392 |
| 2026-09-29 | dispute check round: 3 test-script runs (not in `.spend.json`) | 0.00958 |
| 2026-09-29 | fresh eval + LangSmith round (traced tests, ask, two traced evals) | 0.01814 |
| 2026-09-29 | Studio setup: demo check + one run through the dev server | 0.00084 |
| 2026-09-29 | review, simplification and LLM-judge rounds: evals, demos, probe questions (from `.spend.json`) | 0.31426 |
| **total** | | **0.37487** |

Budget: $4.00. Left: about $3.63.
