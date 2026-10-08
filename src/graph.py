"""The LangGraph pipeline.

retrieve -> extract_claims (LLM) -> compare (LLM) -> reconcile (Python rules)
         -> answer (LLM) | conflict_report (Python) | abstain (Python)

The LLM pulls out claims, says which claims answer the question and which pairs differ (and
what differs), and writes the final answer. It never decides which document is right: that is
decided here, in plain Python, from `supersedes` links only.
"""

import itertools
import logging
from functools import lru_cache
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

import config
from src.llm import structured
from src.load_docs import doc_map
from src.prompts import (answer_messages, check_answer_messages, compare_messages,
                         extract_claims_messages)
from src.render import render
from src.schemas import (Answer, AnswerCheck, Citation, Claims, Comparison, FinalOutput,
                         OutdatedNote)
from src.vectorstore import RetrievedDoc, retrieve as vector_retrieve

log = logging.getLogger(__name__)

NOT_SETTLED = "Neither document is marked as replacing the other; a newer date alone does not settle it."


class RAGInput(TypedDict):
    """What a run needs from outside. Studio shows this as the input form."""

    question: str


class RAGState(TypedDict, total=False):
    question: str
    retrieved: list[RetrievedDoc]
    closest: list[dict]  # top search hits before the cutoff: {doc_id, date, score}
    claims: dict[str, str | None]  # doc_id -> claim, or None if the doc says nothing
    relevance: dict[str, bool]  # doc_id -> does its claim answer the question (LLM)
    pairs: list[dict]  # {doc_a, doc_b, verdict: same | different | unrelated, what_differs}
    relevant_ids: list[str]  # relevant and current (not replaced)
    outdated: list[dict]  # {old_id, old_date, old_claim, new_id, new_date}
    disputes: list[dict]  # {doc_a, doc_b, description}
    route: Literal["answer", "conflict", "abstain"]
    answer_problems: list[str]  # what the check on the answer found (after the last try)
    result: dict | None  # FinalOutput.model_dump()
    output: str  # the result as text, the same as the CLI prints (easy to read in Studio)


# --- "replaces" links ------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _replaced_by() -> dict[str, str]:
    """old doc id -> id of the doc that replaces it, for the whole corpus."""
    return {doc.metadata["supersedes"]: doc_id
            for doc_id, doc in doc_map().items() if doc.metadata.get("supersedes")}


def newest_in_chain(doc_id: str) -> str:
    """Follow "replaced by" links to the end. Returns doc_id itself if nothing replaces it."""
    replaced_by = _replaced_by()
    seen = {doc_id}
    while doc_id in replaced_by and replaced_by[doc_id] not in seen:
        doc_id = replaced_by[doc_id]
        seen.add(doc_id)
    return doc_id


# --- steps -----------------------------------------------------------------------------------


def retrieve(state: RAGState) -> dict:
    return vector_retrieve(state["question"])


def _clean_id(value: str) -> str:
    """A doc id as the LLM wrote it, without brackets or spaces ("[D03]" -> "D03")."""
    return value.strip("[] ")


