# Evaluation

`python eval.py` runs every question of the dataset (`data/larkfield/questions.json` by default)
through the full pipeline and checks the result. It needs no LangSmith account. It prints one PASS/FAIL line per question, a summary, and
the tokens and cost. It exits with code 1 if any question fails, so it can be used in a script.

```bash
python eval.py                        # Larkfield Motors, 20 questions (the default)
python eval.py --dataset helios       # Helios Dynamics, 34 questions
python eval.py --dataset brightwater  # Brightwater Ferries, 26 questions
```

This page describes the Helios questions. The Brightwater and Larkfield questions use the same
format and the same checks; their cases are listed in [`datasets.md`](datasets.md).

The LLM can answer differently from one run to the next, so after a change to a prompt, a
threshold, a document or the model, run it twice; both runs must pass.

## The questions

34 questions. Q1–Q5 are the demo questions (`python main.py --dataset helios demo`); the rest are
extra checks (`python main.py --dataset helios demo --all` runs all of them without the checks). The `note` field in
`data/helios/questions.json` says what each question tests.

| id | question | tests | expected |
|---|---|---|---|
| Q1 | How many approvals does a pull request need before it can be merged? | clean answer | one answer; cites D14; contains "2" or "two" |
| Q2 | How many days per week can employees work remotely? | replaced doc | one answer; cites D02; outdated D01 → D02; contains "3" or "three" |
| Q3 | How many weeks of paid parental leave does Helios Dynamics offer? | real dispute | `dispute: true`; D03 and D04, each with a date; no answer |
| Q4 | What is the daily meal allowance for business travel? | real dispute | `dispute: true`; D05 and D06, each with a date; no answer |
| Q5 | What is the policy on bringing pets to the office? | no answer | `no_answer: true`; no answer, citations or versions |
| Q6 | What is the Kestrel X2 flight time? | replaced doc | one answer; cites D10; outdated D09 → D10; contains "45" |
| Q7 | Where is the headquarters located? | replaced doc | one answer; cites D08; outdated D07 → D08; contains "400 Meridian" |
| Q8 | How often do I need to change my password? | real dispute, in words not numbers | `dispute: true`; D11 and D12 |
| Q9 | How much does the Kestrel X2 weigh? | docs agree | one answer; cites D10 **and** D18; outdated D09 → D10; contains "1.2" or "1.2kg" |
| Q10 | What is the maximum payload of the Kestrel X2? | docs agree | one answer; cites D10 **and** D18; outdated D09 → D10; contains "300" or "300g" |
| Q11 | Does parental leave cover adoption? | disputed pair agrees on the point asked | one answer; cites D03 **and** D04; contains "adoption", "adopted", "adopt" or "adopting"; does **not** contain "16" or "12" |
| Q12 | Is multi-factor sign-in required? | docs agree | one answer; cites D11 **and** D12; contains "required" or "yes" |
| Q13 | Can I split my parental leave? | disputed pair agrees on the point asked | one answer; cites D03 **and** D04; contains "split", "block" or "yes"; does **not** contain "16" or "12" |
| Q14 | Do I keep my salary during parental leave? | disputed pair agrees on the point asked | one answer; cites D03 **and** D04; contains "full" or "100%"; does **not** contain "16" or "12" |
| Q15 | What should I do during a Sev1 incident and who is on call? | docs add different facts (a question in two parts) | one answer; cites D15 **and** D20 |
| Q16 | Do I keep my health insurance during parental leave? | only one doc answers | one answer; cites D04; contains "yes" or "continue" |
| Q17 | How long must passwords be? | only one doc answers | one answer; cites D11; contains "14" |
| Q18 | What are the HQ office opening hours? | replaced doc with the same value | one answer; cites D08; outdated D07 → D08; contains "7:00" |
| Q19 | How often are company laptops replaced? | docs agree | one answer; cites D21 **and** D22; contains "3" or "three" |
| Q20 | What is the yearly learning budget per employee? | real dispute, three documents | `dispute: true`; D23, D24 and D25, each with a date; no answer |
| Q21 | When do I need a doctor's note for sick leave? | only one doc answers | one answer; cites D26; contains "three" or "3" |
| Q22 | How many days of annual leave do employees get per year? | chain of three replaced docs | one answer; cites D29; outdated D27 → D29 and D28 → D29; contains "30" |
| Q23 | How long is the Kestrel X2 warranty? | three docs agree in different words ("12 months", "one year") | one answer; cites D18, D30 **and** D31; contains "one year", "one-year", "12 months", "12-month", "1 year", "twelve months" or "a year" |
| Q24 | How often does engineering ship a release? | real dispute, in words and days | `dispute: true`; D32 and D33 |
| Q25 | How long are customer support tickets kept? | real dispute | `dispute: true`; D34 and D35 |
| Q26 | Does Helios Dynamics pay for public transport to work? | only one doc answers | one answer; cites D36; contains "100%", "yes" or "full" |
| Q27 | When is the summer party? | only one doc answers | one answer; cites D37; contains "20 June", "June 20", "June 20th" or "20th June" |
| Q28 | How long do I have to submit an expense claim? | docs agree | one answer; cites D38 **and** D39; contains "30" |
| Q29 | Does Helios Dynamics offer a gym membership? | no answer, near a real topic (benefits) | `no_answer: true` |
| Q30 | How many paid sick days do employees get per year? | no answer, near a real topic (sick leave) | `no_answer: true` |
| Q31 | Who won the football match last night? | no answer, stopped at the search (no model call) | `no_answer: true`, at the search |
| Q32 | How long is maternity leave? | real dispute, question reworded | `dispute: true`; D03 and D04 |
| Q33 | Who needs to approve my PR? | only one doc answers, question reworded | one answer; cites D14; contains "2", "two", "owns" or "owning" |
| Q34 | Who is the CEO of Helios Dynamics? | no answer, near a real topic (the company overview is found) | `no_answer: true` |

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
question in `questions.json` (its format is below). A check that does not apply to a question
scores 1 with the comment `n/a`. A question passes only if every check scores 1.

