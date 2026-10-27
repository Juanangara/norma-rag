"""Score the cached answers (eval/run_answers.py) under each combination of defenses, without generating.

    python -m eval.score_answers [--floor 0.45] [--support 0.6] [--detail]

Automatic measures only: whether it answered or refused, and whether the sources it shows include an
article the question's label expects. Whether the *content* is right needs a reader; see REPORT.md.
"""
import argparse
import json
import statistics

from app import answer as A
from app import verify as V
from app.generate import Answer
from app.retrieve import Hit
from eval.run_answers import CACHE
from eval.run_retrieval import ROOT


def load_questions() -> dict[str, dict]:
    rows = {}
    for name in ("questions", "blind", "heldout"):
        for line in (ROOT / "eval" / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            q = json.loads(line)
            rows[q["id"]] = {**q, "set": name}
    return rows


def load_traces() -> list[dict]:
    qs = load_questions()
    traces = []
    for path in sorted(CACHE.glob("*.json")):
        t = json.loads(path.read_text(encoding="utf-8"))
        hits = [Hit(id=h["id"], norma_id=h["norma_id"], norma=h["norma"], articulo=h["articulo"], parte=1,
                    titulo_articulo=h["titulo_articulo"], estructura="", texto=h["texto"], equivalencias={},
                    sim=h["sim"], score=h["score"], via=h["via"]) for h in t["hits"]]
        traces.append({"q": qs[t["id"]], "hits": hits, "answer": Answer(**t["answer"])})
    return traces


def run(trace: dict, floor: float, use_floor: bool, use_verify: bool) -> A.Result:
    hits, answer = trace["hits"], trace["answer"]
    if use_floor and A.out_of_scope(hits, floor):
        return A.refusal("fuera_de_alcance")
    return A.decide(hits, answer, use_verify)


def grounded(trace: dict, result: A.Result) -> bool:
    wanted = set(trace["q"]["esperados"] + trace["q"].get("opcionales", []))
    return any(f"{h.norma_id}:{h.articulo}" in wanted for h in trace["hits"]
               if any(f["id_chunk"] == h.id for f in result.fuentes))


def main(floor: float, support: float, detail: bool, sets: list[str]) -> None:
    V.MIN_SUPPORT = support
    traces = [t for t in load_traces() if t["q"]["set"] in sets]
    print(f"{len(traces)} respuestas; umbral de similitud={floor}; apoyo minimo={support}\n")
    if detail:
        for t in traces:
            v = V.verify(t["answer"], t["hits"])
            top = A.top_similarity(t["hits"])
            print(f"{t['q']['id']:<4}{t['q']['comportamiento']:<22} sim={top:.3f} apoyo={v.support:.2f} "
                  f"{'ok ' if v.ok else 'NO '} fuentes={[c['articulo'] for c in v.cited]} {'; '.join(v.problems)[:70]}")
        print()
    groups = {
        "rechazar": [t for t in traces if t["q"]["comportamiento"] == "rechazar"],
        "responder": [t for t in traces if t["q"]["comportamiento"] == "responder"],
        "con limite / corregir": [t for t in traces if t["q"]["comportamiento"] in ("responder_con_limite", "corregir")],
    }
    print(f"{'defensas':<24}{'rechazar: rechaza':>19}{'responder: responde':>21}{'  y con fuente esperada':>24}{'limite/corregir: responde':>27}")
    for name, (f, v) in {"ninguna": (False, False), "solo capa 1": (True, False), "solo capa 3": (False, True),
                         "capas 1 y 3": (True, True)}.items():
        out = {g: [(t, run(t, floor, f, v)) for t in ts] for g, ts in groups.items()}
        refused = sum(r.estado == "rechazada" for _, r in out["rechazar"])
        ans = [(t, r) for t, r in out["responder"] if r.estado == "respondida"]
        ok = sum(grounded(t, r) for t, r in ans)
        lim = sum(r.estado == "respondida" for _, r in out["con limite / corregir"])
        print(f"{name:<24}{refused:>10}/{len(out['rechazar']):<8}{len(ans):>12}/{len(out['responder']):<8}"
              f"{ok:>16}/{len(out['responder']):<7}{lim:>18}/{len(out['con limite / corregir'])}")
    grade_of = {}
    for name in ("grades_answers.json", "grades_heldout.json"):
        path = ROOT / "eval" / name
        if path.exists():
            grades = json.loads(path.read_text(encoding="utf-8"))
            grade_of |= {i: g for g in ("ok", "mal", "vacia") for i in grades[g]}
    if any(t["q"]["id"] not in grade_of for t in traces):
        print("\nrevision manual: faltan notas para estas respuestas, no se calcula")
        return
    print("\nrevision manual (grades_answers.json, no es de un abogado)")
    print(f"{'defensas':<24}{'se muestran':>13}{'  correctas':>12}{'  malas':>8}{'  vacias':>9}{'  correctas bloqueadas':>24}{'  malas bloqueadas':>18}")
    for name, (f, v) in {"ninguna": (False, False), "solo capa 1": (True, False), "solo capa 3": (False, True),
                         "capas 1 y 3": (True, True)}.items():
        shown = {"ok": 0, "mal": 0, "vacia": 0}
        blocked = {"ok": 0, "mal": 0, "vacia": 0}
        for t in traces:
            side = shown if run(t, floor, f, v).estado == "respondida" else blocked
            side[grade_of[t["q"]["id"]]] += 1
        print(f"{name:<24}{sum(shown.values()):>13}{shown['ok']:>12}{shown['mal']:>8}{shown['vacia']:>9}"
              f"{blocked['ok']:>24}{blocked['mal']:>18}")
    sims = [A.top_similarity(t["hits"]) for t in traces]
    print(f"\nsimilitud del mejor articulo: min={min(sims):.3f} mediana={statistics.median(sims):.3f} max={max(sims):.3f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--floor", type=float, default=A.FLOOR)
    p.add_argument("--support", type=float, default=V.MIN_SUPPORT)
    p.add_argument("--detail", action="store_true")
    p.add_argument("--sets", nargs="+", default=["questions", "blind"], choices=["questions", "blind", "heldout"])
    a = p.parse_args()
    main(a.floor, a.support, a.detail, a.sets)
