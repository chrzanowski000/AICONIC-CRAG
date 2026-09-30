"""Tests for the corpus checks in src/load_docs.py."""

import pytest

from src.load_docs import CorpusError, load_documents


def _write(folder, doc_id, topic, supersedes="null"):
    (folder / f"{doc_id}.md").write_text(
        f"---\nid: {doc_id}\ntitle: T\nsource: S\ndate: 2025-01-01\ntopic: {topic}\n"
        f"supersedes: {supersedes}\n---\nText.\n"
    )


def test_the_real_corpus_loads():
    assert len(load_documents()) == 40


def test_a_replaced_doc_must_exist(tmp_path):
    _write(tmp_path, "D01", "a", supersedes="D09")
    with pytest.raises(CorpusError, match="does not exist"):
        load_documents(str(tmp_path))


def test_a_doc_and_the_doc_it_replaces_share_a_topic(tmp_path):
    _write(tmp_path, "D01", "a")
    _write(tmp_path, "D02", "b", supersedes="D01")
    with pytest.raises(CorpusError, match="topics differ"):
        load_documents(str(tmp_path))


def test_duplicate_ids_are_refused(tmp_path):
    _write(tmp_path, "D01", "a")
    (tmp_path / "copy.md").write_text((tmp_path / "D01.md").read_text())
    with pytest.raises(CorpusError, match="Duplicate"):
        load_documents(str(tmp_path))


def test_a_bad_date_is_refused(tmp_path):
    (tmp_path / "D01.md").write_text(
        "---\nid: D01\ntitle: T\nsource: S\ndate: 1 March 2025\ntopic: a\nsupersedes: null\n---\nText.\n")
    with pytest.raises(CorpusError, match="not YYYY-MM-DD"):
        load_documents(str(tmp_path))


def test_a_doc_cannot_replace_itself(tmp_path):
    _write(tmp_path, "D01", "a", supersedes="D01")
    with pytest.raises(CorpusError, match="supersedes itself"):
        load_documents(str(tmp_path))
