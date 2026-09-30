# Status

Last update: 2026-09-30. All milestones of `docs/plan.md` are done, plus a round of fixes to
dispute detection and the LangSmith connection (see below). Latest: a simplification round on the
branch `simplification` (less code, same results, all evals pass). Then the branch `llm-judge`
(from `simplification`): the LLM does all judging; Jev and the regex number check are removed.
Then the branch `document-dates` (from `llm-judge`): every document shown carries its
creation date. Then the branch `more-documents` (from `document-dates`): 40 documents and 30
questions, covering every case. Latest: the branch `cite-all-agreeing` (from `more-documents`):
when documents agree, all of them are cited.

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
- [x] **Simplification** (branch `simplification`): remove code that is not needed, keep every
      result the same. Each step is checked with `pytest` and live runs. Python code 2026 → 1848
      lines; unit tests 26 → 37. Merge into `main` when reviewed.
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
    of such errors is shared by `main.py` and `eval.py`. `src/llm.py` 209 → 132 lines. Checked:
    `pytest` 34 passed; `llm-test` OK; bad model id → one-line error, exit 2; Jev made to fail →
    LLM judges, Q3 still DISPUTED; `eval.py` (Jev) 18/18 PASS.
  - Step 4, answer: the citations are the `Dxx` ids written in the answer text; the separate
    `citations` list in the `Answer` object is gone (two sources for one fact). The checks on the
    answer are one function, `check_answer`, with 3 unit tests; the "both values" note is built by
    `_numbers_note`. `src/quantities.py` gives `clashing_units` and `show_values`, so the "same
    unit, different number" rule is written once. Docs now describe the retry the way the code
    does it. Checked: `pytest` 37 passed; `eval.py` 18/18 PASS and `JUDGE=llm eval.py` 18/18 PASS.
  - Step 5, output: the CLI prints the `output` text that the last step already wrote, instead of
    rendering the result a second time. Checked: `pytest` 37 passed; `ask` (pets) → ABSTAINED.
  - Step 6, settings and copies: removed settings nobody changes: `LLM_PROVIDER_ORDER`,
    `EMBEDDING_BACKEND` (and the untested `huggingface` path), `EMBEDDING_DIM` (the size now comes
    from the model), `QDRANT_DISTANCE` (always cosine; the cutoffs assume it),
    `QDRANT_FORCE_REINDEX` (same as `index --reindex`), `EVAL_MAX_CONCURRENCY`. Kept
    `NUMERIC_BACKSTOP` (used in `docs/evaluation.md` to show what the number check adds).
    `eval.py` now uses `setup_logging`, `load_questions` and `finish_run` from `main.py` instead of
    its own copies; `finish_run` is in a `finally`, so an eval that stops early still records
    its cost. Checked: `pytest` 37 passed; fresh index built from nothing (20 points, reused on
    the next run); `eval.py` on it 18/18 PASS; an eval stopped with Ctrl-C after 20 s still added
    its $0.0007 to `.spend.json`.
  - Not done on purpose: renaming `JEV_RELEVANT_P` / `JEV_DISAGREE_P` (they apply to the LLM
    judge too, but the names are used in many notes and past commands); `llm-test` and
    `jev-test` stay (cheap checks that the key and both APIs work).
