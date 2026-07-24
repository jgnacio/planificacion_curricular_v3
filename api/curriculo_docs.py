"""Identidad estable de los PDFs del currículo oficial EBI/ANEP.

Los PDFs viven en GCS bajo el prefijo `curriculo/` con nombres humanos y acentuados
("Compilación Programas 2do Ciclo.pdf"). Esos nombres no sirven como identificador en
una URL, así que acá se derivan `doc_id` slugificados y estables, y se resuelve el
camino inverso (doc_id → blob name) listando el bucket.
"""

import os
import re
import unicodedata
from functools import lru_cache

from google.cloud import storage

GCS_CURRICULO_PREFIX = "curriculo/"

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG_STRIP_RE.sub("-", ascii_only).strip("-")


def doc_id_from_uri(uri: str) -> str:
    """Deriva el doc_id desde un `gs://bucket/curriculo/Nombre.pdf` o un nombre suelto."""
    basename = uri.rsplit("/", 1)[-1]
    if basename.lower().endswith(".pdf"):
        basename = basename[: -len(".pdf")]
    return slugify(basename)


def ciclo_from_title(title: str) -> str:
    """Extrae el ciclo del nombre del documento para mostrarlo en el badge de la cita."""
    lowered = title.lower()
    if "1er ciclo" in lowered or "primer ciclo" in lowered:
        return "1er Ciclo"
    if "2do ciclo" in lowered or "segundo ciclo" in lowered:
        return "2do Ciclo"
    return ""


@lru_cache(maxsize=1)
def _blob_names_by_doc_id() -> dict[str, str]:
    """Mapa doc_id → blob name. Cacheado: el set de PDFs oficiales es fijo por deploy."""
    bucket_name = os.environ["GCS_BUCKET_NAME"]
    client = storage.Client()
    blobs = client.list_blobs(bucket_name, prefix=GCS_CURRICULO_PREFIX)
    return {
        doc_id_from_uri(blob.name): blob.name
        for blob in blobs
        if blob.name.lower().endswith(".pdf")
    }


def resolve_blob_name(doc_id: str) -> str | None:
    """Devuelve el blob name del PDF, o None si el doc_id no corresponde a ninguno."""
    mapping = _blob_names_by_doc_id()
    if doc_id in mapping:
        return mapping[doc_id]
    # Un PDF agregado después del último listado no estaría en el cache: reintentamos.
    _blob_names_by_doc_id.cache_clear()
    return _blob_names_by_doc_id().get(doc_id)
