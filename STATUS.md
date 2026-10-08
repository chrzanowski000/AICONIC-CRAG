# Status

Last update: 2026-10-08. The system works end to end: Helios has 40 documents and 35 eval questions,
35/35 PASS, and two more separate datasets, Brightwater Ferries (30 documents, 26 questions,
26/26 PASS) and Larkfield Motors (a factory: 28 documents, 20 questions, 20/20 PASS), with a
switch between them (`--dataset` or `DATASET`; default `larkfield`). 54 unit tests pass. Read `docs/architecture.md` for how it works. Detailed history of
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
- **Review clean-up** (branch `simplify-review`): `compare` only compares documents that are not
  replaced (fewer pairs, `same_chain` removed); the eval's dispute and no-answer checks no
  longer repeat the flag check (`outcome_matches` owns it); `best_score` and two filters that
  did nothing removed; the LangSmith dataset name now ends with a fingerprint of
  `questions.json`, so a change makes a new dataset (the old one still had the "status" format
  and would have failed every check). Checked: `pytest` 40 passed; one eval run 33/34 (Q14, see
  Known issues), flags right for all 34, all other outputs the same as on `main`. The LangSmith
  part was not run live. Merged into `main` (2026-09-30).
- **LangSmith dataset** `rag-conflicts-demo-536567d3` (2026-09-30): all 34 questions from
  `questions.json` with their expected results, split into `one_answer` (22), `dispute` (7) and
  `no_answer` (5). `LANGSMITH_TRACING=true python eval.py` uses it (the name ends with the
  fingerprint of `questions.json`). The old dataset `rag-conflicts-demo` (18 questions, old
  format) was deleted. Checked with a 4-question LangSmith run (Q1, Q3, Q5, Q31, experiment
  `rag-conflicts-smoke-1fb08e69`): all 8 checks scored 1 on each.
- **Second dataset** (2026-09-30): Helios moved to `data/helios/`
  (`corpus/`, `questions.json`); a new dataset `data/brightwater/` about Brightwater Ferries, 30
  documents and 26 questions covering every case (agree, disagree, three documents disagree,
  one document answers, no answer, a replaced document, a chain of three, reworded questions,
  stopped at the search). One setting, `DATASET` (default `helios`), or the flag `--dataset` on
  `main.py` and `eval.py`, picks the folder, the Qdrant collection (`<name>_docs`, with its own
  hash file) and the LangSmith dataset and experiment prefix (`rag-conflicts-<name>`). Traces
  carry `dataset` in their metadata. `QDRANT_COLLECTION`, `CORPUS_DIR`, `QUESTIONS_FILE`,
  `EVAL_DATASET_NAME` and `EVAL_EXPERIMENT_PREFIX` are no longer settings of their own.
  `llm-test` uses the first dispute question of the dataset. Docs: `docs/datasets.md`,
  decision 34. Checked: `pytest` 42 passed (a new test loads every dataset and checks that its
  questions name real documents); Brightwater eval run twice, 26/26 both times (the second with LangSmith: dataset `rag-conflicts-brightwater-3aaded38` created, experiment `rag-conflicts-brightwater-35ee8948`, every check 1 except Q15, which hit an OpenRouter rate limit in the LangSmith pass and got no output); Helios `demo` 5/5 on the new layout; `--dataset brightwater llm-test` works. Merged into `main` (2026-09-30).
- **LangSmith datasets rebuilt** (2026-10-01): the old datasets were gone (deleted in the UI,
  with their experiments). Both were created again from the question files, now with a split per
  outcome, made by code (`eval.langsmith_dataset`): `rag-conflicts-helios-536567d3` (34: 22
  `one_answer`, 7 `dispute`, 5 `no_answer`) and `rag-conflicts-brightwater-3aaded38` (26: 16, 5,
  5). No experiments yet.
- **Running docs** (2026-10-01): a step-by-step guide to switching datasets in
  `docs/datasets.md` (stop what uses `qdrant_data/`, pick the dataset, check which one is
  active, what happens by itself, Studio and the CLI at once). `docs/setup.md` has a short
  "Choosing the dataset" section, the Studio dataset note and more on server mode. The lock
  advice is fixed in the docs and in the `LockedStorageError` text: don't delete
  `qdrant_data/.lock` (the lock goes away when the program stops). `.env.example` shows
  `DATASET`. Checked: `pytest` 42 passed; `config` shows the right names; both indexes reused;
  the new error text shown with a second process holding the folder. No model calls.
