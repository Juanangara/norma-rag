"""Turn articles into chunks that fit the embedding model.

An article is one chunk unless it is longer than `limit` tokens. Then it is split on paragraph
boundaries (and on sentences if a single paragraph is still too long). Every part repeats the
article heading in its embedding text, so a part is never an anonymous fragment.
"""
import re
from typing import Callable

SENTENCE_END = re.compile(r"(?<=[.;:])\s+")


def _pack(units: list[str], count: Callable[[str], int], budget: int, sep: str) -> list[str]:
    parts, current = [], ""
    for u in units:
        candidate = f"{current}{sep}{u}" if current else u
        if current and count(candidate) > budget:
            parts.append(current)
            current = u
        else:
            current = candidate
    if current:
        parts.append(current)
    return parts


def split_text(texto: str, count: Callable[[str], int], budget: int) -> list[str]:
    if count(texto) <= budget:
        return [texto]
    parts = []
    for block in _pack(texto.split("\n\n"), count, budget, "\n\n"):
        if count(block) <= budget:
            parts.append(block)
        else:  # one paragraph alone is too long
            parts += _pack(SENTENCE_END.split(block), count, budget, " ")
    return parts


def split_definitions(texto: str) -> list[str]:
    """One part per definition: an intro paragraph followed by independent definitions.

    Each part keeps the intro so it reads on its own ("... se entiende por: e) Responsable ...").
    """
    intro, *items = texto.split("\n\n")
    return [f"{intro}\n\n{item}" for item in items] if items else [texto]


def chunk_article(article: dict, count: Callable[[str], int], limit: int = 450) -> list[dict]:
    """`count` measures the embedding text of a chunk (heading included)."""
    def embedding_text(texto: str) -> str:
        return passage_text({**article, "texto": texto})

    if article["titulo_articulo"] == "Definiciones":
        parts = split_definitions(article["texto"])
    else:
        parts = split_text(article["texto"], lambda s: count(embedding_text(s)), limit)
    if len(parts) == 1:
        return [{**article, "parte": 1, "embedding_text": embedding_text(parts[0])}]
    return [
        {**article, "id": f"{article['id']}-p{i}", "parte": i, "texto": p, "embedding_text": embedding_text(p)}
        for i, p in enumerate(parts, 1)
    ]


def passage_text(chunk: dict) -> str:
    return f"{chunk['norma']}, artículo {chunk['articulo']}. {chunk['titulo_articulo']}. {chunk['texto']}"
