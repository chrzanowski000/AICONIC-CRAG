# Evaluation

`python eval.py` runs every question in `questions.json` through the full pipeline and checks the
result. It needs no LangSmith account. It prints one PASS/FAIL line per question, a summary, and
the tokens and cost. It exits with code 1 if any question fails, so it can be used in a script.

```bash
python eval.py
```

The LLM can answer differently from one run to the next, so after a change to a prompt, a
threshold, a document or the model, run it twice; both runs must pass.

## The questions

34 questions. Q1–Q5 are the demo questions (`python main.py demo`); the rest are extra checks
(`python main.py demo --all` runs all of them without the checks). The `note` field in
`questions.json` says what each question tests.

| id | question | tests | expected |
|---|---|---|---|
| Q1 | How many approvals does a pull request need before it can be merged? | clean answer | `answered`; cites D14; contains "2" or "two" |
| Q2 | How many days per week can employees work remotely? | replaced doc | `answered`; cites D02; outdated D01 → D02; contains "3" or "three" |
| Q3 | How many weeks of paid parental leave does Helios Dynamics offer? | real dispute | `disputed`; D03 and D04, each with a date; no answer |
| Q4 | What is the daily meal allowance for business travel? | real dispute | `disputed`; D05 and D06, each with a date; no answer |
| Q5 | What is the policy on bringing pets to the office? | no answer | `abstained`; no answer, citations or versions |
| Q6 | What is the Kestrel X2 flight time? | replaced doc | `answered`; cites D10; outdated D09 → D10; contains "45" |
| Q7 | Where is the headquarters located? | replaced doc | `answered`; cites D08; outdated D07 → D08; contains "400 Meridian" |
| Q8 | How often do I need to change my password? | real dispute, in words not numbers | `disputed`; D11 and D12 |
| Q9 | How much does the Kestrel X2 weigh? | docs agree | `answered`; cites D10 **and** D18; contains "1.2" |
| Q10 | What is the maximum payload of the Kestrel X2? | docs agree | `answered`; cites D10 **and** D18; contains "300" |
| Q11 | Does parental leave cover adoption? | disputed pair agrees on the point asked | `answered`; cites D03 **and** D04; contains "adopt"; does **not** contain "16" or "12" |
| Q12 | Is multi-factor sign-in required? | docs agree | `answered`; cites D11 **and** D12; contains "required" or "yes" |
| Q13 | Can I split my parental leave? | disputed pair agrees on the point asked | `answered`; cites D03 **and** D04; contains "split", "block" or "yes"; does **not** contain "16" or "12" |
| Q14 | Do I keep my salary during parental leave? | disputed pair agrees on the point asked | `answered`; cites D03 **and** D04; contains "full" or "100%"; does **not** contain "16" or "12" |
| Q15 | What should I do during a Sev1 incident and who is on call? | docs add different facts (a question in two parts) | `answered`; cites D15 **and** D20 |
| Q16 | Do I keep my health insurance during parental leave? | only one doc answers | `answered`; cites D04; contains "yes" or "continue" |
| Q17 | How long must passwords be? | only one doc answers | `answered`; cites D11; contains "14" |
| Q18 | What are the HQ office opening hours? | replaced doc with the same value | `answered`; cites D08; outdated D07 → D08; contains "7:00" |
| Q19 | How often are company laptops replaced? | docs agree | `answered`; cites D21 **and** D22; contains "3" or "three" |
| Q20 | What is the yearly learning budget per employee? | real dispute, three documents | `disputed`; D23, D24 and D25, each with a date; no answer |
| Q21 | When do I need a doctor's note for sick leave? | only one doc answers | `answered`; cites D26; contains "three" or "3" |
| Q22 | How many days of annual leave do employees get per year? | chain of three replaced docs | `answered`; cites D29; outdated D27 → D29 and D28 → D29; contains "30" |
| Q23 | How long is the Kestrel X2 warranty? | three docs agree in different words ("12 months", "one year") | `answered`; cites D18, D30 **and** D31; contains "one year", "one-year", "12 months" or "1 year" |
| Q24 | How often does engineering ship a release? | real dispute, in words and days | `disputed`; D32 and D33 |
| Q25 | How long are customer support tickets kept? | real dispute | `disputed`; D34 and D35 |
| Q26 | Does Helios Dynamics pay for public transport to work? | only one doc answers | `answered`; cites D36; contains "100%", "yes" or "full" |
| Q27 | When is the summer party? | only one doc answers | `answered`; cites D37; contains "20 June" |
| Q28 | How long do I have to submit an expense claim? | docs agree | `answered`; cites D38 **and** D39; contains "30" |
| Q29 | Does Helios Dynamics offer a gym membership? | no answer, near a real topic (benefits) | `abstained` |
| Q30 | How many paid sick days do employees get per year? | no answer, near a real topic (sick leave) | `abstained` |
| Q31 | What is the dress code? | no answer, stopped at the search (no model call) | `abstained` at the search |
| Q32 | How long is maternity leave? | real dispute, question reworded | `disputed`; D03 and D04 |
| Q33 | Who needs to approve my PR? | only one doc answers, question reworded | `answered`; cites D14; contains "2" or "two" |
| Q34 | Who is the CEO of Helios Dynamics? | no answer, near a real topic (the company overview is found) | `abstained` |

