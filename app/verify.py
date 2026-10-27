"""Defense 3: verify the generated answer against the retrieved articles, before showing it.

The sources shown are found by the system (see `attribute`), not taken from the model. Two checks:
figures that are not in those paragraphs, and an answer that talks about things the retrieved
articles never mention.
"""
import re
import unicodedata
from dataclasses import dataclass, field

from app.generate import Answer, paragraphs
from app.retrieve import Hit

# Share of the answer's content words (by 6-letter stem) that the 3 best paragraphs must cover.
MIN_SUPPORT = 0.6
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
CODE = re.compile(r"S\d+P\d+")
WORD = re.compile(r"[a-zñ]{5,}")
# Frequent words that say nothing about the topic.
STOP = set("""
según deben puede pueden debe cuando donde entre sobre además cualquier tiene tienen siempre también
ejemplo manera mismo misma estos estas aquel aquella hacer hasta desde porque cuales cual quien
artículo artículos párrafo normas norma establece establecen indica indican señala dice dicen
""".split())


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


STOP_PLAIN = {plain(w) for w in STOP}


def stems(text: str) -> set[str]:
    return {w[:6] for w in WORD.findall(plain(text)) if w not in STOP_PLAIN}


def numbers(text: str) -> set[str]:
    return {n.rstrip(".,") for n in NUMBER.findall(CODE.sub(" ", text))}


@dataclass
class Verdict:
    ok: bool
    problems: list[str]
    cited: list[dict] = field(default_factory=list)   # what the answer rests on, verbatim from the corpus
    support: float = 0.0


def attribute(text: str, units: dict[str, str], limit: int = 3) -> tuple[list[str], float]:
    """Paragraphs that best cover what `text` says, and the share of its content words they cover.

    Greedy: take the paragraph with most of the answer's word stems, then the one adding most uncovered
    stems. The model's own citations are not used: a 1B model often copies from one article and cites
    another (it did on "¿qué es un dato sensible?"), so the sources shown are found, not claimed.
    """
    words = stems(text)
    if not words:
        return [], 0.0
    stems_of = {i: stems(t) & words for i, t in units.items()}
    chosen, covered = [], set()
    while len(chosen) < limit:
        best = max(stems_of, key=lambda i: len(stems_of[i] - covered), default=None)
        if best is None or not stems_of[best] - covered:
            break
        chosen.append(best)
        covered |= stems_of[best]
    return chosen, len(covered) / len(words)


def verify(answer: Answer, hits: list[Hit]) -> Verdict:
    if not answer.valid:
        return Verdict(False, ["La salida del modelo quedó cortada o mal formada."])
    units = paragraphs(hits)
    ids, support = attribute(answer.respuesta, units)
    if not ids:
        return Verdict(False, ["Ningún párrafo de los artículos respalda lo que dice la respuesta."])
    cited = []
    for i in ids:
        h = hits[int(i[1:i.index("P")]) - 1]
        cited.append({"id": i, "id_chunk": h.id, "norma": h.norma, "articulo": h.articulo,
                      "titulo": h.titulo_articulo, "texto": units[i]})
    # A figure is invented only if it is nowhere in what the model was shown.
    shown = " ".join(f"{h.norma} {h.articulo} {h.titulo_articulo} {h.texto}" for h in hits)

    problems = []
    missing = sorted(numbers(answer.respuesta) - numbers(shown))
    if missing:
        problems.append(f"Cifras que no están en los artículos recuperados: {', '.join(missing)}.")
    if support < MIN_SUPPORT:
        problems.append(f"Solo {support:.0%} de lo que dice la respuesta aparece en los artículos recuperados.")
    return Verdict(not problems, problems, cited, support)
