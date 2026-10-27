"""Hybrid retrieval: vector search + Spanish full-text search, fused with Reciprocal Rank Fusion.

Explicit article references in the question ("artículo 9 del Decreto 1377") are resolved first
and put at the top. Each hit carries its cosine similarity to the question, which the answer
layer can use to decide whether the evidence is strong enough.
"""
from dataclasses import dataclass, field

import psycopg
from pgvector.psycopg import register_vector

from app.references import find_references
from ingest import embed

POOL = 20     # candidates taken from each ranker
RRF_K = 60    # standard RRF damping constant

VECTOR_SQL = "SELECT id FROM chunks ORDER BY embedding <=> %(v)s::vector LIMIT %(n)s"

# plainto_tsquery ANDs every term; a natural question needs OR, so we swap the operator.
# `norm` is the ts_rank_cd normalization bit mask (0 = none, 1 = divide by 1 + log(length), ...).
LEXICAL_SQL = """
WITH q AS (SELECT replace(plainto_tsquery('spanish', %(q)s)::text, '&', '|')::tsquery AS tsq)
SELECT id FROM chunks, q WHERE tsv @@ tsq ORDER BY ts_rank_cd(tsv, tsq, %(norm)s) DESC LIMIT %(n)s
"""

# Vector search alone beat every hybrid setting on eval/questions.jsonl (see eval/REPORT.md),
# so the text ranker has weight 0 by default. It stays available for experiments.
DEFAULT_WEIGHTS = {"vector": 1.0, "texto": 0.0}
DEFAULT_LEX_NORM = 0

PINNED_SQL = """
SELECT id FROM chunks
WHERE norma_id = %(norma_id)s
  AND ((%(via_1377)s AND equivalencias->>'decreto_1377_2013' = %(articulo)s)
       OR (NOT %(via_1377)s AND articulo = %(articulo)s))
ORDER BY orden, parte
"""

FETCH_SQL = """
SELECT id, norma_id, norma, articulo, parte, titulo_articulo, estructura, texto,
       equivalencias, 1 - (embedding <=> %(v)s::vector) AS sim
FROM chunks WHERE id = ANY(%(ids)s)
"""


@dataclass
class Hit:
    id: str
    norma_id: str
    norma: str
    articulo: str
    parte: int
    titulo_articulo: str
    estructura: str
    texto: str
    equivalencias: dict
    sim: float                       # cosine similarity to the question
    score: float = 0.0               # fused score; pinned references get a larger one
    via: list[str] = field(default_factory=list)


def _ids(conn, sql: str, params: dict) -> list[str]:
    return [r[0] for r in conn.execute(sql, params).fetchall()]


def pinned_ids(conn: psycopg.Connection, question: str) -> list[str]:
    pinned = []
    for ref in find_references(question):
        params = {"norma_id": ref.norma_id, "articulo": ref.articulo, "via_1377": ref.via_1377}
        for cid in _ids(conn, PINNED_SQL, params):
            if cid not in pinned:
                pinned.append(cid)
    return pinned


def rank_candidates(conn: psycopg.Connection, question: str, v: list[float], lex_norm: int = DEFAULT_LEX_NORM) -> dict[str, list[str]]:
    """Chunk ids from each ranker, best first."""
    return {
        "vector": _ids(conn, VECTOR_SQL, {"v": v, "n": POOL}),
        "texto": _ids(conn, LEXICAL_SQL, {"q": question, "n": POOL, "norm": lex_norm}),
        "referencia": pinned_ids(conn, question),
    }


def fuse(rankings: dict[str, list[str]], weights: dict[str, float] = DEFAULT_WEIGHTS) -> tuple[dict[str, float], dict[str, list[str]]]:
    """Weighted Reciprocal Rank Fusion. Explicit references outrank everything else."""
    score: dict[str, float] = {}
    via: dict[str, list[str]] = {}
    for name, ids in rankings.items():
        w = 1.0 if name == "referencia" else weights.get(name, 1.0)
        for rank, cid in enumerate(ids, 1):
            score[cid] = score.get(cid, 0.0) + w / (RRF_K + rank)
            via.setdefault(cid, []).append(name)
    for cid in rankings.get("referencia", []):
        score[cid] += 1.0
    return score, via


def retrieve(conn: psycopg.Connection, question: str, k: int = 5, lex_norm: int = DEFAULT_LEX_NORM,
             weights: dict[str, float] = DEFAULT_WEIGHTS) -> list[Hit]:
    v = embed.embed_query(question)
    score, via = fuse(rank_candidates(conn, question, v, lex_norm), weights)
    top = sorted(score, key=score.get, reverse=True)[:k]
    rows = {r[0]: r for r in conn.execute(FETCH_SQL, {"v": v, "ids": top}).fetchall()}
    return [Hit(*rows[cid], score=score[cid], via=via[cid]) for cid in top]


def connect() -> psycopg.Connection:
    from app.config import dsn
    conn = psycopg.connect(dsn())
    register_vector(conn)
    return conn
