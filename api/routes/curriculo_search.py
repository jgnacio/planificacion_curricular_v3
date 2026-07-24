"""Búsqueda del currículo oficial EBI/ANEP sobre un data store de Vertex AI Search
(Discovery Engine). Reemplaza la integración anterior con Open Notebook.

Ruta interna (X-Internal-Key), consumida por el ADK tool `consultar_curriculo_oficial`
en teacher_agent/agent.py.
"""

import logging
import os
import re
import unicodedata
from asyncio import to_thread

from fastapi import APIRouter, Depends
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import discoveryengine_v1 as discoveryengine
from pydantic import BaseModel

from api.auth import require_internal_key
from api.curriculo_docs import ciclo_from_title, doc_id_from_uri

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/curriculo", tags=["curriculo"])

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "facilitador-docente")
# El engine vive en location "global" (no regional) — serving_config abajo lo asume.
DISCOVERY_ENGINE_LOCATION = "global"
DISCOVERY_ENGINE_DATA_STORE_ID = os.getenv("DISCOVERY_ENGINE_DATA_STORE_ID", "")
# Las extractive answers + summary requieren tier enterprise, que vive en el ENGINE
# (no en el serving config del data store). Default derivado del data store id.
DISCOVERY_ENGINE_ENGINE_ID = (
    os.getenv("DISCOVERY_ENGINE_ENGINE_ID", "")
    or (f"{DISCOVERY_ENGINE_DATA_STORE_ID}-engine" if DISCOVERY_ENGINE_DATA_STORE_ID else "")
)


class CurriculoSearchRequest(BaseModel):
    consulta: str
    max_results: int = 3


class Fuente(BaseModel):
    title: str
    pageNumber: int | None = None
    excerpt: str
    uri: str
    # docId + ciclo permiten al frontend armar el badge y abrir el PDF en la página
    # exacta sin exponer nombres de objetos de GCS.
    docId: str = ""
    ciclo: str = ""


class CurriculoSearchResponse(BaseModel):
    answer: str
    sources: list[Fuente]


def _serving_config() -> str:
    return (
        f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{DISCOVERY_ENGINE_LOCATION}"
        f"/collections/default_collection/engines/{DISCOVERY_ENGINE_ENGINE_ID}"
        f"/servingConfigs/default_search"
    )


# El motor es conjuntivo: cada término extra restringe el resultado, y basta una
# palabra ausente de los PDFs ("quinto grado") para que una consulta que funcionaba
# devuelva cero. Estas se descartan al acortar la consulta en los reintentos.
_STOPWORDS = {
    "que", "cual", "como", "para", "por", "del", "los", "las", "una", "uno", "con",
    "sobre", "dice", "de", "el", "la", "en", "y", "o", "a", "un", "se", "su", "sus", "al",
    # Vocabulario de andamiaje de la pregunta, no del contenido curricular
    "programa", "curriculo", "oficial", "orientaciones", "ensenar", "trabajar",
    "aborda", "sugiere", "metodologias", "actividades",
    # Referencias a grado y ciclo: casi nunca aparecen literales en los PDFs
    "grado", "grados", "ciclo", "nivel", "primero", "segundo", "tercero", "cuarto",
    "quinto", "sexto", "1er", "2do", "3er", "4to", "5to", "6to",
}

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _strip_accents(word: str) -> str:
    return unicodedata.normalize("NFKD", word.lower()).encode("ascii", "ignore").decode()


def _content_words(consulta: str) -> list[str]:
    """Palabras de contenido de la consulta, en orden, sin stopwords ni ruido."""
    words = []
    for word in _PUNCT_RE.sub(" ", consulta).split():
        base = _strip_accents(word)
        if len(base) < 3 or base.isdigit() or base in _STOPWORDS:
            continue
        words.append(word)
    return words


def _query_candidates(consulta: str) -> list[str]:
    """Consulta original y versiones progresivamente más cortas, de mayor a menor precisión.

    Se prueban en orden y se devuelve la primera con resultados: acortar gana
    cobertura pero pierde precisión, así que la más larga que funcione es la mejor.
    """
    candidates = [consulta.strip()]
    words = _content_words(consulta)
    for size in range(min(len(words), 4), 0, -1):
        candidate = " ".join(words[:size])
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _search_once(client, consulta: str, max_results: int) -> discoveryengine.SearchResponse:
    # Sólo pedimos extractive answers (feature de tier Enterprise): de ahí salen los
    # excerpts + pageNumber que alimentan las citas y el visor de PDF. NO pedimos
    # summary_spec (la respuesta generativa del add-on LLM): el teacher_agent es un
    # agente Gemini que sintetiza la planificación por su cuenta desde `fuentes` y
    # nunca consume el campo `answer`, así que pagar el summary era redundante. Quitarlo
    # baja el costo por query de ~$6 a ~$4 por 1.000 (add-on LLM → sólo Enterprise).
    request = discoveryengine.SearchRequest(
        serving_config=_serving_config(),
        query=consulta,
        page_size=max_results,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=2,
                max_extractive_segment_count=1,
            ),
        ),
    )
    return client.search(request)


