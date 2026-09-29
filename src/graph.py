"""The LangGraph pipeline.

retrieve -> extract_claims (LLM) -> judge (Jev, or LLM) -> reconcile (Python rules)
         -> answer (LLM) | conflict_report (Python) | abstain (Python)

The LLM only pulls out claims and writes the final answer. Jev only returns probabilities.
Which document wins is decided here, in plain Python, from `supersedes` links only.
"""

import itertools
import logging
import re
from functools import lru_cache
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

import config
from src import jev
from src.llm import StructuredOutputError, plain, structured
from src.load_docs import doc_map
from src.prompts import answer_messages, assess_messages, extract_claims_messages
from src.schemas import Answer, Assessment, Citation, Claims, FinalOutput, OutdatedNote
from src.vectorstore import RetrievedDoc, retrieve as vector_retrieve

log = logging.getLogger(__name__)

NOT_SETTLED = "Neither document is marked as replacing the other; a newer date alone does not settle it."


class RAGState(TypedDict, total=False):
    question: str
    retrieved: list[RetrievedDoc]
    best_score: float
    closest: list[dict]  # top search hits before the cutoff: {doc_id, score}
    claims: dict[str, str | None]  # doc_id -> claim, or None if the doc says nothing
    judge_used: Literal["jev", "llm", "none"]  # "none": no doc had a claim, nothing to judge
    relevance: dict[str, float]  # doc_id -> p(relevant) (LLM judge: 1.0 / 0.0)
    pairs: list[dict]  # {doc_a, doc_b, relation, p_disagree}
    relevant_ids: list[str]  # relevant and current (not replaced)
    outdated: list[dict]  # {old_id, old_date, old_claim, new_id, new_date}
    disputes: list[dict]  # {doc_a, doc_b, description}
    route: Literal["answer", "conflict", "abstain"]
    result: dict | None  # FinalOutput.model_dump()


# --- "replaces" links ------------------------------------------------------------------------


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


def same_chain(a: str, b: str) -> bool:
    return newest_in_chain(a) == newest_in_chain(b)


# --- number check (backstop) ------------------------------------------------------------------

_WORD_NUMBERS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen twenty".split())}
_WORD_NUMBERS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90})
_SKIP_WORDS = {"of", "or", "and", "the", "to", "a", "an", "in", "on", "at", "for", "per", "up",
               "more", "less", "than", "fully", "full", "paid", "about", "only", "least"}
_QUANTITY = re.compile(
    r"(?P<cur>[$€£])?\s?(?P<num>\d+(?:[.,]\d+)?|\b(?:" + "|".join(_WORD_NUMBERS) + r")\b)"
    r"(?P<rest>(?:\s*%)?(?:[\s-]+[A-Za-z]+){0,3})",
    re.IGNORECASE,
)


def quantities(text: str) -> dict[str, set[float]]:
    """Numbers in a claim, grouped by what they count: {"$": {60.0}, "week": {16.0}}.

    The unit is the currency sign, "%", or the first real word after the number.
    """
    found: dict[str, set[float]] = {}
    for m in _QUANTITY.finditer(text or ""):
        raw = m.group("num").lower()
        value = float(_WORD_NUMBERS[raw]) if raw in _WORD_NUMBERS else float(raw.replace(",", "."))
        rest = m.group("rest") or ""
        if m.group("cur"):
            unit = m.group("cur")
        elif rest.strip().startswith("%"):
            unit = "%"
        else:
            words = [w for w in re.findall(r"[a-z]+", rest.lower()) if w not in _SKIP_WORDS]
            if not words:
                continue
            unit = words[0].rstrip("s") or words[0]
        found.setdefault(unit, set()).add(value)
    return found


def numbers_clash(a: str, b: str) -> str | None:
    """If both claims count the same thing with different numbers, say what differs."""
    qa, qb = quantities(a), quantities(b)
    for unit in sorted(set(qa) & set(qb)):
        if qa[unit] != qb[unit]:
            show = lambda vals: "/".join(f"{v:g}" for v in sorted(vals))  # noqa: E731
            return f"{show(qa[unit])} vs {show(qb[unit])} {unit}"
    return None


# --- steps -----------------------------------------------------------------------------------


def retrieve(state: RAGState) -> dict:
    return vector_retrieve(state["question"])


