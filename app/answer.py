"""What the person gets, and the defenses behind it.

The main result is the law itself: the articles closest to the question, verbatim, with their source.
That part does not depend on the language model, and retrieval is the part that measured well
(eval/REPORT.md, sections 4 and 6). A generated summary is optional, always labelled as automatic,
and only shown if it passes the checks, because on held-out non-lawyer questions every summary that
passed was still wrong (section 8).

1. Enough evidence: when even the best article is far from the question, say so and show nothing.
2. Constrained generation (app.generate): bounded JSON, no free-form text.
3. Verification (app.verify): the summary must be supported by the retrieved paragraphs.
"""
from dataclasses import dataclass, field

from app import retrieve as R
from app.generate import SOURCES, Answer, generate
from app.verify import Verdict, verify

# Best-article cosine similarity (bge-m3) under which the question is treated as out of scope.
# Calibrated on the development sets only; see eval/REPORT.md.
FLOOR = 0.45
DISCLAIMER = ("Información orientativa basada en la Ley 1581 de 2012 y el Decreto 1074 de 2015 (capítulo 25). "
              "No es asesoría legal; para un caso concreto consulta a un abogado.")


@dataclass
class Result:
    estado: str                      # "respondida" | "rechazada"
    motivo: str                      # why it was refused: "fuera_de_alcance" | "no_verificada" | ""
    mensaje: str                     # what the person reads
    respuesta: str = ""
    fuentes: list[dict] = field(default_factory=list)
    problemas: list[str] = field(default_factory=list)
    confianza: str = ""              # "alta" | "media" | ""
    aviso: str = DISCLAIMER


def top_similarity(hits: list[R.Hit]) -> float:
    return max((h.sim for h in hits), default=0.0)


def out_of_scope(hits: list[R.Hit], floor: float = FLOOR) -> bool:
    """Layer 1. An explicit reference ("artículo 9 del Decreto 1377") has its own evidence."""
    if any("referencia" in h.via for h in hits):
        return False
    return top_similarity(hits) < floor


def refusal(motivo: str, problemas: list[str] | None = None) -> Result:
    message = {
        "fuera_de_alcance": "No encontré en la Ley 1581 de 2012 ni en el Decreto 1074 de 2015 (cap. 25) "
                            "nada que responda esta pregunta, así que prefiero no inventar una respuesta.",
        "no_verificada": "Encontré artículos relacionados, pero no pude armar una respuesta que se apoye "
                         "con seguridad en ellos. Te los muestro para que los leas directamente.",
    }[motivo]
    return Result("rechazada", motivo, message, problemas=problemas or [])


def decide(hits: list[R.Hit], answer: Answer, use_verification: bool = True) -> Result:
    """Layer 3 and presentation, given an already generated answer."""
    verdict: Verdict = verify(answer, hits)
    if use_verification and not verdict.ok:
        result = refusal("no_verificada", verdict.problems)
        result.fuentes = [{"articulo": h.articulo, "norma": h.norma, "titulo": h.titulo_articulo, "texto": h.texto}
                          for h in hits[:2]]
        return result
    return Result("respondida", "", answer.respuesta, answer.respuesta, verdict.cited, verdict.problems,
                  "alta" if verdict.support >= 0.85 and verdict.ok else "media")


SUMMARY_LABEL = ("Resumen automático de un modelo pequeño (1B) que corre en tu equipo. Puede equivocarse, "
                 "incluso al invertir el sentido de la ley; lo que vale es el texto de los artículos.")
CLOSEST_NOTE = "Estos son los artículos más cercanos a tu pregunta; pueden no responderla del todo."


@dataclass
class Search:
    """What the person sees: the closest articles, and optionally a checked summary."""
    en_alcance: bool
    mensaje: str
    fuentes: list[dict] = field(default_factory=list)   # articles, verbatim, best first
    resumen: Result | None = None
    resumen_nota: str = ""
    aviso: str = DISCLAIMER


def source_view(h: R.Hit) -> dict:
    return {"norma": h.norma, "articulo": h.articulo, "titulo": h.titulo_articulo, "texto": h.texto,
            "id_chunk": h.id, "similitud": round(h.sim, 3)}


def answer_question(conn, question: str, resumen: bool = False) -> Search:
    hits = R.retrieve(conn, question, k=SOURCES)
    if out_of_scope(hits):
        return Search(False, refusal("fuera_de_alcance").mensaje)
    search = Search(True, CLOSEST_NOTE, [source_view(h) for h in hits])
    if resumen:
        result = decide(hits, generate(question, hits))
        if result.estado == "respondida":
            search.resumen = result
            search.resumen_nota = SUMMARY_LABEL
        else:
            search.resumen_nota = ("No se muestra un resumen: el modelo no logró uno que se apoye en los "
                                   "artículos. " + " ".join(result.problemas))
    return search
