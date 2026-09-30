"""Tests for the checks in eval.py, so a PASS in the eval means what it says."""

from eval import (abstained_cleanly, answer_contains, answer_excludes, cites_required_docs,
                  disputed_shows_both_sides, marks_outdated, mentions, status_matches)

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


def test_status_and_citations():
    assert status_matches(Q, {"status": "answered"}, {"status": "answered"})["score"] == 1
    assert status_matches(Q, {"status": "disputed"}, {"status": "answered"})["score"] == 0
    out = {"citations": [_cite("D10"), _cite("D18")]}
    assert cites_required_docs(Q, out, {"cites": ["D10", "D18"]})["score"] == 1
    assert cites_required_docs(Q, {"citations": [_cite("D10")]}, {"cites": ["D10", "D18"]})["score"] == 0
    assert cites_required_docs(Q, out, {"cites_any": ["D18", "D30"]})["score"] == 1
    assert cites_required_docs(Q, {"citations": [_cite("D10", date="")]}, {"cites": ["D10"]})["score"] == 0


def test_dispute_needs_every_version_with_a_date_and_no_answer():
    ref = {"status": "disputed", "versions": ["D23", "D24", "D25"]}
    three = {"versions": [_cite("D23"), _cite("D24"), _cite("D25")], "answer": None}
    assert disputed_shows_both_sides(Q, three, ref)["score"] == 1
    assert disputed_shows_both_sides(Q, {**three, "versions": three["versions"][:2]}, ref)["score"] == 0
    assert disputed_shows_both_sides(Q, {**three, "answer": "€1,000"}, ref)["score"] == 0


def test_outdated_notes_for_a_chain_of_three():
    notes = [{"old_id": "D27", "old_date": "2023-01-01", "new_id": "D29", "new_date": "2025-01-01"},
             {"old_id": "D28", "old_date": "2024-01-01", "new_id": "D29", "new_date": "2025-01-01"}]
    ref = {"outdated": [["D27", "D29"], ["D28", "D29"]]}
    assert marks_outdated(Q, {"outdated": notes}, ref)["score"] == 1
    assert marks_outdated(Q, {"outdated": notes[:1]}, ref)["score"] == 0


def test_abstain_and_where_it_stopped():
    ref = {"status": "abstained", "at_search": True}
    at_search = {"status": "abstained", "reason": "The documents do not answer this question. "
                                                  "No document is close enough to the question."}
    after_reading = {"status": "abstained", "reason": "None of the documents found says anything."}
    assert abstained_cleanly(Q, at_search, ref)["score"] == 1
    assert abstained_cleanly(Q, after_reading, ref)["score"] == 0
    assert abstained_cleanly(Q, after_reading, {"status": "abstained"})["score"] == 1
    assert abstained_cleanly(Q, {"status": "abstained", "answer": "x"}, {"status": "abstained"})["score"] == 0


def test_answer_contains_and_excludes():
    out = {"answer": "Yes, parental leave is paid at 100% of your salary [D03] [D04]."}
    assert answer_contains(Q, out, {"answer_contains": ["full", "100%"]})["score"] == 1
    assert answer_excludes(Q, out, {"answer_excludes": ["16", "12"]})["score"] == 1
    assert answer_excludes(Q, {"answer": "Paid for 12 weeks."}, {"answer_excludes": ["12"]})["score"] == 0
