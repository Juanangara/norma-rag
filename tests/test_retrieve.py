"""Needs the database up and loaded (docker compose up -d; python -m ingest.load). Skipped otherwise."""
import pytest

psycopg = pytest.importorskip("psycopg")


@pytest.fixture(scope="module")
def conn():
    try:
        from app.retrieve import connect
        c = connect()
        if c.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0:
            pytest.skip("chunks table is empty")
    except (psycopg.OperationalError, KeyError, psycopg.errors.UndefinedTable):
        pytest.skip("database not available")
    yield c
    c.close()


def top(conn, question, k=5):
    from app.retrieve import retrieve
    return retrieve(conn, question, k)


def test_old_decreto_1377_numbering_resolves_to_the_current_article(conn):
    hits = top(conn, "¿Qué dice el artículo 9 del Decreto 1377 de 2013 sobre la revocatoria?")
    assert hits[0].articulo == "2.2.2.25.2.6"
    assert "referencia" in hits[0].via


def test_article_of_the_law_is_returned_first(conn):
    assert top(conn, "¿Qué dice el artículo 5 de la Ley 1581?")[0].id == "ley-1581-2012-art-5"


def test_sensitive_data_article_is_in_the_top_5(conn):
    # The answer layer reads the top 5, so we assert recall@5 here, not rank 1.
    assert "ley-1581-2012-art-5" in [h.id for h in top(conn, "¿Qué se considera un dato sensible?")]


def test_responsable_question_finds_the_definition_in_the_top_5(conn):
    # Art. 3 is chunked one definition per chunk; before that it ranked 8th (see eval/REPORT.md).
    hits = top(conn, "¿Quién es el Responsable del Tratamiento de datos personales?")
    assert any(h.id.startswith("ley-1581-2012-art-3-p") and "Responsable del Tratamiento:" in h.texto for h in hits)


def test_hits_expose_similarity_for_thresholding(conn):
    hits = top(conn, "¿Qué derechos tiene el titular de los datos?")
    assert all(-1.0 <= h.sim <= 1.0 for h in hits)
