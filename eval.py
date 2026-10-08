"""Evaluation: run every question of a dataset (data/<name>/questions.json) and check it.

    python eval.py                        # local PASS/FAIL table, exit code 1 on any FAIL
    python eval.py --dataset brightwater  # the same for another dataset in data/
    LANGSMITH_TRACING=true python eval.py --langsmith-dataset larkfield_small_reformated
                                          # only a LangSmith experiment on an existing dataset

When LANGSMITH_TRACING=true and LANGSMITH_API_KEY is set, the same checks also run as a
LangSmith experiment on the LangSmith dataset rag-conflicts-<name>-<fingerprint>.

Every check has the signature (inputs, outputs, reference_outputs) -> {"key", "score", "comment"},
so the same functions work locally and as LangSmith evaluators. A check that does not apply to a
question scores 1 with the comment "n/a".

`reference_outputs` is the `expected` block of a question. It has the same shape as the output
(status, answer, citations, versions, outdated, dispute, no_answer), with documents named by
`doc_id` only, plus `checks`: rules that are not part of the output (answer_contains,
answer_excludes, at_search, also_fine).
"""

import argparse
import hashlib
import json
import sys
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

import config


def _result(key: str, ok: bool, comment: str) -> dict:
    return {"key": key, "score": 1 if ok else 0, "comment": comment}


def _na(key: str) -> dict:
    return {"key": key, "score": 1, "comment": "n/a"}


