"""Parse Capitulo 25 of Decreto 1074 de 2015 (corpus/raw/decreto_1074_2015_cap25.funcionpublica.txt).

Each article ends with a source note such as "(Decreto 1377 de 2013, art. 5)". We keep it as
`equivalencias` so a question about the old numbering can be answered with the current article.
Section 7 was added by Decreto 255 de 2022 and has no such note.
"""
import re

NORMA = "Decreto 1074 de 2015, capítulo 25"
NORMA_ID = "decreto-1074-2015-cap25"

SECCION = re.compile(r'^"?SECCIÓN (\d+)\s*$')
ARTICULO = re.compile(r"^ARTÍCULO (2\.2\.2\.25\.(\d+)\.(\d+))\.\s+(.*)$")
NOTA_1377 = re.compile(r"^\(Decreto 1377 de 2013, art\. (\d+)\)$")
NOTA_ADICION = re.compile(r"^\(Adicionada por el Art\.(\d+), (Decreto \d+ de \d{4})\)$")


def parse(raw: str, fuente: dict) -> list[dict]:
    seccion_num, seccion_nombre = None, None
    pending_name = False
    adicion = None
    current = None
    articles = []

    def close():
        nonlocal current
        if current is None:
            return
        current["texto"] = "\n\n".join(current.pop("_paras")).strip().rstrip('"').strip()
        articles.append(current)
        current = None

    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = SECCION.match(line)
        if m:
            close()
            seccion_num, seccion_nombre, pending_name, adicion = int(m.group(1)), None, True, None
            continue
        if pending_name:
            if NOTA_ADICION.match(line):
                a = NOTA_ADICION.match(line)
                adicion = f"{a.group(2)}, art. {a.group(1)}"
                continue
            seccion_nombre, pending_name = line.rstrip('"'), False
            continue
        m = ARTICULO.match(line)
        if m:
            close()
            titulo, _, resto = m.group(4).partition(". ")
            current = {
                "id": f"{NORMA_ID}-art-{m.group(1)}",
                "norma": NORMA,
                "norma_id": NORMA_ID,
                "articulo": m.group(1),
                "orden": int(m.group(2)) * 100 + int(m.group(3)),
                "titulo_articulo": titulo.strip(),
                "estructura": f"SECCIÓN {seccion_num} - {seccion_nombre}",
                "equivalencias": {},
                "origen": adicion,
                "fuente": fuente,
                "_paras": [resto] if resto else [],
            }
            continue
        if current is None:
            continue
        n = NOTA_1377.match(line)
        if n:
            current["equivalencias"]["decreto_1377_2013"] = int(n.group(1))
            current["origen"] = f"Decreto 1377 de 2013, art. {n.group(1)}"
            continue
        current["_paras"].append(line)
    close()
    for a in articles:
        a["texto"] = a["texto"].strip()
    return articles
