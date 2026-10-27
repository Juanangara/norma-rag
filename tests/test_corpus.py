"""Checks on the parsed corpus. They encode what was verified by hand against a second copy of the law."""
import json
import re
from pathlib import Path

import pytest

ARTICLES = Path(__file__).resolve().parent.parent / "corpus" / "articles"


def load(name):
    with (ARTICLES / f"{name}.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


@pytest.fixture(scope="module")
def ley():
    return load("ley_1581_2012")


@pytest.fixture(scope="module")
def decreto():
    return load("decreto_1074_2015_cap25")


def test_ley_has_articles_1_to_30_in_order(ley):
    assert [a["articulo"] for a in ley] == [str(n) for n in range(1, 31)]


def test_decreto_has_35_articles_without_duplicates(decreto):
    ids = [a["articulo"] for a in decreto]
    assert len(ids) == 35
    assert len(set(ids)) == 35


def test_decreto_sections_1_to_7(decreto):
    secciones = {a["estructura"].split(" - ")[0] for a in decreto}
    assert secciones == {f"SECCIÓN {n}" for n in range(1, 8)}


def test_ley_articles_land_in_the_right_titulo(ley):
    by = {a["articulo"]: a["estructura"] for a in ley}
    assert by["4"].startswith("TÍTULO II")
    assert by["5"].startswith("TÍTULO III")  # SUIN prints art. 5 before art. 4
    assert by["13"].startswith("TÍTULO IV")
    assert by["26"].startswith("TÍTULO VIII")


def test_ley_known_titles(ley):
    by = {a["articulo"]: a["titulo_articulo"] for a in ley}
    assert by["5"] == "Datos sensibles"
    assert by["4"] == "Principios para el Tratamiento de datos personales"
    assert by["30"] == "Vigencia"


def test_ley_article_30_has_no_signatures(ley):
    art30 = ley[-1]["texto"]
    assert art30 == "La presente ley rige a partir de su promulgación."


def test_no_page_noise_left(ley, decreto):
    noise = re.compile(r"suin-juriscol|LEY 1581 DE 2012|\d+/204|\x0c|�|â¿")
    for a in ley + decreto:
        assert not noise.search(a["texto"]), a["id"]


def test_no_structure_headings_leaked_into_article_text(ley):
    # Arts. 18, 21 and 24 used to end with the heading of the next CAPITULO.
    leaked = re.compile(r"(T[ÍI]TULO|CAP[ÍI]TULO) [IVX]+")
    for a in ley:
        assert not leaked.search(a["texto"]), (a["id"], a["texto"][-80:])
    names = ("De la autoridad de protección de datos", "Procedimiento y sanciones",
             "Del Registro Nacional de Bases de Datos", "PRINCIPIOS RECTORES", "PROCEDIMIENTOS")
    for a in ley:
        assert not any(n in a["texto"] for n in names), a["id"]


def test_capitulos_are_recorded_in_estructura(ley):
    by = {a["articulo"]: a["estructura"] for a in ley}
    assert "CAPÍTULO I - De la autoridad" in by["19"]
    assert "CAPÍTULO II - Procedimiento y sanciones" in by["23"]
    assert "CAPÍTULO III" in by["25"]
    assert "CAPÍTULO" not in by["18"]


def test_no_empty_or_tiny_articles(ley, decreto):
    for a in ley + decreto:
        assert len(a["texto"]) > 40, a["id"]  # art. 30 of the law is one short sentence
        assert a["titulo_articulo"], a["id"]


def test_every_1377_article_from_1_to_27_is_mapped_once(decreto):
    mapped = sorted(a["equivalencias"]["decreto_1377_2013"] for a in decreto if a["equivalencias"])
    assert mapped == list(range(1, 28))


def test_section_7_comes_from_decreto_255(decreto):
    s7 = [a for a in decreto if a["estructura"].startswith("SECCIÓN 7")]
    assert len(s7) == 8
    assert all(a["origen"] == "Decreto 255 de 2022, art. 1" for a in s7)
    assert all(not a["equivalencias"] for a in s7)


def test_decreto_text_has_no_source_notes_or_stray_quotes(decreto):
    for a in decreto:
        assert "(Decreto 1377 de 2013, art." not in a["texto"], a["id"]
        assert not a["texto"].endswith('"'), a["id"]


def test_ids_are_unique_across_corpus(ley, decreto):
    ids = [a["id"] for a in ley + decreto]
    assert len(ids) == len(set(ids)) == 65
