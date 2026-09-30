"""Command line for the Helios RAG demo. Run `python main.py -h` for the commands."""

import argparse
import json
import logging
import sys
import time

import config


def setup_logging() -> None:
    logging.basicConfig(level=config.LOG_LEVEL, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "httpx2", "httpcore", "openai", "urllib3", "huggingface_hub"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def cmd_config(args) -> None:
    for name, value in config.as_dict().items():
        print(f"{name:24} {value}")


def cmd_index(args) -> None:
    from src.vectorstore import ensure_index

    info = ensure_index(force=args.reindex)
    action = "Rebuilt" if info["rebuilt"] else "Reused"
    print(f"{action} collection '{config.QDRANT_COLLECTION}' ({config.QDRANT_MODE} mode): "
          f"{info['points']} points. Reason: {info['reason']}.")


def cmd_search(args) -> None:
    from src.vectorstore import ensure_index, retrieve, score_floor, search

    ensure_index()
    hits = search(args.question)
    floor = score_floor(hits[0]["score"]) if hits else config.SCORE_THRESHOLD
    print(f"Question: {args.question}")
    print(f"Search hits (top {config.TOP_K}; keep if score >= {floor:.4f}: cutoff "
          f"{config.SCORE_THRESHOLD}, margin {config.SCORE_MARGIN} below the best):")
    for hit in hits:
        mark = "keep" if hit["score"] >= floor else "drop"
        print(f"  {hit['score']:.4f}  {mark}  [{hit['doc_id']}] {hit['title']} "
              f"({hit['topic']}, {hit['date']})")
    result = retrieve(args.question)
    if not result["retrieved"]:
        print("Context: empty (no hit above the cutoff) -> would abstain.")
        return
    print(f"Context sent to the pipeline ({len(result['retrieved'])} docs, max "
          f"{config.MAX_CONTEXT_DOCS}):")
    for doc in result["retrieved"]:
        how = f"hit {doc['score']:.4f}" if doc["score"] is not None else "related"
        link = f", supersedes {doc['supersedes']}" if doc["supersedes"] else ""
        print(f"  [{doc['doc_id']}] {doc['title']} ({doc['topic']}, {doc['date']}{link}) - {how}")


def cmd_llm_test(args) -> None:
    from src.llm import USAGE, structured
    from src.load_docs import doc_map
    from src.prompts import extract_claims_messages
    from src.schemas import Claims
    from src.vectorstore import _to_retrieved

    question = "How many weeks of paid parental leave does Helios Dynamics offer?"
    docs = [_to_retrieved(doc_map()[i], None) for i in ("D03", "D04", "D13")]
    print(f"Model: {config.LLM_MODEL}  reasoning_effort: {config.LLM_REASONING_EFFORT or '-'}")
    print(f"Question: {question}")
    started = time.time()
    claims = structured(Claims, extract_claims_messages(question, docs))
    print(f"Time: {time.time() - started:.1f}s")
    for item in claims.claims:
        print(f"  [{item.doc_id}] {item.claim}")
    print(f"Tokens: {USAGE.input_tokens} in / {USAGE.output_tokens} out   cost: ${USAGE.llm_cost:.6f}")


def cmd_ask(args) -> None:
    from src.graph import run
    from src.render import show
    from src.vectorstore import ensure_index

    ensure_index()
    print(show(run(args.question, tags=["ask"])))


def load_questions() -> list[dict]:
    with open(config.QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def cmd_demo(args) -> None:
    from src.graph import run
    from src.render import show
    from src.vectorstore import ensure_index

    ensure_index()
    questions = [q for q in load_questions() if args.all or q.get("demo")]
    summary = []
    for q in questions:
        print(f"=== {q['id']} " + "=" * 90)
        state = run(q["question"], question_id=q["id"], tags=["demo"])
        print(show(state))
        got = state["result"]["status"]
        want = ("disputed" if q["expected"]["dispute"] else
                "abstained" if q["expected"]["no_answer"] else "answered")
        summary.append(f"  {q['id']}  {got:10} (expected {want})")
        print()
    print("Summary:")
    print("\n".join(summary))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Helios RAG demo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("config", help="print every setting (secrets hidden)").set_defaults(
        func=cmd_config)

    p = sub.add_parser("index", help="build or refresh the Qdrant collection")
    p.add_argument("--reindex", action="store_true", help="rebuild even if nothing changed")
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("search", help="retrieval test, no model calls")
    p.add_argument("question")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ask", help="run the full pipeline on one question")
    p.add_argument("question")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("demo", help="run the demo questions from questions.json")
    p.add_argument("--all", action="store_true", help="also run the extra questions")
    p.set_defaults(func=cmd_demo)

    sub.add_parser("llm-test", help="one structured-output call (Claims) through OpenRouter"
                   ).set_defaults(func=cmd_llm_test)
    return parser


def finish_run() -> None:
    """Print tokens and cost, add them to the running total, and send any queued traces."""
    from src.llm import USAGE, record_spend

    if USAGE.llm_calls:
        print()
        print(USAGE.summary())
        print(record_spend())
    flush_traces()


def flush_traces() -> None:
    """Send queued traces before a short command exits (only when tracing is on)."""
    if not config.TRACING_ON:
        return
    from langchain_core.tracers.langchain import wait_for_all_tracers

    wait_for_all_tracers()
    print(f"Traces sent to LangSmith project '{config.LANGSMITH_PROJECT}'.")


def known_errors() -> tuple[type[Exception], ...]:
    """Problems that get a one-line message instead of a long traceback."""
    from openai import APIError

    from src.llm import StructuredOutputError
    from src.load_docs import CorpusError
    from src.vectorstore import LockedStorageError

    return (LockedStorageError, StructuredOutputError, CorpusError, APIError)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    if config.TRACING_WARNING:
        print(f"WARNING: {config.TRACING_WARNING}", file=sys.stderr)
    code = 0
    try:
        args.func(args)
    except known_errors() as err:
        print(f"ERROR ({type(err).__name__}): {err}", file=sys.stderr)
        code = 2
    finally:
        finish_run()
    return code


if __name__ == "__main__":
    sys.exit(main())
