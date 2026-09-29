"""Tests for the plain-Python rules in src/graph.py that use the real corpus (no model calls)."""

from src.graph import disputed_numbers, newest_in_chain, same_chain
from src.load_docs import doc_map


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


def test_disputed_numbers_ignores_a_replaced_document():
    assert disputed_numbers(_docs("D09", "D10")) == {}  # 38 vs 45 minutes, but D10 replaces D09


def test_replaces_chains():
    assert newest_in_chain("D01") == "D02"
    assert newest_in_chain("D02") == "D02"
    assert same_chain("D07", "D08")
    assert not same_chain("D03", "D04")  # a real dispute: no supersedes link
