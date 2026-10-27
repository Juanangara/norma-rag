from app.references import Reference, find_references

CAP25 = "decreto-1074-2015-cap25"


def test_old_numbering_of_decreto_1377():
    refs = find_references("¿Qué dice el artículo 9 del Decreto 1377 de 2013 sobre la revocatoria?")
    assert refs == [Reference(CAP25, "9", via_1377=True)]


def test_article_of_the_law():
    assert find_references("¿Qué establece el artículo 12 de la Ley 1581?") == [Reference("ley-1581-2012", "12")]


def test_full_dotted_number_needs_no_context():
    assert find_references("Explica el 2.2.2.25.2.6") == [Reference(CAP25, "2.2.2.25.2.6")]


def test_bare_article_number_is_ambiguous_and_not_guessed():
    assert find_references("¿Qué dice el artículo 5?") == []


def test_no_reference():
    assert find_references("¿Qué es un dato sensible?") == []


def test_decreto_1074_with_a_plain_number_is_not_taken_as_the_law():
    assert find_references("artículo 5 del Decreto 1074 de 2015") == []
