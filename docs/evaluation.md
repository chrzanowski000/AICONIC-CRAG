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

18 questions. Q1–Q5 are the demo questions (`python main.py demo`); the rest are extra checks
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
| Q9 | How much does the Kestrel X2 weigh? | docs agree | `answered`; cites D10 or D18; contains "1.2" |
| Q10 | What is the maximum payload of the Kestrel X2? | docs agree | `answered`; cites D10 or D18; contains "300" |
| Q11 | Does parental leave cover adoption? | disputed pair agrees on the point asked | `answered`; cites D03 or D04; contains "adopt"; does **not** contain "16" or "12" |
| Q12 | Is multi-factor sign-in required? | docs agree | `answered`; cites D11 or D12; contains "required" or "yes" |
| Q13 | Can I split my parental leave? | disputed pair agrees on the point asked | `answered`; cites D03 or D04; does **not** contain "16" or "12" |
| Q14 | Do I keep my salary during parental leave? | disputed pair agrees on the point asked | `answered`; cites D03 or D04; contains "full" or "100%"; does **not** contain "16" or "12" |
| Q15 | What should I do during a Sev1 incident and who is on call? | docs add different facts | `answered`; cites D15 or D20 |
| Q16 | Do I keep my health insurance during parental leave? | only one doc answers | `answered`; cites D04 |
| Q17 | How long must passwords be? | only one doc answers | `answered`; cites D11; contains "14" |
| Q18 | What are the HQ office opening hours? | replaced doc with the same value | `answered`; cites D08; outdated D07 → D08; contains "7:00" |

Why Q9–Q18: a system that shows a dispute every time two documents mention different numbers
would pass Q3, Q4 and Q8 easily. These questions check the other side: documents that agree,
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
| `disputed_shows_both_sides` | For a dispute: at least 2 different versions, the required ones among them, each with a date and a claim, and **no** single answer. |
| `marks_outdated` | Is there an outdated note for each expected old → new pair, with both dates? |
| `abstained_cleanly` | For "I don't know": no answer, no citations, no versions. |
| `answer_contains` | Does the answer contain one of the expected strings? |
| `answer_excludes` | Does the answer avoid all of these strings (for example a number the documents disagree on)? |

The checks look at the structure of the output, not at the wording. A disputed question passes
only when the system refuses to give one answer; an unanswerable question passes only when the
system says nothing that looks like an answer. Guessing is never rewarded.

## Results (2026-09-29, LLM-only judge)

`python eval.py`: **18/18 PASS** on three runs in a row, exit code 0.

```
Q1  PASS  answered  ...; cited ['D14']; contains '2'
Q2  PASS  answered  ...; cited ['D02']; D01(2024-03-01)->D02(2025-06-15); contains 'three'
Q3  PASS  disputed  ...; versions ['D03', 'D04'], each with date and claim, no answer
Q4  PASS  disputed  ...; versions ['D05', 'D06'], each with date and claim, no answer
Q5  PASS  abstained ...; no answer, no citations, no versions
Q6  PASS  answered  ...; cited ['D10']; D09(2024-11-05)->D10(2025-07-20); contains '45'
Q7  PASS  answered  ...; cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '400 Meridian'
Q8  PASS  disputed  ...; versions ['D11', 'D12'], each with date and claim, no answer
Q9  PASS  answered  ...; cited ['D18']; contains '1.2'
Q10 PASS  answered  ...; cited ['D10']; contains '300'
Q11 PASS  answered  ...; cited ['D03', 'D04']; contains 'adopt'; avoids ['16', '12']
Q12 PASS  answered  ...; cited ['D11']; contains 'required'
Q13 PASS  answered  ...; cited ['D03', 'D04']; contains 'split'; avoids ['16', '12']
Q14 PASS  answered  ...; cited ['D03']; contains '100%'; avoids ['16', '12']
Q15 PASS  answered  ...; cited ['D15', 'D20']
Q16 PASS  answered  ...; cited ['D04']; contains 'yes'
Q17 PASS  answered  ...; cited ['D11']; contains '14'
Q18 PASS  answered  ...; cited ['D08']; D07(2024-09-01)->D08(2025-08-01); contains '7:00'
Summary: all passed.
LLM: 63 calls, 38989 in / 4199 out tokens. This run: $0.005611.
```

The check on the answer (see `pipeline.md`, step 5a) sometimes catches an answer about parental
leave that restates D04's "12 weeks"; the second try is clean, so Q11–Q14 still avoid "16" and
"12". In `demo --all` no correct answer got a note.

Earlier results (Jev as judge, then the LLM as Jev's fallback, both 18/18) are in `STATUS.md`.

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
2. runs `client.evaluate(...)` with the same seven checks as evaluators, experiment prefix
   `rag-conflicts`, `max_concurrency=1` (embedded Qdrant allows only one process, and one
   thread keeps it simple);
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

One full eval (18 questions) costs about $0.0056 with the LLM-only judge (it was $0.003 with Jev,
which used fewer LLM calls; the check on the answer adds one call per answered question). The
LangSmith eval runs the pipeline a second time, so it doubles that.
