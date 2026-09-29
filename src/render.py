"""Turn the pipeline output into terminal text."""

import textwrap

import config
from src.schemas import FinalOutput


def _wrap(text: str, first: str = "", rest: str = "") -> str:
    return textwrap.fill(text, width=100, initial_indent=first, subsequent_indent=rest)


def _source_line(c) -> str:
    return f"  - [{c.doc_id}] {c.source} ({c.date}): {c.claim}"


def render(question: str, result: dict) -> str:
    out = FinalOutput.model_validate(result)
    lines = [f"STATUS: {out.status.upper()}", f"Question: {question}"]
    if out.status == "answered":
        lines.append(_wrap(out.answer or ""))
        lines.append("Sources:")
        lines += [_source_line(c) for c in out.citations]
        if out.reason:
            lines.append(_wrap(out.reason))
    elif out.status == "disputed":
        lines.append("The sources disagree. Both versions:")
        lines += [_source_line(c) for c in out.versions]
        if out.differences:
            lines.append("What differs:")
            lines += [_wrap(d, first="  - ", rest="    ") for d in out.differences]
        lines.append(out.reason or "")
    else:
        lines.append(_wrap(f"I don't know. {out.reason or ''}"))
    if out.outdated:
        lines.append("Outdated:")
        for o in out.outdated:
            lines.append(_wrap(f'[{o.old_id}] ({o.old_date}) said: "{o.old_claim}" It is replaced '
                               f"by [{o.new_id}] ({o.new_date}).", first="  - ", rest="    "))
    return "\n".join(lines)


def render_trace(state: dict) -> str:
    """What each step decided. Shown with SHOW_SCORES=true, to tune the thresholds."""
    lines = ["--- trace ---"]
    retrieved = state.get("retrieved") or []
    if not retrieved:
        closest = ", ".join(f"{c['doc_id']} {c['score']:.3f}" for c in state.get("closest", []))
        lines.append(f"retrieve       nothing above the cutoff. closest: {closest}")
    else:
        docs = ", ".join(
            f"{d['doc_id']} {d['score']:.3f}" if d["score"] is not None else f"{d['doc_id']} (related)"
            for d in retrieved)
        lines.append(f"retrieve       {docs}")
    claims = state.get("claims")
    if claims is not None:
        for doc_id, claim in claims.items():
            lines.append(f"claim          {doc_id}: {claim}")
    if "relevance" in state:
        rel = ", ".join(f"{k} {'yes' if v else 'no'}" for k, v in state["relevance"].items()) or "-"
        lines.append(f"compare        relevant: {rel}")
        for p in state.get("pairs", []):
            what = f": {p['what_differs']}" if p["what_differs"] else ""
            lines.append(f"               pair {p['doc_a']}-{p['doc_b']}: {p['verdict']}{what}")
    if "route" in state:
        lines.append(f"reconcile      relevant (current): {state.get('relevant_ids') or '-'}  "
                     f"outdated: {[o['old_id'] + '->' + o['new_id'] for o in state.get('outdated', [])] or '-'}  "
                     f"route: {state['route']}")
        for d in state.get("disputes", []):
            lines.append(f"               dispute {d['doc_a']} vs {d['doc_b']}: {d['description']}")
    if "answer_problems" in state:
        lines.append(f"answer check   {'; '.join(state['answer_problems']) or 'no problems'}")
    return "\n".join(lines)


def show(state: dict) -> str:
    """What the CLI prints: the result text the last step wrote, plus the trace if asked for."""
    text = state["output"]
    if config.SHOW_SCORES:
        text += "\n" + render_trace(state)
    return text
