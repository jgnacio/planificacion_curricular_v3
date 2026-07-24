"""Acceso de lectura a los PDFs del currículo oficial EBI/ANEP.

El visor del frontend abre una cita en su página exacta, así que necesita la URL del
PDF. El bucket es privado: en vez de exponerlo, se devuelve una signed URL de lectura
de corta vida, sólo para usuarios autenticados.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from api.auth import get_current_user_id
from api.curriculo_docs import resolve_blob_name
from api.gcs import get_signed_read_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/curriculo/pdfs", tags=["curriculo"])


@router.get("/{doc_id}/signed-url")
def obtener_url_pdf(doc_id: str, _uid: str = Depends(get_current_user_id)) -> dict:
    blob_name = resolve_blob_name(doc_id)
    if not blob_name:
        raise HTTPException(status_code=404, detail="Documento de currículo no encontrado")

    try:
        url = get_signed_read_url(blob_name)
    except Exception:
        logger.error("No se pudo firmar la URL de %s", blob_name, exc_info=True)
        raise HTTPException(status_code=502, detail="No se pudo acceder al documento")

    return {"url": url}