def _search_sync(consulta: str, max_results: int) -> discoveryengine.SearchResponse:
    """Busca acortando la consulta hasta obtener resultados.

    Devuelve la respuesta del primer candidato con resultados; si ninguno da nada,
    devuelve la del último intento para que `_normalize` produzca el mensaje vacío.
    """
    client = discoveryengine.SearchServiceClient()
    response = None
    for candidate in _query_candidates(consulta):
        response = _search_once(client, candidate, max_results)
        # Una fuente sin página no se puede abrir en el visor, así que no cuenta como
        # resultado útil: seguimos acortando a ver si aparece una citable.
        if any(f.pageNumber is not None for f in _fuentes_from_response(response)):
            if candidate != consulta.strip():
                logger.info("Consulta %r sin citas; se usó %r", consulta, candidate)
            return response
    return response


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _clean_excerpt(text: str) -> str:
    # Discovery Engine resalta términos con <b>…</b> en los snippets; los sacamos.
    return _HTML_TAG_RE.sub("", text).strip()


def _extract_page_number(entry) -> int | None:
    page = entry.get("pageNumber") or entry.get("page_number")
    if page is None:
        return None
    try:
        return int(page)
    except (TypeError, ValueError):
        return None


def _fuentes_from_result(result) -> list[Fuente]:
    struct_data = dict(result.document.derived_struct_data)
    title = struct_data.get("title", "")
    uri = struct_data.get("link", "")

    doc_id = doc_id_from_uri(uri or title)
    ciclo = ciclo_from_title(title)

    entries = struct_data.get("extractive_answers") or struct_data.get("extractive_segments") or []
    fuentes = []
    for entry in entries:
        entry = dict(entry)
        content = _clean_excerpt(entry.get("content", ""))
        fuentes.append(
            Fuente(
                title=title,
                pageNumber=_extract_page_number(entry),
                excerpt=content,
                uri=uri,
                docId=doc_id,
                ciclo=ciclo,
            )
        )
    return fuentes


def _fuentes_from_response(response: discoveryengine.SearchResponse) -> list[Fuente]:
    sources: list[Fuente] = []
    for result in response.results:
        sources.extend(_fuentes_from_result(result))
    return sources


def _normalize(response: discoveryengine.SearchResponse) -> CurriculoSearchResponse:
    sources = _fuentes_from_response(response)

    answer = ""
    if response.summary and response.summary.summary_text:
        answer = response.summary.summary_text
    elif not sources:
        answer = "No se encontraron resultados en el currículo oficial para esa consulta."

    return CurriculoSearchResponse(answer=answer, sources=sources)


@router.post("/search", response_model=CurriculoSearchResponse)
async def buscar_curriculo(
    body: CurriculoSearchRequest,
    _: None = Depends(require_internal_key),
) -> CurriculoSearchResponse:
    if not DISCOVERY_ENGINE_ENGINE_ID:
        logger.error("DISCOVERY_ENGINE_ENGINE_ID / DISCOVERY_ENGINE_DATA_STORE_ID no configurada")
        return CurriculoSearchResponse(
            answer="Búsqueda de currículo no disponible: falta configuración del data store.",
            sources=[],
        )

    try:
        # SearchServiceClient es síncrono — to_thread evita bloquear el event loop de FastAPI.
        response = await to_thread(_search_sync, body.consulta, body.max_results)
    except GoogleAPICallError as e:
        logger.error("Error de Discovery Engine al buscar currículo: %s", e, exc_info=True)
        return CurriculoSearchResponse(
            answer="No se pudo consultar el currículo oficial en este momento. Intentá de nuevo más tarde.",
            sources=[],
        )
    except Exception as e:
        logger.error("Error inesperado al buscar currículo: %s", e, exc_info=True)
        return CurriculoSearchResponse(
            answer="No se pudo consultar el currículo oficial en este momento.",
            sources=[],
        )

    return _normalize(response)
