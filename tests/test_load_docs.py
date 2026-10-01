"""Tests for the corpus checks in src/load_docs.py."""

import json

import pytest

import config
from src.load_docs import CorpusError, load_documents
from src.schemas import FinalOutput


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


@pytest.mark.parametrize("name", config.datasets())
def test_every_dataset_loads_and_its_questions_name_real_docs(name):
    folder = config.DATA_DIR / name
    ids = {d.metadata["id"] for d in load_documents(str(folder / "corpus"))}
    questions = json.loads((folder / "questions.json").read_text())
    assert len({q["id"] for q in questions}) == len(questions)
    for q in questions:
        want = q["expected"]
        named = {c["doc_id"] for key in ("citations", "versions") for c in want.get(key, [])}
        named |= {o[k] for o in want.get("outdated", []) for k in ("old_id", "new_id")}
        assert named <= ids, f"{name} {q['id']} names unknown docs {named - ids}"


@pytest.mark.parametrize("name", config.datasets())
def test_every_expected_block_has_the_shape_of_the_output(name):
    """The expected block uses the output's field names, so the two can be compared side by side
    (for example in LangSmith). Only `checks` holds rules that are not part of the output."""
    questions = json.loads((config.DATA_DIR / name / "questions.json").read_text())
    fields = set(FinalOutput.model_fields) | set(FinalOutput.model_computed_fields)
    for q in questions:
        want = q["expected"]
        assert set(want) - {"checks"} <= fields, f"{name} {q['id']}: {set(want) - fields}"
        expected_flags = FinalOutput(status=want["status"]).model_dump()
        assert (want["dispute"], want["no_answer"]) == (
            expected_flags["dispute"], expected_flags["no_answer"]), f"{name} {q['id']}"
        assert (want["answer"] is not None) == (want["status"] == "answered"), f"{name} {q['id']}"
        assert set(want.get("checks", {})) <= {"answer_contains", "answer_excludes", "at_search",
                                               "also_fine"}, f"{name} {q['id']}"
