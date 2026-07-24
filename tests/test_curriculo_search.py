# Mockea SearchServiceClient — no pega a Discovery Engine real.
# Convención: FastAPI TestClient + unittest.mock.patch (ver tests/test_integration.py).

from unittest.mock import patch

import google.cloud.discoveryengine_v1 as discoveryengine
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

INTERNAL_KEY = "test-internal-key"
URL = "/internal/curriculo/search"


def _fake_response(with_results: bool = True) -> discoveryengine.SearchResponse:
    if not with_results:
        return discoveryengine.SearchResponse(results=[], summary=discoveryengine.SearchResponse.Summary(summary_text=""))

    doc = discoveryengine.Document(
        derived_struct_data={
            "title": "Compilación Programas 1er Ciclo - 2024",
            "link": "gs://bucket/curriculo/1er-ciclo.pdf",
            "extractive_answers": [
                {"content": "El programa sugiere trabajo por proyectos integradores.", "pageNumber": "42"}
            ],
        }
    )
    result = discoveryengine.SearchResponse.SearchResult(document=doc)
    return discoveryengine.SearchResponse(
        results=[result],
        summary=discoveryengine.SearchResponse.Summary(
            summary_text="El programa sugiere trabajo por proyectos integradores [42]."
        ),
    )


def _headers(key: str | None = INTERNAL_KEY) -> dict:
    h = {}
    if key is not None:
        h["x-internal-key"] = key
    return h


@pytest.fixture(autouse=True)
def _configure_env():
    with (
        patch("api.auth.INTERNAL_API_KEY", INTERNAL_KEY),
        patch("api.routes.curriculo_search.DISCOVERY_ENGINE_DATA_STORE_ID", "curriculo-ebi-anep"),
    ):
        yield


def test_valid_query_returns_answer_with_sources():
    with patch("api.routes.curriculo_search._search_sync", return_value=_fake_response(True)) as mock_search:
        r = client.post(URL, json={"consulta": "¿Cómo se aborda el trabajo por proyectos?"}, headers=_headers())

    assert r.status_code == 200
    data = r.json()
    assert data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["pageNumber"] == 42
    assert data["sources"][0]["excerpt"]
    mock_search.assert_called_once()


def test_no_matching_documents_returns_empty_sources():
    with patch("api.routes.curriculo_search._search_sync", return_value=_fake_response(False)):
        r = client.post(URL, json={"consulta": "pregunta sin relación con el currículo"}, headers=_headers())

    assert r.status_code == 200
    data = r.json()
    assert data["sources"] == []
    assert data["answer"]  # mensaje claro de "no encontrado", no vacío ni error crudo


def test_missing_internal_key_rejected():
    with patch("api.routes.curriculo_search._search_sync") as mock_search:
        r = client.post(URL, json={"consulta": "cualquier cosa"}, headers=_headers(key=None))

    assert r.status_code == 401
    mock_search.assert_not_called()


def test_invalid_internal_key_rejected():
    with patch("api.routes.curriculo_search._search_sync") as mock_search:
        r = client.post(URL, json={"consulta": "cualquier cosa"}, headers=_headers(key="wrong-key"))

    assert r.status_code == 401
    mock_search.assert_not_called()


def test_discovery_engine_error_returns_structured_response_not_500():
    with patch("api.routes.curriculo_search._search_sync", side_effect=RuntimeError("quota exceeded")):
        r = client.post(URL, json={"consulta": "cualquier cosa"}, headers=_headers())

    assert r.status_code == 200
    data = r.json()
    assert data["sources"] == []
    assert data["answer"]


def test_sources_carry_doc_id_and_ciclo_for_the_pdf_viewer():
    with patch("api.routes.curriculo_search._search_sync", return_value=_fake_response(True)):
        r = client.post(URL, json={"consulta": "trabajo por proyectos"}, headers=_headers())

    source = r.json()["sources"][0]
    # docId se deriva del nombre del objeto en GCS, ciclo del título del documento.
    assert source["docId"] == "1er-ciclo"
    assert source["ciclo"] == "1er Ciclo"


def test_content_words_drop_stopwords_grade_and_scaffolding():
    from api.routes.curriculo_search import _content_words

    q = "¿Qué orientaciones da el programa para enseñar ecosistemas en quinto grado?"
    assert _content_words(q) == ["ecosistemas"]


def test_query_candidates_go_from_most_to_least_precise():
    from api.routes.curriculo_search import _query_candidates

    candidates = _query_candidates("relaciones tróficas ecosistemas autóctonos de Uruguay")
    # La original primero (máxima precisión), después recortes decrecientes.
    assert candidates[0] == "relaciones tróficas ecosistemas autóctonos de Uruguay"
    assert candidates[-1] == "relaciones"
    assert len(candidates[1].split()) > len(candidates[-1].split())


def test_query_candidates_do_not_repeat_the_original():
    from api.routes.curriculo_search import _query_candidates

    assert _query_candidates("ecosistemas") == ["ecosistemas"]


def test_search_retries_with_a_shorter_query_when_there_are_no_results():
    from api.routes import curriculo_search

    intentos: list[str] = []

    def fake_search_once(_client, consulta, _max_results):
        intentos.append(consulta)
        # Sólo la consulta acortada devuelve algo, como hace el motor real.
        return _fake_response(with_results=consulta == "ecosistemas")

    with (
        patch.object(curriculo_search, "_search_once", fake_search_once),
        patch.object(curriculo_search.discoveryengine, "SearchServiceClient"),
    ):
        response = curriculo_search._search_sync("ecosistemas en quinto grado", 3)

    assert intentos == ["ecosistemas en quinto grado", "ecosistemas"]
    assert len(list(response.results)) == 1