def _clean_claim(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if value.lower() in ("", "null", "none", "n/a", "no claim"):
        return None
    return value


def extract_claims(state: RAGState) -> dict:
    docs = state["retrieved"]
    out = structured(Claims, extract_claims_messages(state["question"], docs))
    by_id = {_clean_id(c.doc_id): _clean_claim(c.claim) for c in out.claims}
    return {"claims": {d["doc_id"]: by_id.get(d["doc_id"]) for d in docs}}


def pairs_to_compare(doc_ids: list[str]) -> list[tuple[str, str]]:
    """Every pair of these docs that are not replaced. A replaced doc can only be "outdated",
    so its verdicts would never be used; two docs that are not replaced are never in the same
    `supersedes` chain."""
    return list(itertools.combinations([i for i in doc_ids if newest_in_chain(i) == i], 2))


def read_comparison(out: Comparison, doc_ids: list[str],
                    pairs: list[tuple[str, str]]) -> tuple[dict, list[dict]]:
    """The LLM's answer as state: relevance per doc, and one verdict per listed pair.

    Pairs the LLM did not list, or listed twice, are handled here: a listed pair it left out
    counts as "unrelated" (logged), a pair that was not listed is ignored.
    """
    relevance = {i: False for i in doc_ids}
    for item in out.docs:
        if _clean_id(item.doc_id) in relevance:
            relevance[_clean_id(item.doc_id)] = item.relevant
    given = {frozenset((_clean_id(p.doc_a), _clean_id(p.doc_b))): p for p in out.pairs}
    result = []
    for a, b in pairs:
        p = given.get(frozenset((a, b)))
        if p is None:
            log.warning("The LLM did not compare %s and %s; counted as unrelated.", a, b)
        verdict = p.verdict if p else "unrelated"
        what = (p.what_differs or f"{a} and {b} give different answers") if verdict == "different" else None
        result.append({"doc_a": a, "doc_b": b, "verdict": verdict, "what_differs": what})
    return relevance, result


def compare(state: RAGState) -> dict:
    """The LLM says which claims answer the question and, for each pair, same or different."""
    claims = state["claims"]
    docs = [d for d in state["retrieved"] if claims.get(d["doc_id"])]
    if not docs:
        return {"relevance": {}, "pairs": []}
    ids = [d["doc_id"] for d in docs]
    pairs = pairs_to_compare(ids)
    out = structured(Comparison, compare_messages(state["question"], docs, claims, pairs))
    relevance, compared = read_comparison(out, ids, pairs)
    return {"relevance": relevance, "pairs": compared}


def reconcile(state: RAGState) -> dict:
    """Plain rules. This is where "outdated" and "disputed" are told apart."""
    claims = state.get("claims", {})
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    relevance = state.get("relevance", {})

    # 1. relevant = the LLM says its claim answers the question (only docs with a claim are asked)
    relevant = [i for i in by_id if relevance.get(i)]

    # 2. replaced docs move to "outdated"; only docs that are not replaced can answer. The newer
    #    doc answers only if the LLM found it relevant too: a newer doc that says nothing about
    #    the question cannot answer it, so then the result is "I don't know" with the note.
    current = [i for i in relevant if newest_in_chain(i) == i]
    outdated = [{"old_id": i, "old_date": by_id[i]["date"], "old_claim": claims[i],
                 "new_id": newest_in_chain(i), "new_date": doc_map()[newest_in_chain(i)].metadata["date"]}
                for i in relevant if newest_in_chain(i) != i]

    # 3. disputes: the LLM says two current docs give different answers
    disputes = [{"doc_a": p["doc_a"], "doc_b": p["doc_b"], "description": p["what_differs"]}
                for p in state.get("pairs", [])
                if p["verdict"] == "different" and p["doc_a"] in current and p["doc_b"] in current]

    # 4. route
    if not current:
        route = "abstain"
    elif disputes:
        route = "conflict"
    else:
        route = "answer"
    return {"relevant_ids": current, "outdated": outdated, "disputes": disputes, "route": route}


def _finish(state: RAGState, result: FinalOutput) -> dict:
    """What every last step writes: the result, and the same result as readable text."""
    data = result.model_dump()
    return {"result": data, "output": render(state["question"], data)}


def _citation(doc: RetrievedDoc, claims: dict) -> Citation:
    return Citation(doc_id=doc["doc_id"], date=doc["date"], source=doc["source"],
                    claim=claims.get(doc["doc_id"]) or "(no claim extracted)")


def find_citations(text: str, allowed: list[str]) -> tuple[list[str], list[str]]:
    """Doc ids written in the answer, in order: (allowed ones, ones that are not allowed)."""
    ids = sorted((i for i in doc_map() if i in text), key=text.index)
    return [i for i in ids if i in allowed], [i for i in ids if i not in allowed]


def with_agreeing(cited: list[str], pairs: list[dict], allowed: list[str]) -> list[str]:
    """The cited docs plus every allowed doc that the LLM called "same" as one of them.

    When documents agree, all of them are sources, even if the answer names only one.
    """
    result = list(cited)
    added = True
    while added:  # "same" links can chain: D10 = D18 and D18 = D30
        added = False
        for p in pairs:
            if p["verdict"] != "same":
                continue
            for a, b in ((p["doc_a"], p["doc_b"]), (p["doc_b"], p["doc_a"])):
                if a in result and b in allowed and b not in result:
                    result.append(b)
                    added = True
    return result


def answer(state: RAGState) -> dict:
    question, claims = state["question"], state["claims"]
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    allowed = state["relevant_ids"]
    docs = [by_id[i] for i in allowed]
    # The answer is written from the checked claims only, not from the full documents, so it can
    # only restate what was compared. A second LLM call then checks it against the claims and the
    # full documents.
    messages = answer_messages(question, docs, claims)

    for attempt in range(2):  # one more try if a citation is wrong or the check finds a problem
        text = structured(Answer, messages).answer.strip()
        cited, bad = find_citations(text, allowed)
        problems = structured(AnswerCheck, check_answer_messages(question, text, docs, claims)).problems
        if cited and not bad and not problems:
            break
        if attempt == 0:
            log.warning("Answer needs a fix (cited %s, not allowed %s, problems %s). "
                        "Asking once more.", cited, bad, problems)
            fix = []
            if not cited or bad:
                fix.append(f"Use only these document ids as citations: {', '.join(allowed)}.")
            if problems:
                fix.append("Fix these problems: " + " ".join(problems) + " Leave out anything the "
                           "claims do not state or the documents give differently.")
            messages = messages + [AIMessage(text), HumanMessage(" ".join(fix))]
    if not cited:
        why = "An answer was written but could not be tied to the documents, so it is not shown."
        return {"answer_problems": problems, **_abstain(state, why)}

    # still there after the retry: say so under the answer
    notes = []
    if problems:
        notes.append("Note: the check on this answer found: " + " ".join(problems))
    if bad:
        named = ", ".join(f"[{i}] (created {doc_map()[i].metadata['date']})" for i in bad)
        notes.append(f"Note: the answer also names {named}, which "
                     + ("is" if len(bad) == 1 else "are") + " not a current source for this question.")
    sources = with_agreeing(cited, state.get("pairs", []), allowed)
    result = FinalOutput(
        status="answered",
        answer=text,
        citations=[_citation(by_id[c], claims) for c in sources],
        outdated=[OutdatedNote(**o) for o in state.get("outdated", [])],
        reason=" ".join(notes) or None,
    )
    return {"answer_problems": problems, **_finish(state, result)}


def conflict_report(state: RAGState) -> dict:
    claims = state["claims"]
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    ids = list(dict.fromkeys(i for dsp in state["disputes"] for i in (dsp["doc_a"], dsp["doc_b"])))
    result = FinalOutput(
        status="disputed",
        versions=[_citation(by_id[i], claims) for i in ids],
        # the dates come from the metadata, the sentence from the LLM
        differences=[f"[{d['doc_a']}] (created {by_id[d['doc_a']]['date']}) vs [{d['doc_b']}] "
                     f"(created {by_id[d['doc_b']]['date']}): {d['description']}"
                     for d in state["disputes"]],
        outdated=[OutdatedNote(**o) for o in state.get("outdated", [])],
        reason=NOT_SETTLED,
    )
    return _finish(state, result)


def _abstain(state: RAGState, why: str) -> dict:
    """An "I don't know" with `why`, the closest documents and any outdated notes."""
    closest = ", ".join(f"{c['doc_id']} (created {c['date']}, score {c['score']:.3f})"
                        for c in state.get("closest", [])[:3])
    reason = why + (f" Closest documents: {closest}." if closest else "")
    result = FinalOutput(status="abstained", reason=reason,
                         outdated=[OutdatedNote(**o) for o in state.get("outdated", [])])
    return {"route": "abstain", **_finish(state, result)}


def abstain(state: RAGState) -> dict:
    if not state.get("retrieved"):
        best = state["closest"][0]["score"] if state.get("closest") else 0.0
        why = (f"No document is close enough to the question (best score {best:.3f}, "
               f"cutoff {config.SCORE_THRESHOLD}).")
    elif state.get("outdated"):
        why = ("Only replaced documents say something about it; the documents that replace them "
               "do not.")
    else:
        why = "None of the documents found says anything that answers the question."
    return _abstain(state, f"The documents do not answer this question. {why}")


# --- the graph -------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(RAGState, input_schema=RAGInput)
    for name, fn in [("retrieve", retrieve), ("extract_claims", extract_claims), ("compare", compare),
                     ("reconcile", reconcile), ("answer", answer),
                     ("conflict_report", conflict_report), ("abstain", abstain)]:
        g.add_node(name, fn)
    g.add_edge(START, "retrieve")
    g.add_conditional_edges(
        "retrieve", lambda s: "abstain" if not s["retrieved"] else "extract_claims",
        {"abstain": "abstain", "extract_claims": "extract_claims"})
    g.add_edge("extract_claims", "compare")
    g.add_edge("compare", "reconcile")
    g.add_conditional_edges("reconcile", lambda s: s["route"],
                            {"answer": "answer", "conflict": "conflict_report",
                             "abstain": "abstain"})
    for last in ("answer", "conflict_report", "abstain"):
        g.add_edge(last, END)
    return g.compile()


def run(question: str, question_id: str | None = None, tags: list[str] | None = None) -> RAGState:
    """Run the pipeline on one question. Returns the final state; the output is state["result"]."""
    return build_graph().invoke(
        {"question": question},
        config={"run_name": "ask", "tags": tags or ["demo"],
                "metadata": {"question_id": question_id, "llm": config.LLM_MODEL,
                             "dataset": config.DATASET}},
    )
