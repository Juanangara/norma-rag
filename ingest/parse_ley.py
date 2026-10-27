"""Parse Ley 1581 de 2012 from the SUIN-Juriscol print (corpus/raw/ley_1581_2012.suin.txt).

The print has page headers/footers in the middle of sentences and, in two places,
swaps the order of consecutive articles (4/5 and 9/10). We therefore split on the
article headings and sort by article number instead of trusting the text order.
"""
import re

NORMA = "Ley 1581 de 2012"
NORMA_ID = "ley-1581-2012"

# Which TITULO each article belongs to. Taken from the Funcion Publica copy of the law,
# because the SUIN print places some headings next to the wrong article.
TITULOS = [
    ("TÍTULO I", "OBJETO, ÁMBITO DE APLICACIÓN Y DEFINICIONES", range(1, 4)),
    ("TÍTULO II", "PRINCIPIOS RECTORES", range(4, 5)),
    ("TÍTULO III", "CATEGORÍAS ESPECIALES DE DATOS", range(5, 8)),
    ("TÍTULO IV", "DERECHOS Y CONDICIONES DE LEGALIDAD PARA EL TRATAMIENTO DE DATOS", range(8, 14)),
    ("TÍTULO V", "PROCEDIMIENTOS", range(14, 17)),
    ("TÍTULO VI", "DEBERES DE LOS RESPONSABLES DEL TRATAMIENTO Y ENCARGADOS DEL TRATAMIENTO", range(17, 19)),
    ("TÍTULO VII", "DE LOS MECANISMOS DE VIGILANCIA Y SANCIÓN", range(19, 26)),
    ("TÍTULO VIII", "TRANSFERENCIA DE DATOS A TERCEROS PAÍSES", range(26, 27)),
    ("TÍTULO IX", "OTRAS DISPOSICIONES", range(27, 31)),
]

# CAPITULOs of TITULO VII. Their headings sit at the end of the previous article in the print.
CAPITULOS = [
    ("CAPÍTULO I", "De la autoridad de protección de datos", range(19, 22)),
    ("CAPÍTULO II", "Procedimiento y sanciones", range(22, 25)),
    ("CAPÍTULO III", "Del Registro Nacional de Bases de Datos", range(25, 26)),
]

PAGE_HEADER = re.compile(r"^\x0c?\d+/\d+/\d+,.*LEY 1581 DE 2012\s*$")
PAGE_URL = re.compile(r"^https://www\.suin-juriscol\.gov\.co/\S+")
PAGE_COUNTER = re.compile(r"\s+\d+/\d+\s*$")
TITULO_LINE = re.compile(r"^\s*(T[ÍI]TULO|CAP[ÍI]TULO) [IVX]+\b")
ARTICULO = re.compile(r"(?m)^\s*Art[ií]culo (\d+)[°º]?\.\s*")
FIRMA = "El Presidente del honorable Senado"


def _clean(raw: str) -> str:
    lines = []
    for line in raw.split("\n"):
        if PAGE_HEADER.match(line) or PAGE_URL.match(line):
            continue
        lines.append(PAGE_COUNTER.sub("", line))
    text = "\n".join(lines)
    return text[: text.index(FIRMA)]


def _drop_titulo_headings(text: str) -> str:
    names = {nombre for _, nombre, _ in TITULOS} | {nombre for _, nombre, _ in CAPITULOS}
    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if TITULO_LINE.match(line) or stripped in names:
            continue
        kept.append(line)
    return "\n".join(kept)


def _paragraphs(block: str) -> str:
    """Join hard-wrapped lines; keep blank lines as paragraph breaks."""
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", block)]
    return "\n\n".join(p for p in paras if p)


def _estructura(numero: int) -> str:
    for titulo, nombre, rango in TITULOS:
        if numero in rango:
            estructura = f"{titulo} - {nombre}"
            for capitulo, cap_nombre, cap_rango in CAPITULOS:
                if numero in cap_rango:
                    estructura += f" / {capitulo} - {cap_nombre}"
            return estructura
    raise ValueError(f"articulo {numero} sin titulo")


def parse(raw: str, fuente: dict) -> list[dict]:
    text = _drop_titulo_headings(_clean(raw))
    heads = list(ARTICULO.finditer(text))
    articles = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = _paragraphs(text[m.end():end])
        titulo, _, resto = body.partition(". ")
        numero = int(m.group(1))
        articles.append({
            "id": f"{NORMA_ID}-art-{numero}",
            "norma": NORMA,
            "norma_id": NORMA_ID,
            "articulo": str(numero),
            "orden": numero,
            "titulo_articulo": titulo.strip(),
            "estructura": _estructura(numero),
            "texto": resto.strip(),
            "equivalencias": {},
            "origen": NORMA,
            "fuente": fuente,
        })
    articles.sort(key=lambda a: a["orden"])
    return articles