| check | what it asks |
|---|---|
| `outcome_matches` | Are the output's `dispute` and `no_answer` flags the expected ones? (both false = one answer) |
| `cites_required_docs` | Is every document in the expected `citations` cited? More are fine (agreeing documents are added). Each citation has a date and a source. |
| `dispute_links_right_docs` | For an expected dispute: the linked versions are **exactly** the expected `versions` (Q20 has 3), each with a date and a claim, and there is **no** answer. |
| `marks_outdated` | Is there an outdated note for each expected `outdated` pair (`old_id` → `new_id`), with both dates? |
| `no_answer_is_clean` | For an expected "I don't know": no answer, citations or versions. With `checks.at_search`, it must also have stopped at the search (no document above the cutoff). The comment says where it stopped. |
| `answer_contains` | Does the answer contain one of the strings in `checks.answer_contains`, as a whole word or number? |
| `answer_excludes` | Does the answer avoid all the strings in `checks.answer_excludes`, as whole words or numbers (for example a number the documents disagree on)? |
| `answer_is_correct` | Only for questions with one answer. **The grader**: an LLM compares the output with the expected `answer` (the correct answer) and says `correct`, `partly correct` or `incorrect`, with a reason. Only `correct` passes. |

Words and numbers are matched whole (`mentions()` in `eval.py`): "2" is found in "needs 2
approvals" but not in "2025" or "[D12]", and "12" is not found in the date "2025-02-12". So
"contains" needs the full word ("adoption", not "adopt").

The first seven checks look at the structure of the output. A disputed question passes only when
the system refuses to give one answer; an unanswerable question passes only when the system says
nothing that looks like an answer. Guessing is never rewarded.

### The expected block has the shape of the output

The `expected` block of a question uses the same field names as the system's output, so the two
can be read side by side (in LangSmith they line up in the compare view):

| field | in the output | in `expected` |
|---|---|---|
| `status` | `answered`, `disputed` or `abstained` | the same |
| `dispute`, `no_answer` | the two flags (both false = one answer) | the same |
| `answer` | the answer, with `[Dxx]` after each fact; `null` for a dispute or "I don't know" | the correct answer, short, in the same style; `null` for a dispute or "I don't know" |
| `citations`, `versions` | each document with `doc_id`, `date`, `source` and `claim` | `doc_id` only |
| `outdated` | `old_id`, `old_date`, `old_claim`, `new_id`, `new_date` | `old_id` and `new_id` only |
| `differences`, `reason` | written by the model or by code | left out |

