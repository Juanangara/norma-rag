"""The evaluation set must point at articles that exist, and keep its intended balance."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIPOS = {"respondible", "referencia", "multiple", "sin_respuesta", "parcial", "premisa_falsa"}
COMPORTAMIENTOS = {"responder", "rechazar", "responder_con_limite", "corregir"}


def questions():
    with (ROOT / "eval" / "questions.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def corpus_keys():
    keys = set()
    for path in (ROOT / "corpus" / "articles").glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            keys |= {f"{a['norma_id']}:{a['articulo']}" for a in map(json.loads, f)}
    return keys


def test_ids_are_unique():
    ids = [q["id"] for q in questions()]
    assert len(ids) == len(set(ids))


def test_fields_and_values_are_valid():
    for q in questions():
        assert q["tipo"] in TIPOS, q["id"]
        assert q["comportamiento"] in COMPORTAMIENTOS, q["id"]
        assert q["pregunta"].strip(), q["id"]


def test_expected_articles_exist_in_the_corpus():
    keys = corpus_keys()
    for q in questions():
        for e in q["esperados"]:
            assert e in keys, (q["id"], e)


def test_questions_that_must_be_refused_expect_no_article():
    for q in questions():
        if q["comportamiento"] == "rechazar":
            assert q["esperados"] == [] and q["respuesta_clave"] is None, q["id"]


def test_questions_with_an_answer_expect_an_article_or_a_correction():
    for q in questions():
        if q["comportamiento"] in {"responder", "responder_con_limite"}:
            assert q["esperados"], q["id"]
            assert q["respuesta_clave"], q["id"]


def test_balance_of_types():
    counts = Counter(q["tipo"] for q in questions())
    assert counts["respondible"] >= 25
    assert counts["sin_respuesta"] >= 5
    assert counts["premisa_falsa"] >= 3


def blind():
    return load_file("blind") + load_file("heldout")


def load_file(name):
    with (ROOT / "eval" / f"{name}.jsonl").open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def test_blind_set_points_at_existing_articles_and_has_unique_ids():
    keys = corpus_keys()
    rows = blind()
    assert len({q["id"] for q in rows}) == len(rows)
    for q in rows:
        assert q["comportamiento"] in COMPORTAMIENTOS, q["id"]
        for e in q["esperados"] + q["opcionales"]:
            assert e in keys, (q["id"], e)


def test_blind_questions_that_must_be_refused_expect_no_article():
    for q in blind():
        if q["comportamiento"] == "rechazar":
            assert q["esperados"] == [], q["id"]
        else:
            assert q["esperados"], q["id"]