The questions by case (details in `corpus.md`, "The cases"):

| case | questions |
|---|---|
| documents agree → answered, citing every agreeing document | Q9, Q10, Q12, Q19, Q23, Q28 |
| documents disagree → disputed | Q3, Q4, Q8, Q20 (three documents), Q24, Q25 |
| one document answers → answered | Q1, Q16, Q17, Q21, Q26, Q27 |
| no document answers → abstained | Q5, Q29, Q30, Q34 (after reading the documents); Q31 (stopped at the search) |
| replaced document → answered with an outdated note | Q2, Q6, Q7, Q18, Q22 (a chain of three) |
| disputed pair that agrees on what is asked → answered | Q11, Q13, Q14 |
| docs add different facts → answered | Q15 |
| question reworded | Q32 (dispute), Q33 (one document) |

Why so many "answered" questions: a system that shows a dispute every time two documents mention
different numbers would pass Q3, Q4 and Q8 easily. These questions check the other side: documents that agree,
documents that add different facts, and above all Q11, Q13 and Q14, where the two documents of a
real dispute (D03, D04) agree on what is asked. There the right result is an answer, and the
answer must not quietly state one side's number of weeks.

## The checks

All checks live in `eval.py`. Each one has the signature
`(inputs, outputs, reference_outputs) -> {"key", "score", "comment"}`, so the same functions are
used locally and as LangSmith evaluators. `reference_outputs` is the `expected` block of the
question in `questions.json`. A check that does not apply to a question scores 1 with the
comment `n/a`. A question passes only if every check scores 1.

| check | what it asks |
|---|---|
| `status_matches` | Is the status (`answered` / `disputed` / `abstained`) the expected one? |
| `cites_required_docs` | Are all docs in `cites` cited, and at least one doc in `cites_any`? Each citation has a date and a source. |
| `disputed_shows_both_sides` | For a dispute: at least 2 different versions (Q20 has 3), the required ones among them, each with a date and a claim, and **no** single answer. |
| `marks_outdated` | Is there an outdated note for each expected old → new pair, with both dates? |
| `abstained_cleanly` | For "I don't know": no answer, no citations, no versions. With `at_search`, it must also have stopped at the search (no document above the cutoff). The comment says where it stopped. |
| `answer_contains` | Does the answer contain one of the expected strings, as a whole word or number? |
| `answer_excludes` | Does the answer avoid all of these strings, as whole words or numbers (for example a number the documents disagree on)? |
| `answer_is_correct` | **The grader**: an LLM compares the whole output with the question's `reference_answer` and says `correct`, `partly correct` or `incorrect`, with a reason. Only `correct` passes. |

Words and numbers are matched whole (`mentions()` in `eval.py`): "2" is found in "needs 2
approvals" but not in "2025" or "[D12]", and "12" is not found in the date "2025-02-12". So
"contains" needs the full word ("adoption", not "adopt").