`expected` leaves out what cannot be known before the run: the claims, "what differs" and the
reason are written by the model. Dates and sources come from the document metadata, and the
checks make sure every document shown has them. Empty lists are left out.

Rules that are not part of the output go in `checks`: `answer_contains`, `answer_excludes`,
`at_search` and `also_fine` (details the answer may give or leave out; see the grader below).

```json
{"id": "Q27", "question": "When is the summer party?",
 "expected": {"status": "answered", "answer": "On Friday 20 June 2025 [D37].",
              "citations": [{"doc_id": "D37"}], "dispute": false, "no_answer": false,
              "checks": {"answer_contains": ["20 June", "June 20", "June 20th", "20th June"],
                         "also_fine": "from 16:00, at Pirita beach."}}}
{"id": "Q20", "question": "What is the yearly learning budget per employee?",
 "expected": {"status": "disputed", "answer": null,
              "versions": [{"doc_id": "D23"}, {"doc_id": "D24"}, {"doc_id": "D25"}],
              "dispute": true, "no_answer": false}}
{"id": "Q31", "question": "Who won the football match last night?",
 "expected": {"status": "abstained", "answer": null, "dispute": false, "no_answer": true,
              "checks": {"at_search": true}}}
```

A unit test (`tests/test_load_docs.py`) makes sure every `expected` block keeps this shape: only
output field names plus `checks`, a `status` that agrees with the flags, and an `answer` only for
`answered`.

### How each outcome is checked

| expected | checked by |
|---|---|
| one answer | the flags; the cited documents; the grader compares the answer with the expected `answer` |
| a dispute | code only: `dispute` is true (`outcome_matches`), and the linked documents are exactly `versions` |
| no answer | code only: `no_answer` is true (`outcome_matches`) and nothing looks like an answer |

### The grader (`answer_is_correct`)

Only questions with one answer have an expected `answer`, and it is always one short answer: the
facts that answer the question, with `[Dxx]` after each fact as the system writes it. Details the
question does not ask about go in `checks.also_fine`; the output may give them or leave them out
(the system answers only what is asked).

The grader gets the question, the reference answer (the expected `answer`, then "Also fine: ..."
with `checks.also_fine` if there is one) and the system's full printed output, and decides:

| verdict | when |
|---|---|
| `correct` | it answers and gives every key fact of the reference answer; nothing contradicts it; extra details that do not contradict are fine |
| `partly correct` | it answers, but a key fact is missing |
| `incorrect` | a fact contradicts the reference answer, or the output does not answer (it says it does not know, or that the documents disagree) |

Source lines quote the documents and are not claims of the answer: for Q14 D04's source line
says "12 weeks", but the answer itself does not, so it is `correct`.

Checked by hand before trusting it (2026-09-30), on outputs with a known verdict:

| output | grader said |
|---|---|
| Q14 answer on pay, D04's source line says 12 weeks | correct |
| Q14 "the documents disagree about pay" | incorrect |
| Q27 "27 June 2025" (wrong date) | incorrect |
| Q27 "Friday 20 June 2025" (date only, no place) | correct |
| Q15 only the on-call rotation | partly correct |

The grader model is `EVAL_JUDGE_MODEL`, by default the same model as the system
(`openai/gpt-6-luna`). That is cheap, but a model grading output like its own can be too kind;
set another model (for example `EVAL_JUDGE_MODEL=z-ai/glm-5.3-flash python eval.py`) for a second
opinion. The grader adds one LLM call per question with one answer (22 per run).

## Unit tests

`python -m pytest` runs the tests in `tests/` (needs `requirements-dev.txt`). They make no model
calls, cost nothing and take about 2 seconds. They use the real corpus.

