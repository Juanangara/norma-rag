"""Build corpus/articles/*.jsonl from corpus/raw/*. Run: python -m ingest.build"""
import json
from pathlib import Path

from ingest import parse_decreto, parse_ley

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "corpus" / "raw"
OUT = ROOT / "corpus" / "articles"

SOURCES = [
    (
        "ley_1581_2012",
        RAW / "ley_1581_2012.suin.txt",
        parse_ley.parse,
        {"nombre": "SUIN-Juriscol", "url": "https://www.suin-juriscol.gov.co/viewDocument.asp?ruta=Leyes/1684507", "consultado": "2024-11-06"},
    ),
    (
        "decreto_1074_2015_cap25",
        RAW / "decreto_1074_2015_cap25.funcionpublica.txt",
        parse_decreto.parse,
        {"nombre": "Función Pública, Gestor Normativo", "url": "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=76608", "consultado": "2026-10-26"},
    ),
]


def build() -> dict[str, int]:
    OUT.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, path, parse, fuente in SOURCES:
        articles = parse(path.read_text(encoding="utf-8"), fuente)
        with (OUT / f"{name}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for a in articles:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        counts[name] = len(articles)
    return counts


if __name__ == "__main__":
    for name, n in build().items():
        print(f"{name}: {n} articulos")
