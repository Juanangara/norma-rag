"""Find explicit article references in a question, e.g. "artículo 9 del Decreto 1377 de 2013".

Pure text logic, no database. It returns what to look up; app.retrieve does the lookup.
A reference to the old Decreto 1377 numbering is resolved through the `equivalencias` field.
"""
import re
from dataclasses import dataclass

DOTTED = re.compile(r"\b2\.2\.2\.25\.\d+\.\d+\b")
ARTICULO_N = re.compile(r"\bart(?:[ií]culos?|\.)\s*(\d{1,2})\b", re.IGNORECASE)
D1377 = re.compile(r"\b1377\b")
LEY = re.compile(r"\bley\b|\b1581\b", re.IGNORECASE)
D1074 = re.compile(r"\b1074\b")


@dataclass(frozen=True)
class Reference:
    norma_id: str   # corpus norma_id
    articulo: str   # current numbering
    via_1377: bool = False


def find_references(question: str) -> list[Reference]:
    refs = [Reference("decreto-1074-2015-cap25", d) for d in DOTTED.findall(question)]
    numbers = ARTICULO_N.findall(question)
    if not numbers:
        return refs
    # A bare "artículo N" with no norma named is ambiguous, so we do not guess.
    if D1377.search(question):
        refs += [Reference("decreto-1074-2015-cap25", n, via_1377=True) for n in numbers]
    elif LEY.search(question) and not D1074.search(question):
        refs += [Reference("ley-1581-2012", n) for n in numbers]
    return refs
