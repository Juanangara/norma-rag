CREATE EXTENSION IF NOT EXISTS vector;

-- One row per chunk: a whole article, or one part of a long one (`parte`).
-- __DIM__ is the embedding size of the configured model. ingest.load recreates this table on every
-- run, so changing EMBEDDING_MODEL only needs a reload.
DROP TABLE IF EXISTS chunks;
CREATE TABLE chunks (
    id              TEXT PRIMARY KEY,
    norma_id        TEXT NOT NULL,
    norma           TEXT NOT NULL,
    articulo        TEXT NOT NULL,
    parte           INT  NOT NULL DEFAULT 1,
    orden           INT  NOT NULL,
    titulo_articulo TEXT NOT NULL,
    estructura      TEXT NOT NULL,
    texto           TEXT NOT NULL,
    equivalencias   JSONB NOT NULL DEFAULT '{}',
    origen          TEXT,
    fuente          JSONB NOT NULL,
    embedding       vector(__DIM__) NOT NULL,
    tsv             tsvector GENERATED ALWAYS AS (
                        to_tsvector('spanish', titulo_articulo || ' ' || texto)
                    ) STORED
);

CREATE INDEX chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX chunks_norma_idx ON chunks (norma_id, orden);