The first seven checks look at the structure of the output. A disputed question passes only when
the system refuses to give one answer; an unanswerable question passes only when the system says
nothing that looks like an answer. Guessing is never rewarded.

### The grader (`answer_is_correct`)

The structure checks cannot tell whether the answer is actually right. For that, every question
has a **reference answer** in `questions.json` (`expected.reference_answer`), written by hand from
the documents:

```json
{"id": "Q27", "question": "When is the summer party?",
 "expected": {"status": "answered", "cites": ["D37"], "answer_contains": ["20 June"],
              "reference_answer": "On Friday 20 June 2025 (D37). Also fine: from 16:00, at Pirita beach."}}
```

- For an answer, the reference holds the facts that answer the question. Details the question
  does not ask about go after "Also fine:": the answer may give them or leave them out (the
  system answers only what is asked).
- For a dispute, the reference names every version and says there is no single answer.
- For "I don't know", the reference says the documents do not answer.

The grader gets the question, the reference and the system's full printed output (answer, sources,
versions, notes), and decides:

| verdict | when |
|---|---|
| `correct` | same outcome as the reference (one answer / the documents disagree / "I don't know") and every key fact; nothing contradicts it; extra details that do not contradict are fine |
| `partly correct` | same outcome, but a key fact is missing |
| `incorrect` | a different outcome, a fact that contradicts the reference, or the answer picks one side of a disagreement |

Source lines quote the documents and are not claims of the answer: for Q14 D04's source line
says "12 weeks", but the answer itself does not, so it is `correct`.

Checked by hand before trusting it (2026-09-30), on outputs with a known verdict:

| output | grader said |
|---|---|
| Q3 dispute with both versions | correct |
| Q3 answered "16 weeks [D03]" (picks a side) | incorrect |
| Q14 answer on pay, D04's source line says 12 weeks | correct |
| Q14 answer "full salary for 12 weeks" | incorrect |
| Q5 invented "pets are allowed on Fridays" | incorrect |
| Q5 "I don't know" | correct |
| Q15 only the Sev1 part | partly correct |

The grader model is `EVAL_JUDGE_MODEL`, by default the same model as the system
(`openai/gpt-6-luna`). That is cheap, but a model grading output like its own can be too kind;
set another model (for example `EVAL_JUDGE_MODEL=z-ai/glm-5.3-flash python eval.py`) for a second
opinion. The grader adds one LLM call per question (34 per run).

## Unit tests

`python -m pytest` runs the tests in `tests/` (needs `requirements-dev.txt`). They make no model
calls, cost nothing and take about 2 seconds. They use the real corpus.

