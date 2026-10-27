"""Look at what the local LLM answers for a few questions. Run: python -m eval.try_generate b01 q01 ...

Read-only inspection, not a score: it prints question, sources used, answer, and whether each quote is
literally in the cited article.
"""
import json
import sys

from app import retrieve as R
from app.generate import SOURCES, generate
from eval.run_retrieval import ROOT


def questions() -> dict[str, dict]:
    rows = {}
    for name in ("questions", "blind"):
        for line in (ROOT / "eval" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            q = json.loads(line)
            rows[q["id"]] = q
    return rows


def main(ids: list[str]) -> None:
    qs = questions()
    conn = R.connect()
    for qid in ids:
        q = qs[qid]
        hits = R.retrieve(conn, q["pregunta"], k=SOURCES)
        a = generate(q["pregunta"], hits)
        print(f"\n=== {qid} [{q['comportamiento']}] {q['pregunta'][:150]}")
        print("fuentes:", ", ".join(f"[{i}] {h.articulo}" for i, h in enumerate(hits, 1)))
        print(f"suficiente={a.suficiente} valido={a.valid}  ({a.seconds:.0f} s, {a.prompt_tokens} tokens de entrada, {a.completion_tokens} de salida)")
        print(a.respuesta or a.raw[-200:])
        for c in a.citas:
            n = c["fuente"]
            literal = c["cita"].strip() in hits[n - 1].texto if 1 <= n <= len(hits) else False
            print(f"  cita [{n}] literal={literal}: {c['cita'][:110]}")


if __name__ == "__main__":
    main(sys.argv[1:])
