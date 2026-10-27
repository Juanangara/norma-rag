"""Generate one answer per question with the local LLM and keep the trace, so the defenses can be
compared offline without generating again. Run: python -m eval.run_answers [questions blind ...]

Traces go to .cache/generations/<id>.json. Selection (the held-out set is run whole): every question that is not a plain "responder"
(refuse, correct, answer with a limit) plus one in three of the plain ones, in id order.
"""
import json
import sys
from dataclasses import asdict

from app import retrieve as R
from app.generate import SOURCES, generate
from eval.run_retrieval import ROOT

CACHE = ROOT / ".cache" / "generations"


def select(rows: list[dict], name: str = "") -> list[dict]:
    if name == "heldout":      # the confirmation set is run whole: no choosing which questions count
        return sorted(rows, key=lambda q: q["id"])
    plain = [q for q in rows if q["comportamiento"] == "responder"][::3]
    other = [q for q in rows if q["comportamiento"] != "responder"]
    return sorted(plain + other, key=lambda q: q["id"])


def main(sets: list[str]) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    conn = R.connect()
    for name in sets:
        rows = [json.loads(l) for l in (ROOT / "eval" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines()]
        for q in select(rows, name):
            path = CACHE / f"{q['id']}.json"
            if path.exists():
                continue
            hits = R.retrieve(conn, q["pregunta"], k=SOURCES)
            answer = generate(q["pregunta"], hits)
            path.write_text(json.dumps({
                "id": q["id"], "set": name,
                "hits": [{"id": h.id, "norma": h.norma, "norma_id": h.norma_id, "articulo": h.articulo,
                          "titulo_articulo": h.titulo_articulo, "texto": h.texto, "sim": h.sim, "via": h.via,
                          "score": h.score} for h in hits],
                "answer": asdict(answer),
            }, ensure_ascii=False), encoding="utf-8")
            print(f"{q['id']} {q['comportamiento']:<22} {answer.seconds:>4.0f} s valid={answer.valid}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["questions", "blind"])
