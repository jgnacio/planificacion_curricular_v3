"""
Orquestador del pipeline STAR on-device.

Flujo:
  PDF → pdf_extractor → segmenter → hierarchizer → Neo4j
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ingestion.hierarchizer import (
    CurriculumNode,
    DocumentNode,
    IngestionResult,
    hierarchize,
)
from ingestion.lm_client import (
    LMStudioClient,
    LMStudioUnavailableError,
    get_backend,
)
from ingestion.pdf_extractor import extract_text_blocks
from ingestion.segmenter import segment

# Modelos por defecto para dev (LM Studio)
_EDGE_MODEL = "liquid/lfm2.5-1.2b"
_HIER_MODEL = "qwen/qwen3-4b-2507"


def run(
    pdf_path: str,
    mode: str = "document",
    lm_base_url: str = "http://localhost:1234/v1",
) -> IngestionResult:
    """
    Ejecuta el pipeline completo de extracción on-device.

    Args:
        pdf_path: Ruta al PDF a procesar.
        mode:     "curriculum" para PDFs del programa ANEP,
                  "document"   para documentos arbitrarios del docente.
        lm_base_url: URL base de LM Studio (solo en dev).

    Returns:
        IngestionResult con resumen de nodos creados y errores.

    Raises:
        LMStudioUnavailableError: Si LM Studio no está corriendo.
    """
    import os
    env = os.getenv("APP_ENV", "dev").lower()

    if env == "dev":
        edge_client = LMStudioClient(base_url=lm_base_url, model=_EDGE_MODEL)
        hier_client = LMStudioClient(base_url=lm_base_url, model=_HIER_MODEL)
        if not edge_client.health_check():
            raise LMStudioUnavailableError(
                "LM Studio no disponible en localhost:1234"
            )
    else:
        edge_client = get_backend(env)
        hier_client = get_backend(env)

    doc_id = str(uuid.uuid4())
    errores: list[str] = []
    nodos_creados = 0

    # 1. Extraer bloques de texto del PDF
    blocks = extract_text_blocks(pdf_path)

    # 2. Segmentar en fragmentos semánticamente completos
    fragments = segment(blocks, edge_client)

    # 3. Jerarquizar y persistir en Neo4j
    from ingestion.database import Neo4jManager
    db = Neo4jManager()
    fecha_upload = datetime.now(timezone.utc).isoformat()

    for fragment in fragments:
        try:
            node = hierarchize(fragment, hier_client, mode)  # type: ignore[arg-type]
            db.save_document_node(node, doc_id, fecha_upload)
            nodos_creados += 1
        except Exception as e:
            errores.append(f"{fragment[:60]}... → {e}")

    db.ensure_fulltext_index()
    db.close()

    return IngestionResult(
        doc_id=doc_id,
        nodos_creados=nodos_creados,
        fragmentos_procesados=len(fragments),
        errores=errores,
    )