- [x] **LLM-only judge** (branch `llm-judge`): no Jev, no regex. The LLM compares the claims and
      says what differs; Python still applies `supersedes` links and picks the route.
  - Step 1: new `compare` step (one LLM call): relevance per doc, and for every pair not linked by
    `supersedes` a verdict (same / different / unrelated) plus, if different, one sentence with
    both values ("D03 says 16 weeks, D04 says 12 weeks"). That sentence is the dispute's
    description and is shown under "What differs:" in the dispute report. Removed: the Jev
    client (`src/jev.py`, `jev-test`, Jev schemas and settings, `httpx` pin), the `JUDGE`
    setting, the judge thresholds, and the number check between claims (`NUMERIC_BACKSTOP`).
    New unit tests for `pairs_to_compare` and `read_comparison` (a pair the LLM leaves out counts
    as unrelated and is logged). Checked: `pytest` 39 passed; `ask` Q3 and "How long is maternity
    leave?" → DISPUTED with "D03 says 16 weeks, D04 says 12 weeks"; Q9 → ANSWERED 1.2 kg;
    `eval.py` 18/18 PASS ($0.0047 per run, about the same as with Jev).
  - Step 2: the answer is checked by a second LLM call (`AnswerCheck`) instead of the regex. It
    gets the answer, the claims and the full text of the current docs, and lists (1) facts no
    claim states and (2) values the documents give differently. Problems → one more try with
    them as the fix; still there → the answer is kept with a note. Citations are found by looking
    for the known doc ids in the text (no regex). Removed: `src/quantities.py` and its 21 tests,
    `disputed_numbers`, `_numbers_note`. The first version of the check prompt also flagged
    "for the whole period" (no value) on Q14; the prompt now says only a written value counts.
    Checked: `pytest` 14 passed; by hand, the check flags "12 weeks" and an invented "company
    car", and passes a clean answer; Q14 asked twice → clean answer, no note; `eval.py` twice →
    18/18 PASS both times ($0.0056 per run); `demo --all` → no notes on any answer, one "12 weeks"
    leak caught and fixed on the second try.
  - Step 3, docs: `CLAUDE.md`, `README.md` and `docs/` describe the LLM-only pipeline
    (`compare`, the answer check, "What differs"); `docs/pipeline.md` has new real traces;
    `docs/decisions.md` records why Jev and the regex were removed; `docs/models.md` keeps the
    Jev comparison as history. New test of the eval itself: with the compare step patched to call
    every pair "same", Q3, Q4 and Q8 FAIL as they should (`docs/evaluation.md`).
- [x] **Creation dates everywhere** (branch `document-dates`): the frontmatter `date` is the day a
      document was created. It is now shown as "created YYYY-MM-DD" on every source line, on both
      versions of a dispute, in the outdated note, in the closest documents of "I don't know",
      and in each "What differs" line, which now starts with both ids and dates, added by code
      from the metadata: "[D03] (created 2025-01-10) vs [D04] (created 2025-02-20): D03 says 16
      weeks, D04 says 12 weeks." No model call changed. New `tests/test_render.py` (2 tests) and
      2 graph tests for `conflict_report` and `abstain`. Checked: `pytest` 18 passed; `demo` shows
      the dates on all three outcomes; `eval.py` 18/18 PASS.
- [x] **Docs refresh** (branch `document-dates`): the docs now describe the current system and
      focus on how it works. `docs/architecture.md` rewritten: the parts, one question start to
      finish, who does what (model vs code), modules and how a command flows through them, the
      output fields, settings, failure handling, tests. `docs/pipeline.md`: new "how the system
      tells the cases apart" table and "known limits". `docs/setup.md`: dev tools, first `ask`,
      error messages. `docs/evaluation.md`: unit tests section, full expectations, known limits
      of the checks. `docs/research.md`: design mapping updated for the LLM-only judge.
      `docs/corpus.md`: real word counts, the topic rule. `docs/plan.md`: marked as history.
      README and `CLAUDE.md`: reading order. Checked by a separate read of every doc against the
      code.
- [x] **40 documents, 30 questions** (branch `more-documents`): 20 new documents (D21–D40) and 12
      new questions (Q19–Q30), so every case is in the corpus at least twice (table in
      `docs/corpus.md`, "The cases"): documents agree (D21+D22 laptops, D38+D39 expense deadline,
      D18+D30+D31 warranty in different words), disagree (D23/D24/D25 learning budget, three
      sides; D32/D33 release cadence, in words; D34/D35 ticket retention), one document answers
      (D26 sick note, D36 public transport, D37 summer party), no document answers but close to a
      real topic (gym, paid sick days), and a chain of three replaced documents (D27 → D28 → D29
      annual leave). Three sentences were changed before the first run so they could not clash
      with existing documents (HQ hours, onboarding week, parking). A dispute with three
      versions now says "All 3 versions:" instead of "Both versions:" (new unit test).
      Checked: retrieval for the 18 old questions still finds their documents; `pytest` 19
      passed; `eval.py` twice → 30/30 PASS both times ($0.011 and $0.0085).
