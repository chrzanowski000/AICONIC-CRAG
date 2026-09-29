"""Command line for the Helios RAG demo. Run `python main.py -h` for the commands."""

import argparse
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
    print(f"Model: {config.LLM_MODEL}  reasoning_effort: {config.LLM_REASONING_EFFORT or '-'}  "
          f"methods: {','.join(config.LLM_STRUCTURED_METHODS)}")
    print(f"Question: {question}")
    started = time.time()
    claims, method = structured(Claims, extract_claims_messages(question, docs))
    print(f"Method used: {method}   time: {time.time() - started:.1f}s")
    for item in claims.claims:
        print(f"  [{item.doc_id}] {item.claim}")
    print(f"Tokens: {USAGE.input_tokens} in / {USAGE.output_tokens} out   cost: ${USAGE.llm_cost:.6f}")


# A fixed state for jev-test: D03 and D04 disagree, TX agrees with D03, D16 is off topic.
JEV_TEST_QUESTION = "How many weeks of paid parental leave does Helios Dynamics offer?"
JEV_TEST_DOCS = [
    {"id": "D03", "source": "HR Handbook", "date": "2025-01-10",
     "claim": "Helios Dynamics offers 16 weeks of fully paid parental leave."},
    {"id": "D04", "source": "People Ops wiki", "date": "2025-02-20",
     "claim": "Employees receive 12 weeks of paid parental leave at full salary."},
    {"id": "TX", "source": "Test note", "date": "2025-03-01",
     "claim": "New parents get sixteen weeks of leave on full pay."},
    {"id": "D16", "source": "HR Handbook", "date": "2025-01-02",
     "claim": "In 2025 Helios Dynamics observes 11 public holidays."},
]
JEV_TEST_EXPECTED = {
    "rel_D03": "high", "rel_D04": "high", "rel_TX": "high", "rel_D16": "low",
    "pair_D03_D04": "disagree", "pair_D03_TX": "agree", "pair_D04_TX": "disagree",
    "pair_D03_D16": "unrelated", "pair_D04_D16": "unrelated", "pair_TX_D16": "unrelated",
}


def cmd_jev_test(args) -> None:
    from src.jev import build_request, call_jev

    request = build_request(JEV_TEST_QUESTION, JEV_TEST_DOCS, linked=set())
    print(f"Model: {config.JEV_MODEL}   URL: {config.JEV_URL}")
    print(f"Question: {JEV_TEST_QUESTION}   ({len(request.questions)} decision questions)")
    started = time.time()
    response = call_jev(request)
    print(f"Answered by {response.model} ({response.provider}) in {time.time() - started:.1f}s")
    ok = 0
    for key, expected in JEV_TEST_EXPECTED.items():
        ans = response.answers[key]
        if ans.type == "noul":
            got = "high" if ans.noul >= config.JEV_RELEVANT_P else "low"
            detail = f"p(yes)={ans.noul:.2f}"
        else:
            got = ans.choice
            probs = ", ".join(f"{k} {v:.2f}" for k, v in (ans.probabilities or {}).items())
            detail = f"{ans.choice} ({probs})"
        ok += got == expected
        print(f"  {'ok  ' if got == expected else 'MISS'} {key:14} expected {expected:9} got {detail}")
    usage = response.usage
    print(f"{ok}/{len(JEV_TEST_EXPECTED)} as expected. Tokens: {usage.input_tokens} in / "
          f"{usage.output_tokens} out   cost: ${usage.cost:.7f}")


def cmd_ask(args) -> None:
    from src.graph import run
    from src.render import show
    from src.vectorstore import ensure_index

    ensure_index()
    print(show(run(args.question, tags=["ask"])))


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

    sub.add_parser("llm-test", help="one structured-output call (Claims) through OpenRouter"
                   ).set_defaults(func=cmd_llm_test)
    sub.add_parser("jev-test", help="one Jev decision call on a fixed example"
                   ).set_defaults(func=cmd_jev_test)
    return parser


def finish_run() -> None:
    """Print tokens and cost, and add them to the running total, if any model was called."""
    from src.llm import USAGE, record_spend

    if USAGE.llm_calls or USAGE.jev_calls:
        print()
        print(USAGE.summary())
        print(record_spend())


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
        finish_run()
    except Exception as err:  # show a short message instead of a long traceback
        from src.vectorstore import LockedStorageError

        if isinstance(err, LockedStorageError):
            print(f"ERROR: {err}", file=sys.stderr)
            return 2
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
