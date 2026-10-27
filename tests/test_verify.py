from app.generate import Answer
from app.retrieve import Hit
from app.verify import numbers, stems, verify


def hit(texto, articulo="9", titulo="Autorización"):
    return Hit(id=f"ley-art-{articulo}", norma_id="ley", norma="Ley 1581 de 2012", articulo=articulo, parte=1,
               titulo_articulo=titulo, estructura="", texto=texto, equivalencias={}, sim=0.5)


HITS = [
    hit("Se requiere la autorización previa e informada del Titular.\n\nEl plazo es de 15 días hábiles."),
    hit("Los datos sensibles no pueden tratarse sin consentimiento.", articulo="5", titulo="Datos sensibles"),
]


def answer(texto, citas, valid=True):
    return Answer(texto, citas, "", 0.0, valid=valid)


def test_a_supported_answer_passes_and_returns_the_cited_text_verbatim():
    v = verify(answer("Se requiere la autorización previa e informada del Titular.", ["S1P1"]), HITS)
    assert v.ok and v.problems == []
    assert v.cited[0]["texto"] == "Se requiere la autorización previa e informada del Titular."
    assert v.cited[0]["articulo"] == "9"


def test_a_number_that_is_nowhere_in_the_retrieved_articles_is_rejected():
    v = verify(answer("La autorización previa e informada del Titular se resuelve en 30 días.", ["S1P1"]), HITS)
    assert not v.ok
    assert "30" in v.problems[0]


def test_a_number_in_the_cited_paragraph_is_accepted():
    v = verify(answer("El plazo es de 15 días hábiles.", ["S1P2"]), HITS)
    assert v.ok, v.problems


def test_the_article_label_counts_as_evidence_for_numbers():
    v = verify(answer("La autorización previa del Titular está en la Ley 1581 de 2012.", ["S1P1"]), HITS)
    assert v.ok


def test_an_answer_about_things_the_citation_never_mentions_is_rejected():
    v = verify(answer("Las centrales de riesgo financiero conservan reportes crediticios históricos.", ["S1P1"]), HITS)
    assert not v.ok and v.problems


def test_an_answer_only_partly_supported_reports_how_much():
    v = verify(answer("Se requiere autorización previa del Titular, además de reportes crediticios históricos "
                      "sobre centrales financieras bancarias.", ["S1P1"]), HITS)
    assert not v.ok and "aparece" in v.problems[0]


def test_the_sources_shown_are_found_not_taken_from_the_models_citations():
    v = verify(answer("Los datos sensibles no pueden tratarse sin consentimiento.", ["S1P1"]), HITS)
    assert v.ok
    assert v.cited[0]["id"] == "S2P1" and v.cited[0]["articulo"] == "5"


def test_an_answer_with_no_content_words_to_check_is_rejected():
    assert not verify(answer("Sí.", ["S1P1"]), HITS).ok


def test_paragraph_codes_written_in_the_answer_are_not_figures():
    v = verify(answer("Se requiere la autorización previa e informada del Titular (S1P1).", ["S1P1"]), HITS)
    assert v.ok, v.problems


def test_truncated_output_is_rejected():
    assert not verify(answer("", [], valid=False), HITS).ok


def test_numbers_and_stems_ignore_accents_case_and_trailing_punctuation():
    assert numbers("En 15 días, o 1.581.") == {"15", "1.581"}
    assert stems("AUTORIZACIÓN") == stems("autorizacion")
