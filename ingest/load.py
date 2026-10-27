"""Chunk, embed and load corpus/articles/*.jsonl into pgvector. Run: python -m ingest.load

The corpus is small, so each run drops and recreates the table (db/schema.sql, sized for the
configured model) inside one transaction. That also removes chunks that no longer exist after a
change in chunking, and makes switching embedding model a reload.
"""
import json
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector

from app.config import dsn
from ingest import embed
from ingest.chunk import chunk_article

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "corpus" / "articles"
SCHEMA = ROOT / "db" / "schema.sql"

INSERT = """
INSERT INTO chunks (id, norma_id, norma, articulo, parte, orden, titulo_articulo, estructura,
                    texto, equivalencias, origen, fuente, embedding)
VALUES (%(id)s, %(norma_id)s, %(norma)s, %(articulo)s, %(parte)s, %(orden)s, %(titulo_articulo)s,
        %(estructura)s, %(texto)s, %(equivalencias)s, %(origen)s, %(fuente)s, %(embedding)s)
"""


def read_articles() -> list[dict]:
    articles = []
    for path in sorted(ARTICLES.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            articles += [json.loads(line) for line in f]
    return articles


def build_chunks() -> list[dict]:
    return [c for a in read_articles() for c in chunk_article(a, embed.token_count)]


def load() -> int:
    chunks = build_chunks()
    vectors = embed.embed_passages([c["embedding_text"] for c in chunks])
    with psycopg.connect(dsn()) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")  # register_vector needs the type to exist
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(SCHEMA.read_text(encoding="utf-8").replace("__DIM__", str(embed.dimension())))
            for c, v in zip(chunks, vectors):
                cur.execute(INSERT, {
                    **c,
                    "equivalencias": json.dumps(c["equivalencias"]),
                    "fuente": json.dumps(c["fuente"]),
                    "embedding": v,
                })
    return len(chunks)


if __name__ == "__main__":
    print(f"{load()} chunks cargados")
