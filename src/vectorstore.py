"""Qdrant: one client per process, the collection, the index build, and retrieval."""

import atexit
import logging
import uuid
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

import config
from src.embeddings import get_embeddings
from src.load_docs import corpus_files, corpus_hash, doc_map, load_documents

log = logging.getLogger(__name__)


class RetrievedDoc(TypedDict):
    doc_id: str
    title: str
    source: str
    date: str
    topic: str
    supersedes: str | None
    text: str
    score: float | None  # None = added as a related doc, not found by the search


class LockedStorageError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    """The one Qdrant client of this process. Closed when the process exits."""
    if config.QDRANT_MODE == "server":
        client = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY or None)
    elif config.QDRANT_MODE == "embedded":
        try:
            client = QdrantClient(path=config.QDRANT_PATH)
        except RuntimeError as err:
            if "already accessed" not in str(err):
                raise
            raise LockedStorageError(
                f"The Qdrant folder {config.QDRANT_PATH} is in use by another process.\n"
                "Fix it one of these ways:\n"
                "  1. stop the other program that uses it (another main.py or eval.py run,\n"
                "     or `langgraph dev` for Studio). Find it with:\n"
                '     ps aux | grep -E "langgraph dev|eval.py|main.py" | grep -v grep\n'
                "  2. or run a Qdrant server and set QDRANT_MODE=server.\n"
                "Don't delete the .lock file: the lock goes away when that program stops."
            ) from err
    else:
        raise ValueError(f"Unknown QDRANT_MODE '{config.QDRANT_MODE}'")
    atexit.register(client.close)
    return client


def point_id(doc_id: str) -> str:
    """Same doc id -> same point id, so writing a doc twice updates it."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))


def _hash_file() -> Path:
    return Path(config.QDRANT_PATH) / f"{config.QDRANT_COLLECTION}.sha256"


def _stored_hash() -> str | None:
    path = _hash_file()
    return path.read_text().strip() if path.exists() else None


def _rebuild_reason(force: bool) -> str | None:
    """Why the index must be rebuilt, or None if it can be reused."""
    client = get_client()
    if force:
        return "reindex was asked for"
    if not client.collection_exists(config.QDRANT_COLLECTION):
        return "the collection does not exist yet"
    count = client.count(config.QDRANT_COLLECTION, exact=True).count
    files = len(corpus_files())
    if count != files:
        return f"the collection has {count} points but there are {files} files"
    if _stored_hash() != corpus_hash():
        return "the documents changed since the last build"
    return None


def ensure_index(force: bool = False) -> dict:
    """Build the collection if needed. Returns what happened, for printing."""
    client = get_client()
    reason = _rebuild_reason(force)
    if reason is None:
        count = client.count(config.QDRANT_COLLECTION, exact=True).count
        return {"rebuilt": False, "reason": "index is up to date", "points": count}

    docs = load_documents()
    if client.collection_exists(config.QDRANT_COLLECTION):
        client.delete_collection(config.QDRANT_COLLECTION)
    client.create_collection(
        config.QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=len(get_embeddings().embed_query("size")), distance=models.Distance.COSINE
        ),
    )
    get_store().add_documents(docs, ids=[point_id(d.metadata["id"]) for d in docs])
    _hash_file().parent.mkdir(parents=True, exist_ok=True)
    _hash_file().write_text(corpus_hash() + "\n")
    count = client.count(config.QDRANT_COLLECTION, exact=True).count
    return {"rebuilt": True, "reason": reason, "points": count}


@lru_cache(maxsize=1)
def get_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        client=get_client(),
        collection_name=config.QDRANT_COLLECTION,
        embedding=get_embeddings(),
        distance=models.Distance.COSINE,
    )


def _to_retrieved(doc: Document, score: float | None) -> RetrievedDoc:
    meta = doc.metadata
    return RetrievedDoc(
        doc_id=meta["id"],
        title=meta["title"],
        source=meta["source"],
        date=meta["date"],
        topic=meta["topic"],
        supersedes=meta.get("supersedes"),
        text=doc.page_content,
        score=None if score is None else round(float(score), 4),
    )


def search(question: str, k: int | None = None) -> list[RetrievedDoc]:
    """Plain vector search, no cutoff, no related docs. Best score first."""
    hits = get_store().similarity_search_with_score(question, k=k or config.TOP_K)
    return [_to_retrieved(doc, score) for doc, score in hits]


def score_floor(best_score: float) -> float:
    """Lowest score a search hit needs to be kept: the cutoff, or best minus the margin."""
    if config.SCORE_MARGIN > 0:
        return max(config.SCORE_THRESHOLD, best_score - config.SCORE_MARGIN)
    return config.SCORE_THRESHOLD


def retrieve(question: str) -> dict:
    """Search, drop weak hits, add the other docs on the same topics, cap the list.

    Returns {"retrieved": [...], "closest": [...]}. `closest` holds the top search hits before
    the cutoff, best first, so an "I don't know" answer can show what was looked at.
    """
    hits = search(question)
    floor = score_floor(hits[0]["score"] if hits else 0.0)
    closest = [{"doc_id": h["doc_id"], "date": h["date"], "score": h["score"]} for h in hits]
    kept = [h for h in hits if h["score"] >= floor]
    if not kept:
        return {"retrieved": [], "closest": closest}

    # Add every other doc on the same topics. A doc and the doc it replaces always share a
    # topic (load_docs checks this), so this also brings in both ends of a "replaces" link.
    seen = {h["doc_id"] for h in kept}
    topics = {h["topic"] for h in kept}
    added = [_to_retrieved(doc, None) for doc_id, doc in doc_map().items()
             if doc.metadata["topic"] in topics and doc_id not in seen]
    added.sort(key=lambda d: d["date"], reverse=True)
    retrieved = (kept + added)[: config.MAX_CONTEXT_DOCS]
    return {"retrieved": retrieved, "closest": closest}
