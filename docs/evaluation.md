# Evaluation

`python eval.py` runs every question in `questions.json` through the full pipeline and checks the
result. It needs no LangSmith account. It prints one PASS/FAIL line per question, a summary, and
the tokens and cost. It exits with code 1 if any question fails, so it can be used in a script.

```bash
python eval.py                 # judge = Jev (default)
JUDGE=llm python eval.py       # judge = the LLM
```

## The questions

| id | question | expected |
|---|---|---|
| Q1 | How many approvals does a pull request need before it can be merged? | `answered`; cites D14; answer contains "2" or "two" |
| Q2 | How many days per week can employees work remotely? | `answered`; cites D02; outdated note D01 → D02 with both dates; answer contains "3" or "three" |
| Q3 | How many weeks of paid parental leave does Helios Dynamics offer? | `disputed`; versions include D03 and D04, each with a date; no answer |
| Q4 | What is the daily meal allowance for business travel? | `disputed`; versions include D05 and D06, each with a date; no answer |
| Q5 | What is the policy on bringing pets to the office? | `abstained`; no answer, no citations, no versions |
| Q6 (extra) | What is the Kestrel X2 flight time? | `answered`; cites D10; outdated note D09 → D10; answer contains "45" |
| Q7 (extra) | Where is the headquarters located? | `answered`; cites D08; outdated note D07 → D08; answer contains "400 Meridian" |

Q1–Q5 are the demo questions (`python main.py demo`). Q6 and Q7 are extra checks of the
"replaced document" rule. `python main.py demo --all` runs all seven without the checks.

## The checks

All checks live in `eval.py`. Each one has the signature
`(inputs, outputs, reference_outputs) -> {"key", "score", "comment"}`, so the same functions are
used locally and as LangSmith evaluators. `reference_outputs` is the `expected` block of the
question in `questions.json`. A check that does not apply to a question scores 1 with the
comment `n/a`. A question passes only if every check scores 1.

| check | what it asks |
|---|---|
| `status_matches` | Is the status (`answered` / `disputed` / `abstained`) the expected one? |
| `cites_required_docs` | Are the required documents cited, each with a date and a source? |
| `disputed_shows_both_sides` | For a dispute: at least 2 different versions, the required ones among them, each with a date and a claim, and **no** single answer. |
| `marks_outdated` | Is there an outdated note for each expected old → new pair, with both dates? |
| `abstained_cleanly` | For "I don't know": no answer, no citations, no versions. |
| `answer_contains` | Does the answer contain one of the expected strings? |

The checks look at the structure of the output, not at the wording. A disputed question passes
only when the system refuses to give one answer; an unanswerable question passes only when the
system says nothing that looks like an answer. Guessing is never rewarded.

## Results (2026-09-29)

`python eval.py`, judge Jev:

```
Q1  PASS  answered  (judge jev) expected answered, got answered; cited ['D14']; contains '2'
Q2  PASS  answered  (judge jev) ...; cited ['D02']; D01(2024-03-01)->D02(2025-06-15); contains 'three'
Q3  PASS  disputed  (judge jev) ...; versions ['D03', 'D04'], each with date and claim, no answer
Q4  PASS  disputed  (judge jev) ...; versions ['D05', 'D06'], each with date and claim, no answer
Q5  PASS  abstained (judge none) ...; no answer, no citations, no versions
Q6  PASS  answered  (judge jev) ...; cited ['D10']; D09(2024-11-05)->D10(2025-07-20); contains '45'
Q7  PASS  answered  (judge jev) ...; cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '400 Meridian'
Summary: all passed.
LLM: 11 calls, 7204 in / 630 out tokens, $0.001035. Jev: 6 calls, $0.000125. This run: $0.001161.
```

`JUDGE=llm python eval.py`: all 7 pass as well, exit code 0. 17 LLM calls, $0.00148.

Q5 shows `judge none`: no document had a claim about pets, so the judge was not called at all.

### Does the eval catch a broken system?

Yes. With the judge unable to report a dispute (`JEV_DISAGREE_P=1.01`) and the number check off
(`NUMERIC_BACKSTOP=false`), Q3 and Q4 fail and the exit code is 1:

```
Q3  FAIL  answered  (judge jev) status_matches: expected disputed, got answered;
          disputed_shows_both_sides: only 0 different versions; missing versions ['D03', 'D04'];
          a single answer was given
Q4  FAIL  answered  ...
Summary: SOME FAILED.
```

In that broken setup the LLM wrote, for Q3: *"Helios Dynamics' HR Handbook says employees receive
16 weeks of fully paid parental leave [D03]. Its Benefits FAQ says employees receive 12 weeks
... [D04]. Because the documents give different amounts, the current entitlement cannot be
determined."* That is a decent answer, but it is luck, not design: the status says `answered`,
the dates are missing, and nothing makes the model do this every time. The checks count it as a
failure on purpose. With the rules on, both versions with dates are shown by code every time.

With only the judge switched off (`JEV_DISAGREE_P=1.01`, number check on), Q3 and Q4 still pass:
the number check finds "16 vs 12 week" and "60 vs 75 $".

## LangSmith (optional)

When `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` are set, `eval.py` also:

1. reads the dataset `EVAL_DATASET_NAME` (default `rag-conflicts-demo`), or creates it from
   `questions.json` if it does not exist (inputs: `question`, `id`; outputs: the `expected`
   block);
2. runs `client.evaluate(...)` with the same six checks as evaluators, experiment prefix
   `rag-conflicts-<judge>`, `max_concurrency=1` (embedded Qdrant allows only one process, and one
   thread keeps it simple);
3. prints the experiment name and URL.

Every check should score 1 in the experiment. The graph runs are traced with
`run_name="ask"`, the tag `eval`, and metadata `question_id` and `judge`; the Jev call shows up as
a `jev_judge` run with its cost in the metadata.

The dataset is created once. If you change `questions.json`, delete the dataset in LangSmith (or
set a new `EVAL_DATASET_NAME`) so it is created again.

Status: this part is written against the langsmith 0.14.1 API but has **not been run yet**,
because no LangSmith key was available. See `STATUS.md`.

## Cost

One full eval (7 questions) costs about $0.0012 with Jev and $0.0015 with the LLM judge. The
LangSmith eval runs the pipeline a second time, so it doubles that.
