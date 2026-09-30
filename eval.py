"""Evaluation: run every question in questions.json and check the result.

    python eval.py                 # local PASS/FAIL table, exit code 1 on any FAIL

When LANGSMITH_TRACING=true and LANGSMITH_API_KEY is set, the same checks also run as a
LangSmith experiment on the dataset EVAL_DATASET_NAME.

Every check has the signature (inputs, outputs, reference_outputs) -> {"key", "score", "comment"},
so the same functions work locally and as LangSmith evaluators. A check that does not apply to a
question scores 1 with the comment "n/a".
"""

import sys

import config


def _result(key: str, ok: bool, comment: str) -> dict:
    return {"key": key, "score": 1 if ok else 0, "comment": comment}


def _na(key: str) -> dict:
    return {"key": key, "score": 1, "comment": "n/a"}


def status_matches(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    want, got = reference_outputs["status"], outputs.get("status")
    return _result("status_matches", got == want, f"expected {want}, got {got}")


def cites_required_docs(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """`cites`: every one of these must be cited. `cites_any`: at least one of these."""
    key = "cites_required_docs"
    required = reference_outputs.get("cites") or []
    any_of = reference_outputs.get("cites_any") or []
    if not required and not any_of:
        return _na(key)
    citations = outputs.get("citations") or []
    cited = {c["doc_id"] for c in citations}
    missing = [d for d in required if d not in cited]
    undated = [c["doc_id"] for c in citations if not c.get("date") or not c.get("source")]
    if missing:
        return _result(key, False, f"missing citations {missing}; cited {sorted(cited)}")
    if any_of and not cited & set(any_of):
        return _result(key, False, f"cites none of {any_of}; cited {sorted(cited)}")
    if undated:
        return _result(key, False, f"citations without date or source: {undated}")
    return _result(key, True, f"cited {sorted(cited)}")


def disputed_shows_both_sides(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "disputed_shows_both_sides"
    if reference_outputs["status"] != "disputed":
        return _na(key)
    versions = outputs.get("versions") or []
    ids = {v["doc_id"] for v in versions}
    problems = []
    if len(ids) < 2:
        problems.append(f"only {len(ids)} different versions")
    missing = [d for d in reference_outputs.get("versions", []) if d not in ids]
    if missing:
        problems.append(f"missing versions {missing}")
    for v in versions:
        if not v.get("date") or not v.get("claim"):
            problems.append(f"{v['doc_id']} has no date or claim")
    if outputs.get("answer") is not None:
        problems.append("a single answer was given")
    if problems:
        return _result(key, False, "; ".join(problems))
    return _result(key, True, f"versions {sorted(ids)}, each with date and claim, no answer")


def marks_outdated(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "marks_outdated"
    required = reference_outputs.get("outdated")
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


def abstained_cleanly(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "abstained_cleanly"
    if reference_outputs["status"] != "abstained":
        return _na(key)
    problems = []
    if outputs.get("status") != "abstained":
        problems.append(f"status is {outputs.get('status')}")
    if outputs.get("answer"):
        problems.append("an answer was given")
    if outputs.get("citations"):
        problems.append("citations were given")
    if outputs.get("versions"):
        problems.append("versions were given")
    at_search = "No document is close enough" in (outputs.get("reason") or "")
    if reference_outputs.get("at_search") and not at_search:
        problems.append("expected to stop at the search, but documents were read")
    if problems:
        return _result(key, False, "; ".join(problems))
    where = "at the search" if at_search else "after reading the documents"
    return _result(key, True, f"no answer, no citations, no versions ({where})")


def answer_contains(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    key = "answer_contains"
    options = reference_outputs.get("answer_contains")
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
    banned = reference_outputs.get("answer_excludes")
    if not banned:
        return _na(key)
    answer = outputs.get("answer") or ""
    hit = [b for b in banned if mentions(answer, b)]
    if hit:
        return _result(key, False, f"answer states {hit}")
    return _result(key, True, f"avoids {banned}")


CHECKS = [status_matches, cites_required_docs, disputed_shows_both_sides, marks_outdated,
          abstained_cleanly, answer_contains, answer_excludes]


def target(inputs: dict) -> dict:
    """Run the pipeline on one question. Returns the FinalOutput dict."""
    from src.graph import run

    state = run(inputs["question"], question_id=inputs.get("id"), tags=["eval"])
    return state["result"]


def run_local(questions: list[dict]) -> bool:
    print(f"Local eval: {len(questions)} questions, model {config.LLM_MODEL}")
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


def run_langsmith(questions: list[dict]) -> None:
    from langsmith import Client

    client = Client()
    name = config.EVAL_DATASET_NAME
    try:
        dataset = client.read_dataset(dataset_name=name)
        print(f"LangSmith: using dataset '{name}'.")
    except Exception:  # not found: create it from questions.json
        dataset = client.create_dataset(name, description="Helios RAG demo questions")
        client.create_examples(dataset_id=dataset.id, examples=[
            {"inputs": {"question": q["question"], "id": q["id"]}, "outputs": q["expected"]}
            for q in questions])
        print(f"LangSmith: created dataset '{name}' with {len(questions)} examples.")
    results = client.evaluate(
        target,
        data=name,
        evaluators=CHECKS,
        experiment_prefix=config.EVAL_EXPERIMENT_PREFIX,
        max_concurrency=1,  # one question at a time: the cost counter is not thread safe
        metadata={"llm": config.LLM_MODEL},
    )
    print(f"LangSmith experiment: {results.experiment_name}")
    if results.url:
        print(f"URL: {results.url}")


def main() -> int:
    from main import finish_run, known_errors, load_questions, setup_logging
    from src.graph import build_graph
    from src.vectorstore import ensure_index

    setup_logging()
    if config.TRACING_WARNING:
        print(f"WARNING: {config.TRACING_WARNING}", file=sys.stderr)
    ok = False
    try:
        ensure_index()
        build_graph()
        questions = load_questions()
        ok = run_local(questions)
        if config.TRACING_ON:
            run_langsmith(questions)
        else:
            print("LangSmith eval skipped (set LANGSMITH_TRACING=true and LANGSMITH_API_KEY "
                  "to run it).")
    except known_errors() as err:
        print(f"ERROR ({type(err).__name__}): {err}", file=sys.stderr)
    finally:
        finish_run()  # cost and traces, also when the run stops early
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
