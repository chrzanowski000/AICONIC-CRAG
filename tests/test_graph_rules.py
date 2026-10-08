"""Tests for the plain-Python rules in src/graph.py that use the real corpus (no model calls)."""

import pytest
from langchain_core.messages import AIMessage

from src import graph
from src.graph import (abstain, conflict_report, find_citations, newest_in_chain,
                       pairs_to_compare, read_comparison, reconcile, with_agreeing)
from src.load_docs import doc_map
from src.schemas import Answer, AnswerCheck, Comparison, DocAssessment, PairComparison
from src.vectorstore import _to_retrieved


def test_replaces_chains():
    assert newest_in_chain("D01") == "D02"
    assert newest_in_chain("D02") == "D02"
    assert newest_in_chain("D27") == "D29"  # a chain of three
    assert newest_in_chain("D03") == "D03"  # a real dispute: no supersedes link


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


def test_pairs_to_compare_leaves_out_replaced_docs():
    assert pairs_to_compare(["D01", "D02", "D03"]) == [("D02", "D03")]  # D02 replaces D01
    assert pairs_to_compare(["D27", "D28", "D29", "D26"]) == [("D29", "D26")]


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


def test_find_citations_in_order_with_ids_that_are_not_allowed():
    text = "Adoption is covered [D04]. It can be split [D03, D04]. See also [D15]."
    assert find_citations(text, ["D03", "D04"]) == (["D04", "D03"], ["D15"])


def test_find_citations_with_none():
    assert find_citations("No ids here.", ["D03"]) == ([], [])


def test_conflict_report_shows_both_creation_dates():
    state = _state({"D03": "16 weeks.", "D04": "12 weeks."}, {"D03", "D04"})
    state["disputes"] = [{"doc_a": "D03", "doc_b": "D04",
                          "description": "D03 says 16 weeks, D04 says 12 weeks."}]
    result = conflict_report(state)["result"]
    assert [(v["doc_id"], v["date"]) for v in result["versions"]] == [
        ("D03", "2025-01-10"), ("D04", "2025-02-20")]
    assert result["differences"] == [
        "[D03] (created 2025-01-10) vs [D04] (created 2025-02-20): "
        "D03 says 16 weeks, D04 says 12 weeks."]


def test_abstain_lists_the_closest_documents_with_dates():
    state = {"question": "q", "retrieved": [],
             "closest": [{"doc_id": "D02", "date": "2025-06-15", "score": 0.541}]}
    reason = abstain(state)["result"]["reason"]
    assert "Closest documents: D02 (created 2025-06-15, score 0.541)." in reason


def test_with_agreeing_adds_every_doc_that_gives_the_same_answer():
    pairs = [_pair("D30", "D31", "same"), _pair("D31", "D18", "same")]
    assert with_agreeing(["D30"], pairs, ["D30", "D31", "D18"]) == ["D30", "D31", "D18"]


def test_with_agreeing_leaves_out_unrelated_and_not_allowed_docs():
    pairs = [_pair("D15", "D20", "unrelated"), _pair("D15", "D14", "same")]
    assert with_agreeing(["D15"], pairs, ["D15", "D20"]) == ["D15"]


def test_reconcile_chain_of_three_answers_from_the_newest_and_marks_both_older_ones():
    claims = {"D27": "25 days.", "D28": "28 days.", "D29": "30 days."}
    out = reconcile(_state(claims, {"D27", "D28", "D29"}))
    assert out["route"] == "answer"
    assert out["relevant_ids"] == ["D29"]
    assert sorted((o["old_id"], o["new_id"]) for o in out["outdated"]) == [("D27", "D29"), ("D28", "D29")]


def test_reconcile_three_way_dispute_keeps_every_pair():
    pairs = [_pair("D23", "D24", "different", "1,000 vs 1,200"),
             _pair("D23", "D25", "different", "1,000 vs 1,500"),
             _pair("D24", "D25", "different", "1,200 vs 1,500")]
    claims = {"D23": "€1,000.", "D24": "€1,200.", "D25": "€1,500."}
    out = reconcile(_state(claims, set(claims), pairs))
    assert out["route"] == "conflict"
    assert len(out["disputes"]) == 3
    versions = conflict_report({**_state(claims, set(claims)), **out})["result"]["versions"]
    assert [v["doc_id"] for v in versions] == ["D23", "D24", "D25"]