def _clean_claim(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if value.lower() in ("", "null", "none", "n/a", "no claim"):
        return None
    return value


def extract_claims(state: RAGState) -> dict:
    docs = state["retrieved"]
    ids = [d["doc_id"] for d in docs]
    try:
        out, _ = structured(Claims, extract_claims_messages(state["question"], docs))
        by_id = {c.doc_id.strip("[] "): _clean_claim(c.claim) for c in out.claims}
        claims = {i: by_id.get(i) for i in ids}
    except StructuredOutputError as err:
        log.warning("Claims could not be parsed (%s). Using the start of each doc instead.", err)
        claims = {d["doc_id"]: d["text"][:300] for d in docs}
    return {"claims": claims}


def _supersession_facts(docs: list[RetrievedDoc]) -> str:
    facts = [f"{d['doc_id']} replaces {d['supersedes']}" for d in docs if d.get("supersedes")]
    return "; ".join(facts)


def _judge_with_llm(question: str, docs: list[RetrievedDoc], claims: dict) -> dict:
    out, _ = structured(Assessment, assess_messages(question, docs, claims,
                                                    _supersession_facts(docs)))
    ids = {d["doc_id"] for d in docs}
    relevance = {d: 0.0 for d in ids}
    for item in out.docs:
        if item.doc_id in ids:
            relevance[item.doc_id] = 1.0 if item.relevant else 0.0
    pairs = []
    for c in out.conflicts:
        if c.doc_a in ids and c.doc_b in ids and c.doc_a != c.doc_b and not same_chain(c.doc_a, c.doc_b):
            pairs.append({"doc_a": c.doc_a, "doc_b": c.doc_b, "relation": "disagree",
                          "p_disagree": 1.0, "note": c.description})
    return {"relevance": relevance, "pairs": pairs}


def judge(state: RAGState) -> dict:
    claims = state["claims"]
    docs = [d for d in state["retrieved"] if claims.get(d["doc_id"])]
    if not docs:
        return {"judge_used": "none", "relevance": {}, "pairs": []}
    if config.JUDGE == "jev":
        linked = {frozenset((a["doc_id"], b["doc_id"]))
                  for a, b in itertools.combinations(docs, 2)
                  if same_chain(a["doc_id"], b["doc_id"])}
        jev_docs = [{"id": d["doc_id"], "source": d["source"], "date": d["date"],
                     "claim": claims[d["doc_id"]]} for d in docs]
        try:
            out = jev.judge(state["question"], jev_docs, linked)
            return {"judge_used": "jev", "relevance": out["relevance"], "pairs": out["pairs"]}
        except Exception as err:  # any failure of the alpha API: fall back, and say so
            if config.JUDGE_FALLBACK != "llm":
                raise
            log.warning("Jev failed (%s). The LLM judges instead.", str(err)[:300])
    elif config.JUDGE != "llm":
        raise ValueError(f"Unknown JUDGE '{config.JUDGE}'")
    out = _judge_with_llm(state["question"], docs, claims)
    return {"judge_used": "llm", **out}


def reconcile(state: RAGState) -> dict:
    """Plain rules. This is where "outdated" and "disputed" are told apart."""
    claims = state.get("claims", {})
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    relevance = state.get("relevance", {})

    # 1. relevant = the judge says so, and the doc has a claim
    relevant = [i for i in by_id if claims.get(i) and relevance.get(i, 0.0) >= config.JEV_RELEVANT_P]

    # 2. replaced docs move to "outdated"; the newest doc of each chain is forced in
    outdated, current = [], []
    for doc_id in relevant:
        newest = newest_in_chain(doc_id)
        if newest == doc_id:
            if doc_id not in current:
                current.append(doc_id)
            continue
        new_meta = doc_map()[newest].metadata
        outdated.append({"old_id": doc_id, "old_date": by_id[doc_id]["date"],
                         "old_claim": claims[doc_id], "new_id": newest,
                         "new_date": new_meta["date"]})
        if newest in by_id and newest not in current:
            current.append(newest)
    outdated_ids = {o["old_id"] for o in outdated}
    current = [i for i in current if i not in outdated_ids]

    # 3. disputes: the judge says the two current docs disagree
    disputes, seen = [], set()
    for pair in state.get("pairs", []):
        a, b = pair["doc_a"], pair["doc_b"]
        if (pair["p_disagree"] >= config.JEV_DISAGREE_P and a in current and b in current
                and not same_chain(a, b)):
            disputes.append({"doc_a": a, "doc_b": b,
                             "description": f"judge ({state.get('judge_used')}): disagree, "
                                            f"p={pair['p_disagree']:.2f}"})
            seen.add(frozenset((a, b)))

    # 4. number check: same topic, different numbers for the same thing, no dispute yet
    if config.NUMERIC_BACKSTOP:
        for a, b in itertools.combinations(current, 2):
            if frozenset((a, b)) in seen or same_chain(a, b):
                continue
            if by_id[a]["topic"] != by_id[b]["topic"]:
                continue
            clash = numbers_clash(claims.get(a) or "", claims.get(b) or "")
            if clash:
                disputes.append({"doc_a": a, "doc_b": b,
                                 "description": f"numeric mismatch (backstop): {clash}"})

    # 5. route
    if not current:
        route = "abstain"
    elif disputes:
        route = "conflict"
    else:
        route = "answer"
    return {"relevant_ids": current, "outdated": outdated, "disputes": disputes, "route": route}


def _citation(doc: RetrievedDoc, claims: dict) -> Citation:
    return Citation(doc_id=doc["doc_id"], date=doc["date"], source=doc["source"],
                    claim=claims.get(doc["doc_id"]) or "(no claim extracted)")


_DOC_ID = re.compile(r"\[(D\d{2})\]")


def answer(state: RAGState) -> dict:
    claims = state["claims"]
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    allowed = [i for i in state["relevant_ids"] if i in by_id]
    docs = [by_id[i] for i in allowed]
    messages = answer_messages(state["question"], docs)

    text, cited = None, []
    for attempt in range(2):  # one more try if no allowed citation is left
        try:
            out, _ = structured(Answer, messages)
            text, raw_cites = out.answer.strip(), [c.strip("[] ") for c in out.citations]
        except StructuredOutputError as err:
            log.warning("Answer could not be parsed (%s). Using plain text.", err)
            text = plain(messages).strip()
            raw_cites = []
        in_text = _DOC_ID.findall(text)
        bad = sorted({c for c in raw_cites + in_text if c not in allowed})
        cited = [c for c in dict.fromkeys(raw_cites + in_text) if c in allowed]
        if bad:
            log.warning("Answer cited documents that are not allowed: %s", bad)
        if cited and not bad:
            break
        if attempt == 0:
            log.warning("Asking once more for an answer with valid citations.")
            messages = messages + [HumanMessage(
                f"Use only these document ids as citations: {', '.join(allowed)}.")]
    if not cited:
        return {"result": FinalOutput(
            status="abstained",
            reason="An answer was written but could not be tied to the documents, so it is not shown.",
        ).model_dump()}

    result = FinalOutput(
        status="answered",
        answer=text,
        citations=[_citation(by_id[c], claims) for c in cited],
        outdated=[OutdatedNote(**o) for o in state.get("outdated", [])],
    )
    return {"result": result.model_dump()}


def conflict_report(state: RAGState) -> dict:
    claims = state["claims"]
    by_id = {d["doc_id"]: d for d in state["retrieved"]}
    ids = list(dict.fromkeys(i for dsp in state["disputes"] for i in (dsp["doc_a"], dsp["doc_b"])))
    result = FinalOutput(
        status="disputed",
        versions=[_citation(by_id[i], claims) for i in ids],
        outdated=[OutdatedNote(**o) for o in state.get("outdated", [])],
        reason=NOT_SETTLED,
    )
    return {"result": result.model_dump()}


def abstain(state: RAGState) -> dict:
    closest = ", ".join(f"{c['doc_id']} ({c['score']:.3f})" for c in state.get("closest", [])[:3])
    if not state.get("retrieved"):
        why = f"No document is close enough to the question (best score {state.get('best_score', 0):.3f}, cutoff {config.SCORE_THRESHOLD})."
    else:
        why = "None of the documents found says anything that answers the question."
    reason = f"The documents do not answer this question. {why}"
    if closest:
        reason += f" Closest documents: {closest}."
    return {"route": "abstain", "result": FinalOutput(status="abstained", reason=reason).model_dump()}


# --- the graph -------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def build_graph():
    g = StateGraph(RAGState)
    for name, fn in [("retrieve", retrieve), ("extract_claims", extract_claims), ("judge", judge),
                     ("reconcile", reconcile), ("answer", answer),
                     ("conflict_report", conflict_report), ("abstain", abstain)]:
        g.add_node(name, fn)
    g.add_edge(START, "retrieve")
    g.add_conditional_edges(
        "retrieve", lambda s: "abstain" if not s["retrieved"] else "extract_claims",
        {"abstain": "abstain", "extract_claims": "extract_claims"})
    g.add_edge("extract_claims", "judge")
    g.add_edge("judge", "reconcile")
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
                "metadata": {"question_id": question_id, "judge": config.JUDGE}},
    )