| file | what it checks |
|---|---|
| `tests/test_graph_rules.py` | the "replaces" chains; `reconcile` (replaced doc → outdated, a chain of three, `different` pair → dispute with the LLM's sentence, a three-way dispute, `same` → answer, a pair with a doc that is not relevant is ignored, nothing relevant → abstain, a dispute that also has an outdated note); which pairs are sent to the LLM; reading the LLM's comparison (pairs in any order, a left-out pair counts as unrelated); citing every agreeing document; finding citations in the answer; `conflict_report` and `abstain` show the creation dates |
| `tests/test_render.py` | every source line, every version of a dispute ("Both" or "All 3 versions"), "What differs" and the outdated note show "created YYYY-MM-DD"; "I don't know" has no sources |
| `tests/test_load_docs.py` | the real corpus loads; a missing `supersedes` target, a link across topics, a duplicate id, a bad date and a document that replaces itself are refused |
| `tests/test_eval_checks.py` | the eval's own checks: whole-word matching, citations (`cites` and `cites_any`), every version of a three-way dispute, outdated notes for a chain of three, "I don't know" at the search or after reading, contains / excludes |
| `tests/test_retrieval.py` | the score cutoff and the margin below the best hit |
| `tests/test_llm.py` | a reply that holds an error instead of an answer is retried, then stops with a clear error; other errors are not hidden |

The unit tests cover the plain-code rules. What the LLM says can only be checked by the eval.

## Results (2026-09-30, 40 documents, 34 questions)

With the grader (latest): one run **34/34 PASS**, one run **33/34** — Q15 was `partly correct`:
that answer described the incident steps and the on-call rotation but left out that a Sev1 alert
must be acknowledged within 15 minutes. That is a real gap in that answer, found only by the
grader; the answer step does not always cover both parts of a two-part question in full. It is
tracked in `STATUS.md`. The first grader runs also showed that some reference answers asked for
details the question did not ask about (pension, location, the Finance lead); those were moved
to "Also fine:". `python -m pytest`: 39 unit tests pass.

Before the grader: **34/34 PASS** on two runs in a row. One of those runs:

```
Q1  PASS  answered  ...; cited ['D14']; contains '2'
Q2  PASS  answered  ...; cited ['D02']; D01(2024-03-01)->D02(2025-06-15); contains 'three'
Q3  PASS  disputed  ...; versions ['D03', 'D04'], each with date and claim, no answer
Q4  PASS  disputed  ...; versions ['D05', 'D06'], each with date and claim, no answer
Q5  PASS  abstained ...; no answer, no citations, no versions (after reading the documents)
Q6  PASS  answered  ...; cited ['D10']; D09(2024-11-05)->D10(2025-07-20); contains '45'
Q7  PASS  answered  ...; cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '400 Meridian'
Q8  PASS  disputed  ...; versions ['D11', 'D12'], each with date and claim, no answer
Q9  PASS  answered  ...; cited ['D10', 'D18']; contains '1.2'
Q10 PASS  answered  ...; cited ['D10', 'D18']; contains '300'
Q11 PASS  answered  ...; cited ['D03', 'D04']; contains 'adoption'; avoids ['16', '12']
Q12 PASS  answered  ...; cited ['D11', 'D12', 'D13']; contains 'required'
Q13 PASS  answered  ...; cited ['D03', 'D04']; contains 'split'; avoids ['16', '12']
Q14 PASS  answered  ...; cited ['D03', 'D04']; contains '100%'; avoids ['16', '12']
Q15 PASS  answered  ...; cited ['D15', 'D20']
Q16 PASS  answered  ...; cited ['D04']; contains 'yes'
Q17 PASS  answered  ...; cited ['D11']; contains '14'
Q18 PASS  answered  ...; cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '7:00'
Q19 PASS  answered  ...; cited ['D21', 'D22']; contains '3'
Q20 PASS  disputed  ...; versions ['D23', 'D24', 'D25'], each with date and claim, no answer
Q21 PASS  answered  ...; cited ['D26']; contains 'three'
Q22 PASS  answered  ...; cited ['D29']; D27(2023-01-01)->D29(2025-01-01), D28(2024-01-01)->D29(2025-01-01); contains '30'
Q23 PASS  answered  ...; cited ['D18', 'D30', 'D31']; contains 'one year'
Q24 PASS  disputed  ...; versions ['D32', 'D33'], each with date and claim, no answer
Q25 PASS  disputed  ...; versions ['D34', 'D35'], each with date and claim, no answer
Q26 PASS  answered  ...; cited ['D36']; contains 'yes'
Q27 PASS  answered  ...; cited ['D37']; contains '20 June'
Q28 PASS  answered  ...; cited ['D38', 'D39']; contains '30'
Q29 PASS  abstained ...; no answer, no citations, no versions (after reading the documents)
Q30 PASS  abstained ...; no answer, no citations, no versions (after reading the documents)
Q31 PASS  abstained ...; no answer, no citations, no versions (at the search)
Q32 PASS  disputed  ...; versions ['D03', 'D04'], each with date and claim, no answer
Q33 PASS  answered  ...; cited ['D14']; contains 'two'
Q34 PASS  abstained ...; no answer, no citations, no versions (after reading the documents)
Summary: all passed.
LLM: 106 calls, 79785 in / 6911 out tokens. This run: $0.009428.
```

The check on the answer (see `pipeline.md`, step 5a) caught an answer about parental leave that
restated D04's "12 weeks" in one of the two runs; the second try was clean, so Q11–Q14 still
avoid "16" and "12".

## What the questions do not cover

- **A replaced document that is the only one to answer.** "Is the HQ office open on weekends?":
  D07 answers, D08 replaces it and says nothing about weekends. Today the result is an answer
  that says the information is missing, with D07 in the outdated note. The right result is not
  decided yet (see `STATUS.md`), so there is no question for it.
- **A replaced document and a dispute in the same question.** No documents in the corpus make
  this case; the rules handle it (the outdated note is shown with the dispute), and a unit test
  checks that, but no eval question does.

Earlier results (20 documents and 18 questions: Jev as judge, then the LLM as Jev's fallback,
then the LLM alone, all 18/18) are in `STATUS.md`.

## What this found, and what was fixed

The first version of the extra questions (before the fix) gave two wrong results out of 13:
"Does parental leave cover adoption?" and "Do I keep my salary during parental leave?" came out
`disputed`, although D03 and D04 agree on both points. The claims had pulled in the week counts
("covered by 16 weeks of fully paid parental leave"), so the judge saw a clash.
And once the claims were narrowed, the answer to the salary question still said "for the
full 16 weeks [D03]", because the answer step saw the full documents.

Fixes: claims keep only the part that answers the question; the comparison looks only at that
part; the answer is written from the claims, not from the full documents; and the answer is
checked for values the documents give differently (first by a regex number check, now by a
second LLM call). Q11, Q13 and Q14 (with
`answer_excludes`) keep this fixed.

## Does the eval catch a broken system?

Yes. Test (2026-09-29): the compare step was patched to call every pair `same`, so no dispute is
ever found, and Q3, Q4 and Q8 were run:

```
Q3  FAIL  answered  status_matches: expected disputed, got answered; ... a single answer was given
Q4  FAIL  answered  status_matches: expected disputed, got answered; ... a single answer was given
Q8  FAIL  answered  status_matches: expected disputed, got answered; ... a single answer was given
```

The answer step still did not pick a side. It wrote, for example, "The claims conflict: one says
16 weeks of fully paid parental leave [D03], while another says 12 weeks at full salary [D04]."
But that is free text from a model, with status `answered`, so the eval fails it on purpose. With
the normal pipeline, both versions with dates and "what differs" are shown by code every time.

## LangSmith (optional)

When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set, `eval.py` also:

1. reads the dataset `EVAL_DATASET_NAME` (default `rag-conflicts-demo`), or creates it from
   `questions.json` if it does not exist (inputs: `question`, `id`; outputs: the `expected`
   block);
2. runs `client.evaluate(...)` with the same eight checks as evaluators (the grader included), experiment prefix
   `rag-conflicts`, `max_concurrency=1` (one question at a time: the cost counter is not
   thread safe);
3. prints the experiment name and URL.

```bash
LANGSMITH_TRACING=true python eval.py
```

Every check should score 1 in the experiment. The graph runs are traced with
`run_name="ask"`, the tag `eval`, and metadata `question_id` and `llm`.

The dataset is created once. If you change `questions.json`, delete the dataset in LangSmith (or
set a new `EVAL_DATASET_NAME`) so it is created again.

First runs (2026-09-29, before Jev was removed):

| experiment | judge | runs | errors | feedback scores |
|---|---|---|---|---|
| `rag-conflicts-jev-4af5fc19` | Jev | 18 | 0 | 126 of 126 are 1 (7 checks × 18 questions) |
| `rag-conflicts-llm-07eb37b5` | LLM | 18 | 0 | 126 of 126 are 1 |

The first run created the dataset `rag-conflicts-demo` (18 examples); the second one reused it.
The local table passed 18/18 in both runs as well.

## Cost

One full eval (34 questions, 40 documents) costs about $0.009 to $0.012 with the LLM-only judge.
(With 18 questions it was $0.0056, and $0.003 with Jev, which used fewer LLM calls; the check on
the answer adds one call per answered question.) The
LangSmith eval runs the pipeline a second time, so it doubles that.
