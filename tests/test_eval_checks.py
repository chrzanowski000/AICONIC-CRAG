"""Tests for the checks in eval.py, so a PASS in the eval means what it says."""

from eval import (answer_contains, answer_excludes, cites_required_docs, dispute_links_right_docs,
                  marks_outdated, mentions, no_answer_is_clean, outcome_matches)
from src.schemas import FinalOutput

Q = {"question": "q"}


def _cite(doc_id, date="2025-01-01"):
    return {"doc_id": doc_id, "date": date, "source": "S", "claim": "c"}


def test_mentions_matches_whole_words_and_numbers_only():
    assert mentions("A pull request needs 2 approvals.", "2")
    assert not mentions("Updated in 2025 [D12].", "2")
    assert not mentions("Changed on 2025-02-12.", "12")
    assert mentions("Claims are accepted within 30.", "30")
    assert mentions("Paid at 100% of base salary.", "100%")
    assert mentions("Yes, adoption is covered.", "adoption")
    assert not mentions("Yes, adoption is covered.", "adopt")


def test_the_output_flags_follow_the_status():
    assert FinalOutput(status="disputed").model_dump()["dispute"] is True
    assert FinalOutput(status="abstained").model_dump()["no_answer"] is True
    one = FinalOutput(status="answered").model_dump()
    assert one["dispute"] is False and one["no_answer"] is False


ONE = {"status": "answered", "dispute": False, "no_answer": False}
DISPUTE = {"status": "disputed", "answer": None, "dispute": True, "no_answer": False}
NONE = {"status": "abstained", "answer": None, "dispute": False, "no_answer": True}


def _ids(*doc_ids):
    return [{"doc_id": i} for i in doc_ids]


def test_outcome_and_citations():
    assert outcome_matches(Q, {"dispute": False, "no_answer": False}, ONE)["score"] == 1
    assert outcome_matches(Q, {"dispute": True, "no_answer": False}, ONE)["score"] == 0
    assert outcome_matches(Q, {"dispute": False, "no_answer": True}, NONE)["score"] == 1
    out = {"citations": [_cite("D10"), _cite("D18")]}
    both = {**ONE, "citations": _ids("D10", "D18")}
    assert cites_required_docs(Q, out, both)["score"] == 1
    assert cites_required_docs(Q, {"citations": [_cite("D10")]}, both)["score"] == 0
    assert cites_required_docs(Q, out, {**ONE, "citations": _ids("D10")})["score"] == 1  # more is fine
    undated = {"citations": [_cite("D10", date="")]}
    assert cites_required_docs(Q, undated, {**ONE, "citations": _ids("D10")})["score"] == 0


def test_dispute_needs_the_flag_and_exactly_the_right_documents():
    ref = {**DISPUTE, "versions": _ids("D23", "D24", "D25")}
    three = {"dispute": True, "versions": [_cite("D23"), _cite("D24"), _cite("D25")], "answer": None}
    assert dispute_links_right_docs(Q, three, ref)["score"] == 1
    assert dispute_links_right_docs(Q, {**three, "versions": three["versions"][:2]}, ref)["score"] == 0
    extra = {**three, "versions": three["versions"] + [_cite("D13")]}
    assert dispute_links_right_docs(Q, extra, ref)["score"] == 0  # a wrong document is linked
    assert dispute_links_right_docs(Q, {**three, "answer": "€1,000"}, ref)["score"] == 0
    assert dispute_links_right_docs(Q, three, ONE)["comment"] == "n/a"


def test_outdated_notes_for_a_chain_of_three():
    notes = [{"old_id": "D27", "old_date": "2023-01-01", "new_id": "D29", "new_date": "2025-01-01"},
             {"old_id": "D28", "old_date": "2024-01-01", "new_id": "D29", "new_date": "2025-01-01"}]
    ref = {**ONE, "outdated": [{"old_id": "D27", "new_id": "D29"}, {"old_id": "D28", "new_id": "D29"}]}
    assert marks_outdated(Q, {"outdated": notes}, ref)["score"] == 1
    assert marks_outdated(Q, {"outdated": notes[:1]}, ref)["score"] == 0


def test_no_answer_needs_the_flag_and_where_it_stopped():
    ref = {**NONE, "checks": {"at_search": True}}
    at_search = {"no_answer": True, "reason": "The documents do not answer this question. "
                                              "No document is close enough to the question."}
    after_reading = {"no_answer": True, "reason": "None of the documents found says anything."}
    assert no_answer_is_clean(Q, at_search, ref)["score"] == 1
    assert no_answer_is_clean(Q, after_reading, ref)["score"] == 0
    assert no_answer_is_clean(Q, after_reading, NONE)["score"] == 1
    assert no_answer_is_clean(Q, {"no_answer": True, "answer": "x"}, NONE)["score"] == 0


def test_answer_contains_and_excludes():
    out = {"answer": "Yes, parental leave is paid at 100% of your salary [D03] [D04]."}
    assert answer_contains(Q, out, {"checks": {"answer_contains": ["full", "100%"]}})["score"] == 1
    assert answer_excludes(Q, out, {"checks": {"answer_excludes": ["16", "12"]}})["score"] == 1
    banned = {"checks": {"answer_excludes": ["12"]}}
    assert answer_excludes(Q, {"answer": "Paid for 12 weeks."}, banned)["score"] == 0


def test_answer_is_correct_passes_only_on_correct(monkeypatch):
    import eval as ev

    seen = {}

    def fake_grade(question, output_text, reference):
        seen["text"], seen["reference"] = output_text, reference
        return ev.Grade(verdict=verdict, reason="because")

    monkeypatch.setattr(ev, "grade", fake_grade)
    out = {"status": "answered", "answer": "Two approvals [D14].", "citations": [_cite("D14")]}
    ref = {**ONE, "answer": "A pull request needs 2 approvals [D14].",
           "checks": {"also_fine": "from people on the team."}}
    for verdict, score in (("correct", 1), ("partly correct", 0), ("incorrect", 0)):
        result = ev.answer_is_correct(Q, out, ref)
        assert result["score"] == score
        assert result["comment"] == f"{verdict}: because"
    assert "Two approvals [D14]." in seen["text"] and "[D14] S (created 2025-01-01)" in seen["text"]
    assert seen["reference"] == "A pull request needs 2 approvals [D14]. Also fine: from people on the team."
    assert ev.answer_is_correct(Q, out, DISPUTE)["comment"] == "n/a"  # no expected answer, no grading