| file | what it checks |
|---|---|
| `tests/test_graph_rules.py` | the "replaces" chains; `reconcile` (replaced doc → outdated, a chain of three, `different` pair → dispute with the LLM's sentence, a three-way dispute, `same` → answer, a pair with a doc that is not relevant is ignored, nothing relevant → abstain, a dispute that also has an outdated note); which pairs are sent to the LLM; reading the LLM's comparison (pairs in any order, a left-out pair counts as unrelated); citing every agreeing document; finding citations in the answer; `conflict_report` and `abstain` show the creation dates |
| `tests/test_render.py` | every source line, every version of a dispute ("Both" or "All 3 versions"), "What differs" and the outdated note show "created YYYY-MM-DD"; "I don't know" has no sources |
| `tests/test_load_docs.py` | the real corpus loads; a missing `supersedes` target, a link across topics, a duplicate id, a bad date and a document that replaces itself are refused; every dataset's questions name real documents, and every `expected` block has the shape of the output |
| `tests/test_eval_checks.py` | the eval's own checks: whole-word matching, citations (more are fine, each with a date), every version of a three-way dispute, outdated notes for a chain of three, "I don't know" at the search or after reading, contains / excludes |
| `tests/test_retrieval.py` | the score cutoff and the margin below the best hit |
| `tests/test_llm.py` | a reply that holds an error instead of an answer is retried, then stops with a clear error; other errors are not hidden |

The unit tests cover the plain-code rules. What the LLM says can only be checked by the eval.

## Results (2026-09-30, on `main`)

`python eval.py --dataset helios`: **34/34 PASS**. The flags were right for all 34 (22 one answer, 7 disputes, 5
no answer), and every output was also read by hand against the documents. `python -m pytest`: 40
unit tests pass.

```
Q1  PASS  answered  cited ['D14']; contains '2'; correct
Q2  PASS  answered  cited ['D02']; D01(2024-03-01)->D02(2025-06-15); contains 'three'; correct
Q3  PASS  disputed  dispute: true, linked ['D03', 'D04'], each with date and claim
Q4  PASS  disputed  dispute: true, linked ['D05', 'D06'], each with date and claim
Q5  PASS  abstained no_answer: true, nothing that looks like an answer (after reading the documents)
Q6  PASS  answered  cited ['D10']; D09(2024-11-05)->D10(2025-07-20); contains '45'; correct
Q7  PASS  answered  cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '400 Meridian'; correct
Q8  PASS  disputed  dispute: true, linked ['D11', 'D12'], each with date and claim
Q9  PASS  answered  cited ['D10', 'D18']; contains '1.2'; correct
Q10 PASS  answered  cited ['D10', 'D18']; contains '300'; correct
Q11 PASS  answered  cited ['D03', 'D04']; contains 'adoption'; avoids ['16', '12']; correct
Q12 PASS  answered  cited ['D11', 'D12', 'D13']; contains 'required'; correct
Q13 PASS  answered  cited ['D03', 'D04']; contains 'split'; avoids ['16', '12']; correct
Q14 PASS  answered  cited ['D03', 'D04']; contains '100%'; avoids ['16', '12']; correct
Q15 PASS  answered  cited ['D15', 'D20']; correct
Q16 PASS  answered  cited ['D04']; contains 'yes'; correct
Q17 PASS  answered  cited ['D11']; contains '14'; correct
Q18 PASS  answered  cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '7:00'; correct
Q19 PASS  answered  cited ['D21', 'D22']; contains '3'; correct
Q20 PASS  disputed  dispute: true, linked ['D23', 'D24', 'D25'], each with date and claim
Q21 PASS  answered  cited ['D26']; contains 'three'; correct
Q22 PASS  answered  cited ['D29']; D27(2023-01-01)->D29(2025-01-01), D28(2024-01-01)->D29(2025-01-01); contains '30'; correct
Q23 PASS  answered  cited ['D18', 'D30', 'D31']; contains 'one year'; correct
Q24 PASS  disputed  dispute: true, linked ['D32', 'D33'], each with date and claim
Q25 PASS  disputed  dispute: true, linked ['D34', 'D35'], each with date and claim
Q26 PASS  answered  cited ['D36']; contains '100%'; correct
Q27 PASS  answered  cited ['D37']; contains '20 June'; correct
Q28 PASS  answered  cited ['D38', 'D39']; contains '30'; correct
Q29 PASS  abstained no_answer: true, nothing that looks like an answer (after reading the documents)
Q30 PASS  abstained no_answer: true, nothing that looks like an answer (after reading the documents)
Q31 PASS  abstained no_answer: true, nothing that looks like an answer (at the search)
Q32 PASS  disputed  dispute: true, linked ['D03', 'D04'], each with date and claim
Q33 PASS  answered  cited ['D14']; contains '2'; correct
Q34 PASS  abstained no_answer: true, nothing that looks like an answer (after reading the documents)
Summary: all passed.
LLM: 128 calls, 89724 in / 8044 out tokens. This run: $0.010989.
```

Run after the review clean-up (same day): **33/34**, flags right for all 34. Q14 failed
`answer_excludes`: the answer repeated D04's "12 weeks"; the answer check caught it on both tries,
so the answer was shown with a note, and the eval failed it as it should. This had passed in
about 10 runs before (see `STATUS.md`, Known issues).

The last word of each answered line is the grader's verdict. Q15 is graded with the current
reference answer: the run itself used an older reference that also asked for a "weekly"
rotation, which the question does not ask about; that word was removed and the same answer was
graded again.

## What the questions do not cover

- **A replaced document that is the only one to answer.** "Is the HQ office open on weekends?":
  D07 answers, D08 replaces it and says nothing about weekends. Today the result is an answer
  that says the information is missing, with D07 in the outdated note. The right result is not
  decided yet (see `STATUS.md`), so there is no question for it.
- **A replaced document and a dispute in the same question.** No documents in the corpus make
  this case; the rules handle it (the outdated note is shown with the dispute), and a unit test
  checks that, but no eval question does.

## Does the eval catch a broken system?

Yes. Test: the compare step was patched to call every pair `same`, so no dispute is ever found,
and Q3, Q4 and Q8 were run. All three failed: the output was one answer where a dispute was
expected, and no versions were linked.

The answer step still did not pick a side. It wrote, for example, "The claims conflict: one says
16 weeks of fully paid parental leave [D03], while another says 12 weeks at full salary [D04]."
But that is free text from a model, not a dispute with every version and its date, so the eval
fails it on purpose. With the normal pipeline, every version with its date and "what differs" is
shown by code every time.

## LangSmith (optional)

When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set, `eval.py` also:

1. reads the LangSmith dataset `rag-conflicts-<name>-<fingerprint>` of the dataset in use (for
   example `rag-conflicts-helios-536567d3`), or creates it from `data/<name>/questions.json` if
   it does not exist (inputs: `question`, `id`; outputs: the `expected`
   block, which has the shape of the output, so reference and output line up in the compare view;
   split: `one_answer`, `dispute` or `no_answer`, to filter by outcome in the UI);
2. runs `client.evaluate(...)` with the same eight checks as evaluators (the grader included),
   experiment prefix `rag-conflicts-<name>`, `max_concurrency=1` (one question at a time: the cost
   counter is not thread safe);
3. prints the experiment name and URL, and how many examples passed every check.

To run only an experiment on a LangSmith dataset that already exists (no local run, nothing
created), name it with `--langsmith-dataset`. Its questions must belong to `--dataset`, or the
run stops before any model call:

```bash
LANGSMITH_TRACING=true python eval.py --langsmith-dataset larkfield_small_reformated
LANGSMITH_TRACING=true python eval.py --dataset helios --langsmith-dataset rag-conflicts-helios-536567d3_reformated
```

```bash
LANGSMITH_TRACING=true python eval.py
LANGSMITH_TRACING=true python eval.py --dataset brightwater
```

The graph runs are traced with `run_name="ask"`, the tag `eval`, and metadata `question_id`,
`llm` and `dataset`. The dataset name ends with a short fingerprint of `questions.json`
(`rag-conflicts-helios-1a2b3c4d`), so a change to the questions or their expected results creates a
new dataset instead of grading against old examples. The old dataset is not deleted: it stays in
LangSmith as a copy, with its experiments.

## Cost

One full eval (34 questions, 40 documents, with the grader) costs about $0.011. The LangSmith
eval runs the pipeline a second time, so it doubles that.