def outcome_matches(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """The output's `dispute` and `no_answer` flags are the expected ones (both false = one answer)."""
    want = (reference_outputs["dispute"], reference_outputs["no_answer"])
    got = (bool(outputs.get("dispute")), bool(outputs.get("no_answer")))
    names = {(False, False): "one answer", (True, False): "dispute", (False, True): "no answer"}
    return _result("outcome_matches", got == want,
                   f"expected {names.get(want, want)}, got {names.get(got, got)}")


def _ids(items: list[dict]) -> list[str]:
    return [i["doc_id"] for i in items or []]


def _checks(reference_outputs: dict) -> dict:
    return reference_outputs.get("checks") or {}


def cites_required_docs(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """Every expected citation is cited (more are fine: agreeing documents are added)."""
    key = "cites_required_docs"
    required = _ids(reference_outputs.get("citations"))
    if not required:
        return _na(key)
    citations = outputs.get("citations") or []
    cited = {c["doc_id"] for c in citations}
    missing = [d for d in required if d not in cited]
    undated = [c["doc_id"] for c in citations if not c.get("date") or not c.get("source")]
    if missing:
        return _result(key, False, f"missing citations {missing}; cited {sorted(cited)}")
    if undated:
        return _result(key, False, f"citations without date or source: {undated}")
    return _result(key, True, f"cited {sorted(cited)}")


def dispute_links_right_docs(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """For an expected dispute: the versions are exactly the expected documents, each with its
    date and claim, and there is no answer. (The `dispute` flag is checked by outcome_matches.)"""
    key = "dispute_links_right_docs"
    if not reference_outputs["dispute"]:
        return _na(key)
    versions = outputs.get("versions") or []
    ids = {v["doc_id"] for v in versions}
    want = set(_ids(reference_outputs.get("versions")))
    problems = []
    if ids != want:
        problems.append(f"linked {sorted(ids)}, expected {sorted(want)}")
    for v in versions:
        if not v.get("date") or not v.get("claim"):
            problems.append(f"{v['doc_id']} has no date or claim")
    if outputs.get("answer") is not None:
        problems.append("a single answer was given")
    if problems:
        return _result(key, False, "; ".join(problems))
    return _result(key, True, f"linked {sorted(ids)}, each with date and claim")


def marks_outdated(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "marks_outdated"
    required = [(o["old_id"], o["new_id"]) for o in reference_outputs.get("outdated") or []]
    if not required:
        return _na(key)
    notes = outputs.get("outdated") or []
    found = {(n["old_id"], n["new_id"]): n for n in notes}
    problems = []
    for old, new in required:
        note = found.get((old, new))
        if note is None:
            problems.append(f"no note {old}->{new}")
        elif not note.get("old_date") or not note.get("new_date"):
            problems.append(f"note {old}->{new} has no dates")
    if problems:
        return _result(key, False, "; ".join(problems))
    return _result(key, True, ", ".join(f"{o}({found[(o, n)]['old_date']})->{n}"
                                        f"({found[(o, n)]['new_date']})" for o, n in required))


def mentions(text: str, word: str) -> bool:
    """True if `word` is in `text` as a whole word or number, ignoring case.

    "2" is found in "needs 2 approvals" but not in "2025" or "[D12]"; "12" is not found in the
    date "2025-02-12"; "30" is found at the end of "within 30." and "100%" in "at 100% of".
    """
    text, word = text.lower(), word.lower()
    start = text.find(word)
    while start != -1:
        end = start + len(word)
        before, after = text[start - 1:start], text[end:end + 1]
        before2, after2 = text[max(start - 2, 0):max(start - 1, 0)], text[end + 1:end + 2]
        # a letter or digit next to it, or "12" in "2.12" / "02-12", joins it to a longer word
        joined_before = before.isalnum() or (before in (".", ",", ":", "-", "/") and before2.isdigit())
        joined_after = after.isalnum() or (after in (".", ",", ":", "-", "/") and after2.isdigit())
        if not joined_before and not joined_after:
            return True
        start = text.find(word, start + 1)
    return False


def no_answer_is_clean(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """For an expected "I don't know": no answer, sources or versions. With `at_search`, it must
    also have stopped at the search. (The `no_answer` flag is checked by outcome_matches.)"""
    key = "no_answer_is_clean"
    if not reference_outputs["no_answer"]:
        return _na(key)
    problems = []
    if outputs.get("answer"):
        problems.append("an answer was given")
    if outputs.get("citations"):
        problems.append("citations were given")
    if outputs.get("versions"):
        problems.append("versions were given")
    at_search = "No document is close enough" in (outputs.get("reason") or "")
    if _checks(reference_outputs).get("at_search") and not at_search:
        problems.append("expected to stop at the search, but documents were read")
    if problems:
        return _result(key, False, "; ".join(problems))
    where = "at the search" if at_search else "after reading the documents"
    return _result(key, True, f"nothing that looks like an answer ({where})")


def answer_contains(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "answer_contains"
    options = _checks(reference_outputs).get("answer_contains")
    if not options:
        return _na(key)
    answer = outputs.get("answer") or ""
    hit = [o for o in options if mentions(answer, o)]
    if hit:
        return _result(key, True, f"contains {hit[0]!r}")
    return _result(key, False, f"none of {options} in the answer")


def answer_excludes(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """The answer must not state these (for example a number the documents disagree on)."""
    key = "answer_excludes"
    banned = _checks(reference_outputs).get("answer_excludes")
    if not banned:
        return _na(key)
    answer = outputs.get("answer") or ""
    hit = [b for b in banned if mentions(answer, b)]
    if hit:
        return _result(key, False, f"answer states {hit}")
    return _result(key, True, f"avoids {banned}")


# --- the grader: an LLM compares the output with the reference answer -------------------------

GRADE = """\
You grade an answer written by a question-answering system that works from company documents.
You get the question, the correct answer written by a person, and the system's output. Decide:
- correct: the output answers the question and gives every key fact of the correct answer, and
  nothing in it contradicts the correct answer. Extra details that do not contradict it are fine.
- partly correct: it answers, but a key fact of the correct answer is missing.
- incorrect: a fact contradicts the correct answer, or the output does not answer (for example it
  says it does not know, or that the documents disagree).
The key facts are the facts in the correct answer that answer the question. The correct answer may
end with "Also fine: ...": those details are optional; the output may give them or leave them out.
Lines starting with "- [Dxx]" under "Sources" or "Outdated" quote the documents; details in them
are not claims of the answer.
Give the reason in one short sentence. Return only the structured object."""


class Grade(BaseModel):
    verdict: Literal["correct", "partly correct", "incorrect"]
    reason: str = Field(description="One short sentence")


def grade(question: str, output_text: str, reference: str) -> Grade:
    """Ask the grader model to compare the output with the reference answer."""
    from src.llm import structured

    return structured(Grade, [SystemMessage(GRADE), HumanMessage(
        f"Question: {question}\n\nReference answer: {reference}\n\nSystem output:\n{output_text}")],
        model=config.EVAL_JUDGE_MODEL)


def answer_is_correct(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """For a question with one answer: the grader says the output matches the expected answer
    (only "correct" passes). Disputes and "I don't know" are checked by their flags instead."""
    key = "answer_is_correct"
    reference = reference_outputs.get("answer")
    if not reference:
        return _na(key)
    also_fine = _checks(reference_outputs).get("also_fine")
    if also_fine:
        reference += f" Also fine: {also_fine}"
    from src.render import render

    verdict = grade(inputs["question"], render(inputs["question"], outputs), reference)
    return _result(key, verdict.verdict == "correct", f"{verdict.verdict}: {verdict.reason}")


CHECKS = [outcome_matches, cites_required_docs, dispute_links_right_docs, marks_outdated,
          no_answer_is_clean, answer_contains, answer_excludes, answer_is_correct]


def target(inputs: dict) -> dict:
    """Run the pipeline on one question. Returns the FinalOutput dict."""
    from src.graph import run

    state = run(inputs["question"], question_id=inputs.get("id"), tags=["eval"])
    return state["result"]


def run_local(questions: list[dict]) -> bool:
    print(f"Local eval: dataset {config.DATASET}, {len(questions)} questions, "
          f"model {config.LLM_MODEL}")
    all_ok = True
    for q in questions:
        outputs = target({"question": q["question"], "id": q["id"]})
        results = [check({"question": q["question"]}, outputs, q["expected"]) for check in CHECKS]
        failed = [r for r in results if r["score"] != 1]
        all_ok &= not failed
        if failed:
            reason = "; ".join(f"{r['key']}: {r['comment']}" for r in failed)
        else:
            reason = "; ".join(r["comment"] for r in results if r["comment"] != "n/a")
        print(f"{q['id']:3} {'PASS' if not failed else 'FAIL'}  {outputs['status']:9} "
              f"{reason}")
    passed = "all passed" if all_ok else "SOME FAILED"
    print(f"Summary: {passed}.")
    return all_ok


def outcome(expected: dict) -> str:
    return "dispute" if expected["dispute"] else "no_answer" if expected["no_answer"] else "one_answer"


def langsmith_dataset(client, questions: list[dict]) -> str:
    """The LangSmith dataset of these questions: reused if it exists, else created. Its name."""
    # The name ends with a fingerprint of the questions, so any change to questions.json gets a
    # new dataset instead of grading against old examples.
    fingerprint = hashlib.sha256(json.dumps(questions, sort_keys=True).encode()).hexdigest()[:8]
    name = f"{config.EVAL_DATASET_NAME}-{fingerprint}"
    if client.has_dataset(dataset_name=name):
        print(f"LangSmith: using dataset '{name}'.")
    else:
        dataset = client.create_dataset(name, description=f"RAG demo questions ({config.DATASET})")
        client.create_examples(dataset_id=dataset.id, examples=[
            {"inputs": {"question": q["question"], "id": q["id"]}, "outputs": q["expected"],
             "split": outcome(q["expected"])}  # to filter by outcome in the LangSmith UI
            for q in questions])
        print(f"LangSmith: created dataset '{name}' with {len(questions)} examples.")
    return name


def check_named_dataset(client, name: str, questions: list[dict]) -> None:
    """Stop unless the LangSmith dataset `name` exists and holds questions of the dataset in use
    (its questions are answered from this dataset's documents)."""
    if not client.has_dataset(dataset_name=name):
        raise SystemExit(f"No LangSmith dataset '{name}'.")
    ours = {q["question"] for q in questions}
    foreign = [e.inputs["question"] for e in client.list_examples(dataset_name=name)
               if e.inputs["question"] not in ours]
    if foreign:
        raise SystemExit(f"LangSmith dataset '{name}' has questions that are not in "
                         f"{config.QUESTIONS_FILE}, for example: {foreign[0]!r}. "
                         "Pick the matching --dataset.")


def run_langsmith(client, name: str) -> bool:
    """Run the checks as a LangSmith experiment on the LangSmith dataset `name`. Prints how many
    examples passed every check; True if all did."""
    results = client.evaluate(
        target,
        data=name,
        evaluators=CHECKS,
        experiment_prefix=config.EVAL_EXPERIMENT_PREFIX,
        max_concurrency=1,  # one question at a time (fewer rate limits)
        metadata={"llm": config.LLM_MODEL, "dataset": config.DATASET},
    )
    print(f"LangSmith experiment: {results.experiment_name} (LangSmith dataset '{name}')")
    if results.url:
        print(f"URL: {results.url}")
    rows = list(results)
    failed = [f"{row['example'].inputs.get('id')}: "
              + ", ".join(r.key for r in row["evaluation_results"]["results"] if r.score != 1)
              for row in rows if any(r.score != 1 for r in row["evaluation_results"]["results"])]
    print(f"LangSmith: {len(rows) - len(failed)}/{len(rows)} examples passed every check.")
    for line in failed:
        print(f"  FAIL {line}")
    return not failed


def main(argv: list[str] | None = None) -> int:
    from main import finish_run, known_errors, load_questions, setup_logging
    from src.graph import build_graph
    from src.vectorstore import ensure_index

    parser = argparse.ArgumentParser(description="Run the eval questions of one dataset.")
    parser.add_argument("--dataset", choices=config.datasets(),
                        help=f"which data/<name>/ to use (default: {config.DATASET})")
    parser.add_argument("--langsmith-dataset", metavar="NAME",
                        help="skip the local run; run only a LangSmith experiment on this existing "
                             "LangSmith dataset, whose questions must belong to --dataset "
                             "(needs LANGSMITH_TRACING=true)")
    args = parser.parse_args(argv)
    if args.dataset:
        config.use_dataset(args.dataset)
    setup_logging()
    if config.TRACING_WARNING:
        print(f"WARNING: {config.TRACING_WARNING}", file=sys.stderr)
    if args.langsmith_dataset and not config.TRACING_ON:
        print("ERROR: --langsmith-dataset needs LANGSMITH_TRACING=true and LANGSMITH_API_KEY.",
              file=sys.stderr)
        return 1
    ok = False
    try:
        ensure_index()
        build_graph()
        questions = load_questions()
        if args.langsmith_dataset:
            from langsmith import Client

            client = Client()
            check_named_dataset(client, args.langsmith_dataset, questions)
            ok = run_langsmith(client, args.langsmith_dataset)
        else:
            ok = run_local(questions)
            if config.TRACING_ON:
                from langsmith import Client

                client = Client()
                run_langsmith(client, langsmith_dataset(client, questions))
            else:
                print("LangSmith eval skipped (set LANGSMITH_TRACING=true and LANGSMITH_API_KEY "
                      "to run it).")
    except known_errors() as err:
        print(f"ERROR ({type(err).__name__}): {err}", file=sys.stderr)
    finally:
        finish_run()  # send queued traces, also when the run stops early
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
