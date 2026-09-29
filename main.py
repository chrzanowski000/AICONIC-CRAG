"""Command line for the Helios RAG demo. Run `python main.py -h` for the commands."""

import argparse
import logging
import sys

import config


def setup_logging() -> None:
    logging.basicConfig(level=config.LOG_LEVEL, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "httpcore", "openai", "urllib3"):
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
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except Exception as err:  # show a short message instead of a long traceback
        from src.vectorstore import LockedStorageError

        if isinstance(err, LockedStorageError):
            print(f"ERROR: {err}", file=sys.stderr)
            return 2
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