- **Third dataset** (2026-10-01): `data/larkfield/`, Larkfield Motors, a
  factory that builds e-bike motors; the system advises people on the production line. 28
  documents and 20 questions, split 11 `one_answer`, 5 `dispute`, 4 `no_answer`. Every case is
  covered: agree (also three documents in different words), disagree (numbers, in words about a
  safety rule, three documents), one document answers, no answer (near real topics, and stopped
  at the search), a replaced document (also with the same value), a chain of three, a disputed
  pair that agrees on the point asked, reworded questions. No code change. Docs:
  `docs/datasets.md`. Checked: `pytest` 43 passed; `search` finds every expected document for
  all 20 questions; eval run twice, 20/20 both times (the second with LangSmith: dataset
  `rag-conflicts-larkfield-69cc59e5` created with the split, experiment
  `rag-conflicts-larkfield-b7ad4fdf`, all 8 checks scored 1 on all 20); outputs read by hand.
  One earlier try stopped at Q2 on an OpenRouter rate limit; `LLM_MAX_RETRIES=5` got through. Merged
  into `main` (2026-10-01); `pytest` 43 passed there.
- **Larkfield is the default dataset** (2026-10-01): `DATASET` now defaults to `larkfield`
  (`config.py`). Helios needs `--dataset helios` (or `DATASET=helios`). The unit tests still use
  Helios (`tests/conftest.py`). Docs updated: every place that named the default, and every Helios
  example command now has `--dataset helios`. CLAUDE.md: the "run the eval twice" rule now says
  on each dataset a change touches. Checked: `config` shows `larkfield`; `index` and `search` use
  `larkfield_docs`; `--dataset helios index` still works; `pytest` 43 passed. No model calls.
- **Expected outputs in the output's shape** (2026-10-01, branch `output-format`): the
  `expected` block of every question (80, all three datasets) now uses the output's field names:
  `status`, `answer` (short, `[Dxx]` after each fact, like the system writes), `citations` /
  `versions` (`doc_id` only), `outdated` (`old_id`, `new_id`), `dispute`, `no_answer`, plus
  `checks` for the test-only rules (`answer_contains`, `answer_excludes`, `at_search`,
  `also_fine`). So reference and output line up in LangSmith. The pipeline did not change. The
  eval checks read the new keys; `cites_any` (unused) is gone; a unit test keeps the shape in line
  with `FinalOutput`. New: `eval.py --langsmith-dataset <name>` runs only an experiment on an
  existing LangSmith dataset. LangSmith: the old datasets are kept; new copies
  `rag-conflicts-{helios-536567d3,brightwater-3aaded38,larkfield-69cc59e5}_reformated` and a
  small `larkfield_small_reformated` (Q1–Q5: 2 answers, 2 disputes, 1 no answer) were created;
  `rag-conflicts-helios-3da97895` was made by a stopped run. Checked: `pytest` 46 passed; the new
  checks pass on the 20 saved Larkfield outputs; eval on the new format: Helios 34/34 twice
  (the second with LangSmith), Brightwater 26/26 and Larkfield 20/20 once each (the second run
  was stopped). Not run yet: experiments on the `_reformated` and small datasets.
- **Short README** (2026-10-01, branch `output-format`): 126 lines instead of 186. The pipeline as
  an image (`docs/graph.png`, made from the diagram in `docs/pipeline.md`), a table of the 7 nodes,
  and the 5 `larkfield_small_reformated` questions as question vs reference vs real output (the
  2026-10-01 run). The Helios examples and long results moved out; they are in `docs/pipeline.md`
  and `docs/evaluation.md`.
- **Eval questions checked by hand** (2026-10-08, branch `eval-questions`): all 80 questions
  were checked against the full text of the documents, with search scores worked out locally.
  No expected outcome was wrong. Fixed the checks that could fail a correct answer or miss a
  wrong one:
  - Helios Q9 and Q10 now expect the D09 → D10 outdated note (as Q18 does for D07 → D08).
  - Helios Q15's reference no longer makes one detail of D15 or D20 a must.
  - Helios Q33's reference names who approves (one from the team that owns the code).
  - Helios Q31 is now an off-topic question (best score 0.469; "What is the dress code?" was
    0.571, too close to the 0.58 cutoff).
  - Brightwater Q13 no longer says "before it is worked" (D09 also allows approval after a late
    sailing), and Q21 no longer makes "dogs and cats" a must.
  - Wider `answer_contains` lists for common spellings: Helios Q9, Q10, Q23 and Q27, Brightwater
    Q19, and Larkfield Q2.
  Checked: `pytest` 46 passed; eval twice on each dataset, all passed (Larkfield 20/20, Helios
  34/34, Brightwater 26/26). One earlier Brightwater run failed Q10 (see Known issues).

