from api.curriculo_docs import ciclo_from_title, doc_id_from_uri, slugify


def test_slugify_strips_accents_and_punctuation():
    assert slugify("Compilación Programas 2do Ciclo") == "compilacion-programas-2do-ciclo"


def test_doc_id_from_gcs_uri_drops_prefix_and_extension():
    uri = "gs://informes-nee/curriculo/Compilación Programas 2do Ciclo.pdf"
    assert doc_id_from_uri(uri) == "compilacion-programas-2do-ciclo"


def test_doc_id_is_stable_for_the_first_cycle_document():
    uri = "gs://informes-nee/curriculo/Compilación Programas 1er Ciclo - 2024.pdf"
    assert doc_id_from_uri(uri) == "compilacion-programas-1er-ciclo-2024"


def test_doc_id_accepts_a_bare_filename():
    assert doc_id_from_uri("Compilación Programas 2do Ciclo.pdf") == "compilacion-programas-2do-ciclo"


def test_ciclo_is_extracted_from_the_document_title():
    assert ciclo_from_title("Compilación Programas 1er Ciclo - 2024") == "1er Ciclo"
    assert ciclo_from_title("Compilación Programas 2do Ciclo") == "2do Ciclo"


def test_ciclo_is_empty_when_the_title_does_not_name_one():
    assert ciclo_from_title("Marco Curricular Nacional") == ""
