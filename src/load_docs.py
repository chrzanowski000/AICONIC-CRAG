"""Read the corpus: markdown files with frontmatter, turned into LangChain documents."""

import datetime as dt
import hashlib
from functools import lru_cache
from pathlib import Path

import frontmatter
from langchain_core.documents import Document

import config

REQUIRED_FIELDS = ("id", "title", "source", "date", "topic")


class CorpusError(ValueError):
    """The corpus has a problem that must be fixed before indexing."""


def corpus_files(corpus_dir: str | None = None) -> list[Path]:
    folder = Path(corpus_dir or config.CORPUS_DIR)
    files = sorted(folder.glob("*.md"))
    if not files:
        raise CorpusError(f"No .md files found in {folder}")
    return files


def _as_date_text(value, path: Path) -> str:
    if isinstance(value, dt.date):
        return value.isoformat()
    try:
        return dt.date.fromisoformat(str(value)).isoformat()
    except ValueError as err:
        raise CorpusError(f"{path.name}: date '{value}' is not YYYY-MM-DD") from err


def _read_one(path: Path) -> Document:
    post = frontmatter.load(path)
    missing = [f for f in REQUIRED_FIELDS if not post.get(f)]
    if missing:
        raise CorpusError(f"{path.name}: missing frontmatter fields {missing}")
    supersedes = post.get("supersedes") or None
    metadata = {
        "id": str(post["id"]),
        "title": str(post["title"]),
        "source": str(post["source"]),
        "date": _as_date_text(post["date"], path),
        "topic": str(post["topic"]),
        "supersedes": str(supersedes) if supersedes else None,
    }
    return Document(page_content=post.content.strip(), metadata=metadata)


def load_documents(corpus_dir: str | None = None) -> list[Document]:
    """Load and check every document. Raises CorpusError on the first problem found."""
    docs = [_read_one(path) for path in corpus_files(corpus_dir)]
    seen: set[str] = set()
    for doc in docs:
        doc_id = doc.metadata["id"]
        if doc_id in seen:
            raise CorpusError(f"Duplicate document id {doc_id}")
        seen.add(doc_id)
    topic = {doc.metadata["id"]: doc.metadata["topic"] for doc in docs}
    for doc in docs:
        doc_id, target = doc.metadata["id"], doc.metadata["supersedes"]
        if not target:
            continue
        if target not in seen:
            raise CorpusError(f"{doc_id} supersedes {target}, which does not exist")
        if target == doc_id:
            raise CorpusError(f"{target} supersedes itself")
        # Retrieval adds related docs by topic, so a doc and the one it replaces must share it.
        if topic[target] != topic[doc_id]:
            raise CorpusError(f"{doc_id} supersedes {target} but their topics differ")
    return docs


@lru_cache(maxsize=1)
def doc_map() -> dict[str, Document]:
    """doc id -> Document, for the default corpus. Loaded once per process."""
    return {doc.metadata["id"]: doc for doc in load_documents()}


def corpus_hash(corpus_dir: str | None = None) -> str:
    """sha256 over the names and bytes of all corpus files. Changes when any doc changes."""
    digest = hashlib.sha256()
    for path in corpus_files(corpus_dir):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()