- [x] **Cite every agreeing document** (branch `cite-all-agreeing`): the sources of an answer are
      the documents it cites plus every allowed document that `compare` marked `same` as one of
      them (`with_agreeing` in `src/graph.py`, 2 unit tests). The eval now requires all agreeing
      documents for Q9–Q14, Q19, Q23, Q28 (`cites` instead of `cites_any`). Two prompt changes
      were needed, found by tracing the failures: (1) `compare` sometimes called a document that
      says the same rule in other words "unrelated" (D12 "stays switched on for all work
      systems" vs D11 "required for email, ..."); the prompt now says the same rule in other
      words or for a wider or narrower scope is `same`, and a detail the question does not ask
      about never makes a pair different. (2) With D04 now always relevant for Q14, the answer
      often restated D04's "12 weeks"; the answer prompt now says to leave out details the
      question does not ask about. Tried and reverted: asking the answer to cite every agreeing
      document (made the "12 weeks" leak worse; code does it instead) and rewording the claim
      prompt (D04's claim still keeps "12 weeks"). Checked: `pytest` 21 passed; traces of Q11
      and Q12 3 of 3 cite all agreeing documents, Q14 4 of 4 clean; final `eval.py` twice →
      30/30 PASS both times, no retries.

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

1. Review and merge the branch `cite-all-agreeing` into `main` (it holds `more-documents`,
   `document-dates`, `llm-judge` and `simplification` too).
2. Fix the "newer doc is silent" case (see Known issues) and add that question to the eval.
3. More eval questions: near-topic questions that must get "I don't know" (for example "How many
   weeks of paid parental leave do contractors get?"), a reworded dispute ("How long is
   maternity leave?"), and a stricter check for Q15 (both parts of the question). Match digits as
   whole words in `answer_contains` / `answer_excludes`. After changing `questions.json`, delete
   the LangSmith dataset `rag-conflicts-demo` so the next traced eval creates it again.

## Known issues

- A source line shows the document's whole claim. For Q14 (salary during parental leave) D04's
  claim keeps "12 weeks" ("Employees receive 12 weeks of paid parental leave at full salary"),
  so the answer is right but D04's source line shows one side of the weeks dispute.
- If only the replaced doc answers the question and the doc that replaces it says nothing about
  it, the result is ANSWERED with a non-answer ("the information does not say ... [D08]") and the
  source line "(no claim extracted)". Seen with "Is the HQ office open on weekends?" and "Where
  is the bike storage at HQ?" (D07 answers, D08 replaces it and is silent). Cause: `reconcile`
  adds the newest doc of a chain even when it has no claim.
- A question with two parts could lose one part without saying so: with Jev, "What should I do
  during a Sev1 incident and who is on call?" answered only the first part (D20 relevance 0.19).
  The LLM judge keeps D20 (Q15 cites D15 and D20), but the eval check for Q15 is still weak.
- One model judges everything: there is no second opinion and no probability to tune. The LLM
  can answer differently from run to run, so the eval is run twice after a change.
- **Changed from the plan** (all written down in `docs/decisions.md` and `docs/pipeline.md`):
  - retrieval cutoff 0.58 instead of 0.45, plus a new `SCORE_MARGIN` (0.10);
  - `JEV_RELEVANT_P` and `JEV_DISAGREE_P` 0.5 instead of 0.6;
  - `function_calling` does not use `with_structured_output` (it sent `parallel_tool_calls`,
    which made OpenRouter find no host);
  - the state has a `closest` field (for "I don't know"), and `judge_used` can be `none`;
  - running spend total in `.spend.json`;
  - Jev and the regex number check were removed; the LLM compares the claims and checks the
    answer (branch `llm-judge`).
- The score cutoff cannot separate every off-topic question from an answerable one (off-topic
  questions reach 0.70, answerable paraphrases go down to 0.62). The LLM's relevance check is
  the real gate; it rejected every off-topic doc in the tests.
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
| 2026-09-29 | review, simplification and LLM-judge rounds: evals, demos, probe questions (from `.spend.json`) | 0.18335 |
| **total** | | **0.24396** |

Budget: $4.00. Left: about $3.76.
