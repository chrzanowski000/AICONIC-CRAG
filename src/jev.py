"""Jev, the decision model, through OpenRouter's Decisions API.

One call per question: a yes/no "is this doc relevant?" for every doc with a claim, and an
agree / disagree / unrelated choice for every pair of those docs that is not linked by
`supersedes`. Jev only returns probabilities; it never writes text.
"""

import itertools
import logging

import httpx
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import ValidationError

import config
from src.llm import USAGE
from src.schemas import JevDocument, JevQuestion, JevRequest, JevResponse, JevState

log = logging.getLogger(__name__)

PAIR_INSTRUCTIONS = (
    "Compare the claims of {a} and {b} as answers to the question. Different dates or sources "
    "do NOT make claims agree or disagree; only their content does."
)
PAIR_CRITERIA = {
    "agree": "Both give the same answer (same values or rules)",
    "disagree": "They give answers that cannot both be true (different numbers, names or rules)",
    "unrelated": "At least one does not answer the question",
}


class JevError(RuntimeError):
    """The Decisions API failed or returned something we cannot use."""


def build_request(question: str, docs: list[dict], linked: set[frozenset[str]]) -> JevRequest:
    """docs: [{id, source, date, claim}] (only docs with a claim). linked: pairs not to compare."""
    questions: dict[str, JevQuestion] = {}
    for doc in docs:
        questions[f"rel_{doc['id']}"] = JevQuestion(
            type="noul",
            instructions=(f"Does document {doc['id']} directly answer the question? "
                          f"Its claim: {doc['claim']}"),
        )
    for a, b in itertools.combinations([d["id"] for d in docs], 2):
        if frozenset((a, b)) in linked:
            continue
        questions[f"pair_{a}_{b}"] = JevQuestion(
            type="choice", instructions=PAIR_INSTRUCTIONS.format(a=a, b=b), criteria=PAIR_CRITERIA
        )
    return JevRequest(
        model=config.JEV_MODEL,
        state=JevState(question=question, documents=[JevDocument(**d) for d in docs]),
        questions=questions,
    )


@traceable(name="jev_judge", run_type="chain")
def call_jev(request: JevRequest) -> JevResponse:
    """One POST to the Decisions API. Raises JevError on any problem."""
    try:
        resp = httpx.post(
            config.JEV_URL,
            json=request.model_dump(exclude_none=True),
            headers={"Authorization": f"Bearer {config.LLM_API_KEY}",
                     "HTTP-Referer": config.LLM_HTTP_REFERER, "X-Title": config.LLM_APP_TITLE},
            timeout=config.JEV_TIMEOUT_S,
        )
    except httpx.HTTPError as err:
        raise JevError(f"request failed: {err!r}") from err
    if resp.status_code != 200:
        raise JevError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    try:
        parsed = JevResponse.model_validate_json(resp.content)
    except ValidationError as err:
        raise JevError(f"unexpected response format: {err}") from err
    missing = set(request.questions) - set(parsed.answers)
    if missing:
        raise JevError(f"answers missing for {sorted(missing)}")
    USAGE.add_jev(parsed.usage.cost)
    run = get_current_run_tree()
    if run is not None:
        run.add_metadata({"cost": parsed.usage.cost, "jev_model": parsed.model,
                          "questions": len(request.questions)})
    return parsed


def judge(question: str, docs: list[dict], linked: set[frozenset[str]]) -> dict:
    """Ask Jev. Returns {"relevance": {id: p}, "pairs": [{doc_a, doc_b, relation, p_disagree}]}."""
    request = build_request(question, docs, linked)
    response = call_jev(request)
    relevance: dict[str, float] = {}
    pairs: list[dict] = []
    for key, answer in response.answers.items():
        if key not in request.questions:
            continue
        if key.startswith("rel_"):
            if answer.noul is None:
                raise JevError(f"{key}: no probability in the answer")
            relevance[key[4:]] = float(answer.noul)
        elif key.startswith("pair_"):
            _, a, b = key.split("_", 2)
            probs = answer.probabilities or {}
            if answer.choice is None or "disagree" not in probs:
                raise JevError(f"{key}: no choice or probabilities in the answer")
            pairs.append({"doc_a": a, "doc_b": b, "relation": answer.choice,
                          "p_disagree": round(float(probs["disagree"]), 4)})
    return {"relevance": relevance, "pairs": pairs, "model": response.model}
