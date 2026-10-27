"""Measure retrieval on eval/questions.jsonl. Run: python -m eval.run_retrieval

Scores at article level (parts of one article count once). Only questions with expected
articles are scored. Questions that must be refused are used to look at similarity instead.
"""
import json
import re
import statistics
from pathlib import Path

from app import retrieve as R
from ingest import embed

ROOT = Path(__file__).resolve().parent.parent
K = 5
PART_SUFFIX = re.compile(r"-p\d+$")
LEX_NORMS = [0, 1, 2, 4, 8, 32]
WEIGHTS = {
    "solo vector": {"vector": 1.0, "texto": 0.0},
    "solo texto": {"vector": 0.0, "texto": 1.0},
    "1:1": {"vector": 1.0, "texto": 1.0},
    "2:1": {"vector": 2.0, "texto": 1.0},
    "3:1": {"vector": 3.0, "texto": 1.0},
}


def article_of(chunk_id: str) -> str:
    """'ley-1581-2012-art-4-p2' -> 'ley-1581-2012:4'"""
    norma, _, resto = chunk_id.partition("-art-")
    return f"{norma}:{PART_SUFFIX.sub('', resto)}"


def articles_in_order(chunk_ids: list[str]) -> list[str]:
    seen = []
    for cid in chunk_ids:
        a = article_of(cid)
        if a not in seen:
            seen.append(a)
    return seen


def score(ranked: list[str], expected: list[str]) -> dict:
    top = ranked[:K]
    found = [e for e in expected if e in top]
    first = next((i for i, a in enumerate(ranked, 1) if a in expected), None)
    return {"hit": bool(found), "coverage": len(found) / len(expected), "rr": 1 / first if first else 0.0}


def short(article: str) -> str:
    return article.replace("decreto-1074-2015-cap25:", "D").replace("ley-1581-2012:", "L")


def main(path: Path) -> None:
    questions = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
    conn = R.connect()
    cands, sims = {}, {}
    for q in questions:
        v = embed.embed_query(q["pregunta"])
        cands[q["id"]] = {n: R.rank_candidates(conn, q["pregunta"], v, n) for n in LEX_NORMS}
        top = R._ids(conn, R.VECTOR_SQL, {"v": v, "n": 1})[0]
        sims[q["id"]] = conn.execute(
            "SELECT 1 - (embedding <=> %s::vector) FROM chunks WHERE id = %s", (v, top)).fetchone()[0]

    scored = [q for q in questions if q["esperados"]]
    print(f"{path.name}: {len(scored)} preguntas con articulo esperado; K={K}; nivel articulo\n")
    print(f"{'configuracion':<22}{'norm':>5}{'hit@5':>8}{'cobert@5':>10}{'MRR':>7}{'util@5':>8}")
    for wname, w in WEIGHTS.items():
        norms = [0] if wname == "solo vector" else LEX_NORMS
        for n in norms:
            rows = []
            for q in scored:
                s, _ = R.fuse(cands[q["id"]][n], w)
                ranked = articles_in_order(sorted(s, key=s.get, reverse=True))
                r = score(ranked, q["esperados"])
                r["util"] = any(a in ranked[:K] for a in q["esperados"] + q.get("opcionales", []))
                rows.append(r)
            m = (sum(r["hit"] for r in rows) / len(rows), statistics.mean(r["coverage"] for r in rows),
                 statistics.mean(r["rr"] for r in rows), sum(r["util"] for r in rows) / len(rows))
            print(f"{wname:<22}{'-' if wname == 'solo vector' else n:>5}{m[0]:>8.2f}{m[1]:>10.2f}{m[2]:>7.2f}{m[3]:>8.2f}")

    print("\nsimilitud del mejor chunk (solo vector)")
    if "tipo" in questions[0]:
        for tipo, label in (("respondible", "respondibles"), ("sin_respuesta", "sin respuesta"), ("premisa_falsa", "premisa falsa"), ("parcial", "parcial")):
            vals = sorted(sims[q["id"]] for q in questions if q["tipo"] == tipo)
            print(f"  {label:<14} n={len(vals):<3} min={vals[0]:.3f} mediana={statistics.median(vals):.3f} max={vals[-1]:.3f}")
        ans = [sims[q["id"]] for q in questions if q["tipo"] in ("respondible", "referencia", "multiple")]
        no = [sims[q["id"]] for q in questions if q["tipo"] == "sin_respuesta"]
        print(f"  solapamiento: la mayor similitud sin respuesta ({max(no):.3f}) vs la menor respondible ({min(ans):.3f})")
    else:
        vals = sorted(sims.values())
        print(f"  n={len(vals)} min={vals[0]:.3f} mediana={statistics.median(vals):.3f} max={vals[-1]:.3f}")
        print("\nposicion de cada articulo esperado (solo vector); '-' = fuera del top 30")
        for q in questions:
            s, _ = R.fuse(cands[q["id"]][0], WEIGHTS["solo vector"])
            ranked = articles_in_order(sorted(s, key=s.get, reverse=True))
            pos = " ".join(f"{short(e)}={ranked.index(e) + 1 if e in ranked else '-'}" for e in q["esperados"]) or "(debe rechazar)"
            print(f"  {q['id']} sim={sims[q['id']]:.3f}  {pos}")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "questions.jsonl")
