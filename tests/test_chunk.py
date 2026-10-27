from ingest.chunk import chunk_article, split_text


def words(s):
    return len(s.split())


def article(texto):
    return {"id": "x-art-1", "norma": "N", "articulo": "1", "titulo_articulo": "T", "texto": texto}


def test_short_article_is_one_chunk_with_same_id():
    chunks = chunk_article(article("uno dos tres"), words, limit=50)
    assert len(chunks) == 1
    assert chunks[0]["id"] == "x-art-1"
    assert chunks[0]["parte"] == 1


def test_long_article_splits_on_paragraphs_and_keeps_all_text():
    paras = [f"p{i} " + "palabra " * 10 for i in range(6)]
    chunks = chunk_article(article("\n\n".join(paras)), words, limit=30)
    assert len(chunks) > 1
    assert [c["id"] for c in chunks] == [f"x-art-1-p{i}" for i in range(1, len(chunks) + 1)]
    assert "\n\n".join(c["texto"] for c in chunks) == "\n\n".join(paras)


def test_every_part_repeats_the_heading_and_fits_the_limit():
    paras = ["palabra " * 10 for _ in range(6)]
    for c in chunk_article(article("\n\n".join(paras)), words, limit=30):
        assert c["embedding_text"].startswith("N, artículo 1. T.")
        assert words(c["embedding_text"]) <= 30


def test_definitions_become_one_chunk_each_and_keep_the_intro():
    a = {**article("Para los efectos, se entiende por:\n\na) Uno: algo.\n\nb) Dos: otra cosa."),
         "titulo_articulo": "Definiciones"}
    chunks = chunk_article(a, words, limit=450)
    assert [c["id"] for c in chunks] == ["x-art-1-p1", "x-art-1-p2"]
    assert chunks[1]["texto"] == "Para los efectos, se entiende por:\n\nb) Dos: otra cosa."
    assert "a) Uno" not in chunks[1]["embedding_text"]


def test_a_paragraph_longer_than_the_limit_is_split_on_sentences():
    texto = " ".join(f"Frase {i} con varias palabras aqui." for i in range(12))
    parts = split_text(texto, words, 20)
    assert len(parts) > 1
    assert " ".join(parts) == texto
