"""Embedding model wrapper. E5 models need a "passage: " / "query: " prefix on every text; bge-m3 needs none."""
import os
from typing import TYPE_CHECKING

from app import env  # noqa: F401  (loads .env before MODEL is read)

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

MODEL = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-m3")
PASSAGE_PREFIX, QUERY_PREFIX = ("passage: ", "query: ") if "e5" in MODEL.lower() else ("", "")
_model = None


def model() -> "SentenceTransformer":
    global _model
    if _model is None:
        # Imported here so that code and tests that never embed do not need torch installed.
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL, device="cpu")
    return _model


def dimension() -> int:
    return model().get_embedding_dimension()


def token_count(text: str) -> int:
    return len(model().tokenizer(PASSAGE_PREFIX + text)["input_ids"])


def embed_passages(texts: list[str]) -> list[list[float]]:
    return model().encode([PASSAGE_PREFIX + t for t in texts], normalize_embeddings=True, batch_size=8).tolist()


def embed_query(question: str) -> list[float]:
    return model().encode(QUERY_PREFIX + question, normalize_embeddings=True).tolist()
