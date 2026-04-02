"""
Endpoint para la carga de documentos propios del docente.

POST /documents/upload
  - Acepta PDF de hasta 50 MB
  - ciclo: parámetro opcional (default: "2do_ciclo")
  - Procesa con Folio on-device (dev: LM Studio) o Gemini (prod)
  - Persiste fragmentos como nodos :DocumentoDocente en Neo4j
  - Retorna IngestionResult con resumen de nodos creados
"""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

import folio
from folio import LMStudioUnavailableError
from folio.hierarchizer import IngestionResult
from ingestion.folio_adapter import PlanCurricularAdapter

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=IngestionResult)
async def upload_document(
    file: UploadFile = File(...),
    ciclo: str = Query(default="2do_ciclo", description="Ciclo curricular al que pertenece el documento"),
) -> IngestionResult:
    """
    Subir un PDF para incorporarlo como contexto RAG del docente.

    El documento se procesa con Folio (on-device en dev, Gemini en prod) y
    sus fragmentos quedan disponibles en las búsquedas del agente RAG,
    etiquetados con el ciclo curricular correspondiente.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=422,
            detail="Solo se aceptan archivos PDF (content-type: application/pdf)",
        )

    content = await file.read()

    if len(content) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF excede el límite de 50 MB ({len(content) // 1024 // 1024} MB recibidos)",
        )

    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        adapter = PlanCurricularAdapter(ciclo=ciclo)
        result = folio.run(tmp_path, storage=adapter)
        return result
    except LMStudioUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LM Studio unavailable: {exc}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando el documento: {exc}",
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
