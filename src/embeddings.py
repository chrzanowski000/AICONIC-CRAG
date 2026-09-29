"""Local text embeddings: FastEmbed (ONNX, CPU)."""

from functools import lru_cache

from langchain_core.embeddings import Embeddings

import config


class FastEmbedDense(Embeddings):
    """LangChain wrapper around fastembed.TextEmbedding. Vectors come back normalized."""

    def __init__(self, model_name: str, cache_dir: str):
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._model = TextEmbedding(model_name, cache_dir=cache_dir)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """One embeddings object per process."""
    return FastEmbedDense(config.EMBEDDING_MODEL, config.MODELS_CACHE_DIR)