- **Pipeline rules** (2026-10-08, branch `fix-pipeline-rules`), from a full review:
  - Doc ids the LLM writes with brackets (`[D04]`) in the compare step are now read right.
  - A newer document answers only if the LLM marked it relevant. If only a replaced document
    answers, the result is "I don't know" with the outdated note (new Helios Q35, "Is the HQ
    office open on weekends?").
  - The retry shows the model its first answer; ids that are not allowed and still there after
    the retry are named, with dates, in a note under the answer.
  - When the answer step gives up, the "I don't know" shows the closest documents and the
    outdated notes, and the route is `abstain`.
  - The 10-document cap never splits a topic, so both ends of a link and both sides of a dispute
    stay together.
  - Helios Q15's reference keeps only the two key facts; the details are "also fine".
  Checked: `pytest` 54 passed; eval twice on each dataset, all passed (Larkfield 20/20, Helios
  35/35, Brightwater 26/26).

## Next steps

1. Optional: run the eval with another grader model (`EVAL_JUDGE_MODEL`) for a second opinion.

## Known issues

- Q14 ("Do I keep my salary during parental leave?") can still repeat D04's "12 weeks": D04's
  claim keeps the whole sentence. The answer check catches it and asks again; if the second try
  still has it, the answer is shown with a note and the eval fails Q14. Seen once in about 11
  runs since the answer-prompt fix.
  **Root cause: the claim prompt** (`EXTRACT_CLAIMS` in `src/prompts.py`, and the `claim` field
  description in `src/schemas.py`) gives two instructions that pull against each other: "keep
  only the part that answers the question; leave out ... other numbers" and "copy numbers ...
  exactly as written". D04 says both facts in one sentence ("Employees receive 12 weeks of paid
  parental leave at full salary"). Doing both would mean rewriting it as "Leave is paid at full
  salary"; the model copies the sentence whole instead. The field description puts "numbers ...
  copied exactly as written" first, which makes this more likely. One rewording was tried (a
  colour/price example: rewrite without the extra details, copy exactly the values you keep);
  D04's claim still kept "12 weeks", so it was reverted. Not fixed yet.
- Brightwater Q10 ("When does car check-in close?") can miss D15 in the dispute: D15 says "car
  lanes close 20 minutes before departure", not "check-in", so the model sometimes treats it as
  not relevant. Seen once in 9 tries on 2026-10-08.
- One model reads everything: there is no second opinion and no probability to tune, and it can
  answer differently from run to run. Run the eval twice after a change to a prompt, a threshold,
  a document or the model.
- The score cutoff cannot separate every off-topic question from an answerable one (off-topic
  questions reach 0.70). The LLM's relevance check is the real gate.
- Tested on these three datasets and their questions only. The score cutoff and margin were
  chosen on Helios and worked unchanged on Brightwater and Larkfield.
- OpenRouter rate limits (an error inside an HTTP 200 reply) were frequent on 2026-09-30: two
  Brightwater eval runs stopped after the 2, 4, 8 s retries, and one run logged 111 retries.
  `LLM_MAX_RETRIES=5` (waits up to 32 s) got a full run through; one question still failed in its
  LangSmith pass.

## Money spent

| date | what | cost (USD) |
|---|---|---|
| 2026-09-29 | two probe calls by hand (Jev, gpt-6-luna) | 0.00004 |
| 2026-09-29 | all app runs, M1–M5 (from `.spend.json`, 40+ runs) | 0.01809 |
| 2026-09-29 | dispute check round: app runs (from `.spend.json`) | 0.01392 |
| 2026-09-29 | dispute check round: 3 test-script runs (not in `.spend.json`) | 0.00958 |
| 2026-09-29 | fresh eval + LangSmith round (traced tests, ask, two traced evals) | 0.01814 |
| 2026-09-29 | Studio setup: demo check + one run through the dev server | 0.00084 |
| 2026-09-29 | review, simplification and LLM-judge rounds: evals, demos, probe questions (from `.spend.json`) | 0.32907 |
| 2026-09-30 | second dataset: Brightwater evals (4 runs, 2 stopped early), Helios demo, llm-test (from `.spend.json`) | 0.02705 |
| 2026-10-01 | third dataset: Larkfield evals (3 runs, 1 stopped early; one with LangSmith) (from `.spend.json`) | 0.01919 |
| 2026-10-01 | expected-output format: evals on all three datasets, one Helios run with LangSmith, one stopped run (from `.spend.json`) | 0.05122 |
| 2026-10-08 | full review: eval on all three datasets, eval-question fixes (8 more eval runs), Q10 probes, llm-test (from `.spend.json`) | 0.12147 |
| 2026-10-08 | pipeline rules: eval twice on all three datasets, Helios Q15/Q35 runs, probes (from `.spend.json`) | 0.11595 |
| **total** | | **0.72456** |

Budget: $4.00. Left: about $3.28.
