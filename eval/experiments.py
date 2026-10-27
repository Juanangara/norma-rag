"""Compare embedding models and rerankers without touching the database.

    python -m eval.experiments MODEL [MODEL ...] [--rerank] [--sets blind questions heldout]

Chunks are embedded in memory (cached under .cache/) and ranked by cosine similarity, so a model
needs no table of its own. By default only the development sets are scored; `heldout` is
opt-in so it is looked at on purpose, not by accident.
"""
import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

from eval.run_retrieval import K, article_of, articles_in_order, score
from ingest.load import build_chunks

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "embeddings"

# name -> (huggingface id, query prefix, passage prefix)
MODELS = {
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    "e5-base": ("intfloat/multilingual-e5-base", "query: ", "passage: "),
    "e5-large": ("intfloat/multilingual-e5-large", "query: ", "passage: "),
    "bge-m3": ("BAAI/bge-m3", "", ""),
}
RERANKER = "BAAI/bge-reranker-v2-m3"
SETS = {"questions": "questions.jsonl", "blind": "blind.jsonl", "heldout": "heldout.jsonl"}
POOL = 20


def load_set(name: str) -> list[dict]:
    path = ROOT / "eval" / SETS[name]
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    return [q for q in rows if q["esperados"]]


def passage_body(chunk: dict) -> str:
    """Same text as ingest.chunk.passage_text, without the E5 prefix."""
    return f"{chunk['norma']}, artículo {chunk['articulo']}. {chunk['titulo_articulo']}. {chunk['texto']}"


def embed_chunks(key: str, model: SentenceTransformer, chunks: list[dict]) -> np.ndarray:
    _, _, pprefix = MODELS[key]
    texts = [pprefix + passage_body(c) for c in chunks]
    digest = hashlib.sha1(("\n".join(texts) + key).encode()).hexdigest()[:12]
    path = CACHE / f"{key}-{digest}.npy"
    if path.exists():
        return np.load(path)
    CACHE.mkdir(parents=True, exist_ok=True)
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
    np.save(path, vectors)
    return vectors


def evaluate(rankings: dict[str, list[str]], questions: list[dict]) -> tuple[float, float, float]:
    rows = [score(rankings[q["id"]], q["esperados"]) for q in questions]
    return (sum(r["hit"] for r in rows) / len(rows), statistics.mean(r["coverage"] for r in rows),
            statistics.mean(r["rr"] for r in rows))


def run(keys: list[str], rerank: bool, sets: list[str], pool_size: int = POOL) -> None:
    started = time.perf_counter()
    chunks = build_chunks()
    questions = {s: load_set(s) for s in sets}
    reranker = CrossEncoder(RERANKER, device="cpu", max_length=1024) if rerank else None
    print(f"{'modelo':<22}{'conjunto':<11}{'n':>3}{'hit@5':>8}{'cobert@5':>10}{'MRR':>7}")
    for key in keys:
        hf_id, qprefix, _ = MODELS[key]
        model = SentenceTransformer(hf_id, device="cpu")
        vectors = embed_chunks(key, model, chunks)
        for setname, qs in questions.items():
            qvec = model.encode([qprefix + q["pregunta"] for q in qs], normalize_embeddings=True)
            ranked_first, ranked_rerank = {}, {}
            for q, v in zip(qs, qvec):
                order = np.argsort(-(vectors @ v))
                ids = [chunks[i]["id"] for i in order]
                ranked_first[q["id"]] = articles_in_order(ids)
                if reranker is not None:
                    pool = order[:pool_size]
                    scores = reranker.predict([(q["pregunta"], passage_body(chunks[i])) for i in pool])
                    print(f"  rerank {q['id']}: {time.perf_counter() - started:.0f} s acumulados", flush=True)
                    ranked_rerank[q["id"]] = articles_in_order([chunks[pool[i]]["id"] for i in np.argsort(-scores)])
            h, c, m = evaluate(ranked_first, qs)
            print(f"{key:<22}{setname:<11}{len(qs):>3}{h:>8.2f}{c:>10.2f}{m:>7.2f}")
            if reranker is not None:
                h, c, m = evaluate(ranked_rerank, qs)
                print(f"{key + ' + rerank':<22}{setname:<11}{len(qs):>3}{h:>8.2f}{c:>10.2f}{m:>7.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", choices=list(MODELS))
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--sets", nargs="+", default=["questions", "blind"], choices=list(SETS))
    parser.add_argument("--pool", type=int, default=POOL, help="chunks sent to the reranker per question")
    args = parser.parse_args()
    run(args.models, args.rerank, args.sets, args.pool)
