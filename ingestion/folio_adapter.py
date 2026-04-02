"""
Adapter de Folio para planificacion_curricular_v3.

Conecta el pipeline Folio con el Neo4jManager existente.
Cada fragmento extraído queda como nodo :DocumentoDocente con
los campos estándar del sistema (fuente, ciclo, fecha_upload).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ingestion.database import Neo4jManager

if TYPE_CHECKING:
    from folio.hierarchizer import IngestionResult


class PlanCurricularAdapter:
    """
    StorageAdapter que persiste fragmentos de Folio en Neo4j
    usando el Neo4jManager del proyecto.

    Agrega ciclo y fuente a cada nodo para que el RAG pueda
    filtrar por contexto curricular.
    """

    def __init__(self, ciclo: str = "2do_ciclo"):
        self._db = Neo4jManager()
        self._ciclo = ciclo

    def save(self, fragment: dict, doc_id: str, metadata: dict) -> None:
        texto = (fragment.get("texto") or "").strip()
        if not texto:
            return

        # Construir un objeto compatible con _save_document_node_tx
        # usando un namespace simple (evita importar DocumentNode de Folio)
        node = _FragmentNode(
            texto=texto,
            titulo_seccion=fragment.get("titulo_seccion"),
            tipo=fragment.get("tipo", "fragmento"),
            ciclo=self._ciclo,
        )

        fecha_upload = metadata.get("fecha_upload", "")
        with self._db.driver.session() as session:
            session.execute_write(
                _save_tx,
                node=node,
                doc_id=doc_id,
                fecha_upload=fecha_upload,
            )

    def on_complete(self, doc_id: str, result: "IngestionResult") -> None:
        self._db.ensure_fulltext_index()
        self._db.close()


class _FragmentNode:
    """Estructura interna para pasar datos al tx de Neo4j."""

    def __init__(
        self,
        texto: str,
        titulo_seccion: str | None,
        tipo: str,
        ciclo: str,
    ):
        self.texto = texto
        self.titulo_seccion = titulo_seccion
        self.tipo = tipo
        self.ciclo = ciclo


def _save_tx(tx, node: _FragmentNode, doc_id: str, fecha_upload: str) -> None:
    props = {
        "doc_id": doc_id,
        "titulo_seccion": node.titulo_seccion,
        "texto": node.texto,
        "fecha_upload": fecha_upload,
        "fuente": "docente",
        "ciclo": node.ciclo,
        "tipo": node.tipo,
    }
    tx.run(
        """
        MERGE (d:DocumentoDocente {doc_id: $doc_id, texto: $texto})
        SET d += $props
        """,
        doc_id=doc_id,
        texto=node.texto,
        props=props,
    )
