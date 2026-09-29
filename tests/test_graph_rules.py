"""Tests for the plain-Python rules in src/graph.py that use the real corpus (no model calls)."""

from src.graph import disputed_numbers, newest_in_chain, reconcile, same_chain
from src.load_docs import doc_map
from src.vectorstore import _to_retrieved


def _docs(*ids):
    """The fields of each document that the rules read."""
    return [{"doc_id": i, "topic": doc_map()[i].metadata["topic"], "text": doc_map()[i].page_content}
            for i in ids]


def test_disputed_numbers_finds_the_parental_leave_weeks():
    assert disputed_numbers(_docs("D03", "D04")) == {"week": {"D03": {16.0}, "D04": {12.0}}}


def test_disputed_numbers_finds_the_meal_allowance():
    assert disputed_numbers(_docs("D05", "D06")) == {"$": {"D05": {60.0}, "D06": {75.0}}}


def test_disputed_numbers_ignores_documents_that_agree():
    assert disputed_numbers(_docs("D10", "D18")) == {}  # both say 1.2 kg and 300 g


def test_replaces_chains():
    assert newest_in_chain("D01") == "D02"
    assert newest_in_chain("D02") == "D02"
    assert same_chain("D07", "D08")
    assert not same_chain("D03", "D04")  # a real dispute: no supersedes link


def _state(claims, relevance, pairs=()):
    """A state as the judge leaves it, for the docs in `claims` (real metadata, no model calls)."""
    return {"question": "q", "retrieved": [_to_retrieved(doc_map()[i], None) for i in claims],
            "claims": claims, "relevance": relevance, "pairs": list(pairs), "judge_used": "jev"}


def test_reconcile_moves_a_replaced_doc_to_outdated_even_when_the_numbers_differ():
    out = reconcile(_state({"D09": "38 minutes of flight time.", "D10": "45 minutes of flight time."},
                           {"D09": 0.9, "D10": 0.9}))
    assert out["route"] == "answer"
    assert out["relevant_ids"] == ["D10"]
    assert [(o["old_id"], o["new_id"]) for o in out["outdated"]] == [("D09", "D10")]
    assert out["disputes"] == []


def test_reconcile_keeps_a_dispute_the_judge_reports():
    pair = {"doc_a": "D03", "doc_b": "D04", "relation": "disagree", "p_disagree": 0.99}
    out = reconcile(_state({"D03": "16 weeks.", "D04": "12 weeks."}, {"D03": 0.9, "D04": 0.9}, [pair]))
    assert out["route"] == "conflict"
    assert [(d["doc_a"], d["doc_b"]) for d in out["disputes"]] == [("D03", "D04")]


def test_reconcile_number_check_finds_a_dispute_the_judge_missed():
    pair = {"doc_a": "D03", "doc_b": "D04", "relation": "agree", "p_disagree": 0.01}
    out = reconcile(_state({"D03": "16 weeks of leave.", "D04": "12 weeks of leave."},
                           {"D03": 0.9, "D04": 0.9}, [pair]))
    assert out["route"] == "conflict"
    assert "numeric mismatch" in out["disputes"][0]["description"]


def test_reconcile_answers_when_the_docs_agree():
    pair = {"doc_a": "D10", "doc_b": "D18", "relation": "agree", "p_disagree": 0.0}
    out = reconcile(_state({"D10": "It weighs 1.2 kg.", "D18": "The drone weighs 1.2 kg."},
                           {"D10": 0.9, "D18": 0.9}, [pair]))
    assert out["route"] == "answer"
    assert out["disputes"] == []


def test_reconcile_abstains_when_nothing_is_relevant():
    out = reconcile(_state({"D03": None, "D16": "11 public holidays."}, {"D16": 0.03}))
    assert out["route"] == "abstain"
    assert out["relevant_ids"] == []