def test_a_dispute_still_shows_the_outdated_note():
    # D01 is replaced by D02; D02 and D03 give different answers (a made-up pair, rules only)
    claims = {"D01": "Two days.", "D02": "Three days.", "D03": "Four days."}
    pair = _pair("D02", "D03", "different", "D02 says three days, D03 says four days.")
    state = _state(claims, set(claims), [pair])
    out = reconcile(state)
    assert out["route"] == "conflict"
    result = conflict_report({**state, **out})["result"]
    assert [v["doc_id"] for v in result["versions"]] == ["D02", "D03"]
    assert [(o["old_id"], o["new_id"]) for o in result["outdated"]] == [("D01", "D02")]


def test_read_comparison_cleans_ids_written_with_brackets():
    out = Comparison(
        docs=[DocAssessment(doc_id="[D03]", relevant=True), DocAssessment(doc_id=" D04", relevant=True)],
        pairs=[PairComparison(doc_a="[D03]", doc_b="[D04]", verdict="different", what_differs="x")],
    )
    relevance, pairs = read_comparison(out, ["D03", "D04"], [("D03", "D04")])
    assert relevance == {"D03": True, "D04": True}
    assert pairs == [_pair("D03", "D04", "different", "x")]


@pytest.mark.parametrize("d08_claim", [None, "Open from 7:00 to 20:00 on weekdays."])
def test_a_newer_doc_that_does_not_answer_is_not_used_as_the_answer(d08_claim):
    # D07 answers (weekends); D08 replaces it but says nothing about it, or is marked not relevant
    state = _state({"D07": "The office is closed on weekends.", "D08": d08_claim}, {"D07"})
    out = reconcile(state)
    assert out["route"] == "abstain"
    assert out["relevant_ids"] == []
    assert [(o["old_id"], o["new_id"]) for o in out["outdated"]] == [("D07", "D08")]
    result = abstain({**state, **out, "closest": []})["result"]
    assert "Only replaced documents say something about it" in result["reason"]
    assert [o["old_id"] for o in result["outdated"]] == ["D07"]


class _FakeLLM:
    """Replies in order: Answer, AnswerCheck, Answer, AnswerCheck. Keeps the messages it got."""

    def __init__(self, answers, problems):
        self.answers, self.problems, self.seen = list(answers), list(problems), []

    def __call__(self, schema, messages):
        self.seen.append(messages)
        if schema is Answer:
            return Answer(answer=self.answers.pop(0))
        return AnswerCheck(problems=self.problems.pop(0))


def _answer_state():
    state = _state({"D10": "It weighs 1.2 kg.", "D09": "It weighs 1.2 kg."}, {"D09", "D10"})
    state.update(reconcile(state))  # D09 is replaced by D10
    state["closest"] = [{"doc_id": "D10", "date": "2025-07-20", "score": 0.81}]
    return state


def test_the_retry_shows_the_first_answer_and_a_wrong_id_is_noted(monkeypatch):
    fake = _FakeLLM(["It weighs 1.2 kg [D09].", "It weighs 1.2 kg [D10] [D09]."], [[], []])
    monkeypatch.setattr(graph, "structured", fake)
    result = graph.answer(_answer_state())["result"]
    retry = fake.seen[2]  # the second Answer call
    assert isinstance(retry[-2], AIMessage) and retry[-2].content == "It weighs 1.2 kg [D09]."
    assert result["status"] == "answered"
    assert [c["doc_id"] for c in result["citations"]] == ["D10"]
    assert "[D09] (created 2024-11-05)" in result["reason"]


def test_an_answer_without_a_citation_is_an_i_dont_know_with_the_closest_docs(monkeypatch):
    monkeypatch.setattr(graph, "structured", _FakeLLM(["About a kilo.", "About a kilo."], [[], []]))
    out = graph.answer(_answer_state())
    assert out["route"] == "abstain"
    assert out["result"]["status"] == "abstained"
    assert "could not be tied to the documents" in out["result"]["reason"]
    assert "D10 (created 2025-07-20, score 0.810)" in out["result"]["reason"]
    assert [o["old_id"] for o in out["result"]["outdated"]] == ["D09"]
