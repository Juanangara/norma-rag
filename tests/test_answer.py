"""Layer 1 and the shape of the result, with synthetic hits (no database, no model)."""
from app.answer import FLOOR, decide, out_of_scope, refusal
from app.generate import Answer
from app.retrieve import Hit


def hit(sim, via=None, texto="Se requiere la autorización previa e informada del Titular."):
    return Hit(id="a-art-9", norma_id="ley", norma="Ley 1581 de 2012", articulo="9", parte=1,
               titulo_articulo="Autorización", estructura="", texto=texto, equivalencias={}, sim=sim,
               via=via or ["vector"])


def test_a_question_far_from_every_article_is_out_of_scope():
    assert out_of_scope([hit(FLOOR - 0.01), hit(0.2)])
    assert not out_of_scope([hit(FLOOR + 0.01)])


def test_an_explicit_article_reference_is_never_out_of_scope():
    assert not out_of_scope([hit(0.1, via=["referencia"])])


def test_a_summary_that_fails_verification_is_replaced_by_a_refusal_with_the_articles():
    wrong = Answer("Las centrales de riesgo conservan reportes crediticios históricos.", ["S1P1"], "", 0.0)
    result = decide([hit(0.6)], wrong)
    assert result.estado == "rechazada" and result.motivo == "no_verificada"
    assert result.fuentes[0]["texto"].startswith("Se requiere")


def test_a_supported_summary_is_shown_with_its_source():
    good = Answer("Se requiere la autorización previa e informada del Titular.", ["S1P1"], "", 0.0)
    result = decide([hit(0.6)], good)
    assert result.estado == "respondida"
    assert result.fuentes[0]["articulo"] == "9"


def test_every_refusal_says_it_is_not_legal_advice():
    assert "asesoría legal" in refusal("fuera_de_alcance").aviso
