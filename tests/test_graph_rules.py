"""Tests for the plain-Python rules in src/graph.py that use the real corpus (no model calls)."""

from src.graph import (check_answer, disputed_numbers, newest_in_chain, pairs_to_compare,
                       read_comparison, reconcile, same_chain)
from src.load_docs import doc_map
from src.schemas import Comparison, DocAssessment, PairComparison
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


def _state(claims, relevant, pairs=()):
    """A state as `compare` leaves it, for the docs in `claims` (real metadata, no model calls)."""
    return {"question": "q", "retrieved": [_to_retrieved(doc_map()[i], None) for i in claims],
            "claims": claims, "relevance": {i: i in relevant for i in claims},
            "pairs": list(pairs)}


def _pair(a, b, verdict, what=None):
    return {"doc_a": a, "doc_b": b, "verdict": verdict, "what_differs": what}


def test_reconcile_moves_a_replaced_doc_to_outdated_even_when_the_numbers_differ():
    claims = {"D09": "38 minutes of flight time.", "D10": "45 minutes of flight time."}
    out = reconcile(_state(claims, {"D09", "D10"}))  # a linked pair is never compared
    assert out["route"] == "answer"
    assert out["relevant_ids"] == ["D10"]
    assert [(o["old_id"], o["new_id"]) for o in out["outdated"]] == [("D09", "D10")]
    assert out["disputes"] == []


def test_reconcile_keeps_a_dispute_with_what_differs():
    pair = _pair("D03", "D04", "different", "D03 says 16 weeks, D04 says 12 weeks")
    out = reconcile(_state({"D03": "16 weeks.", "D04": "12 weeks."}, {"D03", "D04"}, [pair]))
    assert out["route"] == "conflict"
    assert out["disputes"] == [{"doc_a": "D03", "doc_b": "D04",
                                "description": "D03 says 16 weeks, D04 says 12 weeks"}]


def test_reconcile_answers_when_the_docs_agree():
    pair = _pair("D10", "D18", "same")
    out = reconcile(_state({"D10": "It weighs 1.2 kg.", "D18": "The drone weighs 1.2 kg."},
                           {"D10", "D18"}, [pair]))
    assert out["route"] == "answer"
    assert out["disputes"] == []


def test_reconcile_ignores_a_difference_with_a_doc_that_is_not_relevant():
    pair = _pair("D15", "D20", "different", "different things")
    out = reconcile(_state({"D15": "Acknowledge within 15 minutes.", "D20": "Two engineers."},
                           {"D15"}, [pair]))
    assert out["route"] == "answer"
    assert out["relevant_ids"] == ["D15"]


def test_reconcile_abstains_when_nothing_is_relevant():
    out = reconcile(_state({"D03": None, "D16": "11 public holidays."}, set()))
    assert out["route"] == "abstain"
    assert out["relevant_ids"] == []


def test_pairs_to_compare_leaves_out_supersedes_links():
    assert pairs_to_compare(["D01", "D02", "D03"]) == [("D01", "D03"), ("D02", "D03")]


def test_read_comparison_matches_pairs_in_any_order_and_fills_gaps():
    out = Comparison(
        docs=[DocAssessment(doc_id="D03", relevant=True), DocAssessment(doc_id="D99", relevant=True)],
        pairs=[PairComparison(doc_a="D04", doc_b="D03", verdict="different", what_differs=None),
               PairComparison(doc_a="D03", doc_b="D05", verdict="same", what_differs=None)],
    )
    relevance, pairs = read_comparison(out, ["D03", "D04", "D05"],
                                       [("D03", "D04"), ("D03", "D05"), ("D04", "D05")])
    assert relevance == {"D03": True, "D04": False, "D05": False}
    assert pairs == [
        _pair("D03", "D04", "different", "D03 and D04 give different answers"),
        _pair("D03", "D05", "same"),
        _pair("D04", "D05", "unrelated"),  # left out by the LLM
    ]


WEEKS = {"week": {"D03": {16.0}, "D04": {12.0}}}


def test_check_answer_accepts_a_clean_answer():
    text = "Yes, adoption is covered [D03]. It also covers foster care [D03, D04]."
    assert check_answer(text, ["D03", "D04"], WEEKS) == (["D03", "D04"], [], [])


def test_check_answer_finds_ids_that_are_not_allowed():
    assert check_answer("Two approvals [D14] [D15].", ["D14"], {}) == (["D14"], ["D15"], [])


def test_check_answer_finds_a_disputed_number():
    assert check_answer("Leave is paid for 16 weeks [D03].", ["D03", "D04"], WEEKS) == (
        ["D03"], [], ["week"])
