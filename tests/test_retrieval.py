"""Tests for the score cutoff and the context cap in src/vectorstore.py (no search, no model)."""

import pytest

import config
from src import vectorstore
from src.load_docs import doc_map
from src.vectorstore import _to_retrieved, score_floor


@pytest.fixture(autouse=True)
def fixed_cutoff(monkeypatch):
    """The tests use these numbers, whatever .env sets."""
    monkeypatch.setattr(config, "SCORE_THRESHOLD", 0.58)
    monkeypatch.setattr(config, "SCORE_MARGIN", 0.10)


def test_the_floor_is_the_cutoff_when_the_best_hit_is_weak():
    assert score_floor(0.60) == 0.58  # 0.60 - 0.10 is under the cutoff 0.58


def test_the_floor_is_the_margin_below_a_strong_best_hit():
    assert abs(score_floor(0.888) - 0.788) < 1e-9


def _ids(docs):
    return [d["doc_id"] for d in docs]


def _search_returns(monkeypatch, scores: dict[str, float]):
    hits = [_to_retrieved(doc_map()[i], s) for i, s in scores.items()]
    monkeypatch.setattr(vectorstore, "search", lambda question: hits)


def test_the_cap_never_splits_a_topic(monkeypatch):
    # kestrel-x2 has 5 docs, annual-leave 3 (D27 -> D28 -> D29), offices 2 (D07 -> D08)
    _search_returns(monkeypatch, {"D10": 0.90, "D27": 0.85, "D07": 0.84})
    monkeypatch.setattr(config, "MAX_CONTEXT_DOCS", 7)
    retrieved = vectorstore.retrieve("q")["retrieved"]
    # annual-leave would make 8, so it is left out with its hit; offices fits (7)
    assert sorted(_ids(retrieved)) == ["D07", "D08", "D09", "D10", "D18", "D30", "D31"]
    assert _ids(retrieved)[:2] == ["D10", "D07"]  # search hits first, best first


def test_the_topic_of_the_best_hit_always_goes_in(monkeypatch):
    _search_returns(monkeypatch, {"D10": 0.90, "D07": 0.84})
    monkeypatch.setattr(config, "MAX_CONTEXT_DOCS", 3)
    retrieved = vectorstore.retrieve("q")["retrieved"]
    assert sorted(_ids(retrieved)) == ["D09", "D10", "D18", "D30", "D31"]


def test_nothing_is_kept_under_the_cutoff(monkeypatch):
    _search_returns(monkeypatch, {"D10": 0.50})
    out = vectorstore.retrieve("q")
    assert out["retrieved"] == [] and _ids(out["closest"]) == ["D10"]
