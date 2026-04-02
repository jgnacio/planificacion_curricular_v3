"""
Jerarquizador semántico: convierte fragmentos de texto en nodos estructurados.

Usa qwen3-4b (dev) o Gemini (prod) para generar JSON jerárquico.
Dos modos:
  - curriculum: hint del schema ANEP (Ciclo→Espacio→Unidad→Eje)
  - document:   jerarquía libre, inferida del contexto
"""
from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel

from ingestion.lm_client import LLMBackend

MAX_RETRIES = 2

# ── Schemas Pydantic ───────────────────────────────────────────────────────────

class CurriculumNode(BaseModel):
    ciclo: str | None = None
    espacio: str | None = None
    unidad: str | None = None
    eje: str | None = None
    tipo: Literal["contenido", "competencia", "criterio", "otro"] = "otro"
    texto: str


class DocumentNode(BaseModel):
    titulo_seccion: str | None = None
    tipo: Literal["fragmento", "error"] = "fragmento"
    texto: str


FragmentNode = Union[CurriculumNode, DocumentNode]


class IngestionResult(BaseModel):
    doc_id: str
    nodos_creados: int
    fragmentos_procesados: int
    errores: list[str]


# ── Prompts ───────────────────────────────────────────────────────────────────

_CURRICULUM_PROMPT = """\
Sos un extractor de datos del programa curricular EBI/ANEP Uruguay.
Tu única tarea es identificar la información jerárquica en el fragmento y devolverla como JSON.

Schema de referencia ANEP:
- ciclo: "1er Ciclo" | "2do Ciclo" | null
- espacio: nombre del espacio curricular (ej: "Espacio Científico Matemático") | null
- unidad: nombre de la unidad curricular (ej: "Matemática", "Historia") | null
- eje: nombre del eje temático en MAYÚSCULAS (ej: "NUMERACIÓN NATURAL") | null
- tipo: "contenido" | "competencia" | "criterio" | "otro"
- texto: el texto literal completo del fragmento (obligatorio)

REGLA: Solo incluí información que esté literalmente en el fragmento. Si un campo no está presente → null.

Fragmento:
---
{fragment}
---

Respondé SOLO con JSON válido, sin texto adicional."""

_DOCUMENT_PROMPT = """\
Sos un extractor de contenido. Dado este fragmento de texto, identificá:
- titulo_seccion: el título o encabezado de sección al que pertenece (inferido del contexto) | null
- tipo: siempre "fragmento"
- texto: el texto literal completo del fragmento (obligatorio)

Fragmento:
---
{fragment}
---

Respondé SOLO con JSON válido, sin texto adicional."""


# ── Public API ─────────────────────────────────────────────────────────────────

def hierarchize(
    fragment: str,
    client: LLMBackend,
    mode: Literal["curriculum", "document"],
) -> FragmentNode:
    """
    Convierte un fragmento de texto en un nodo estructurado.

    Reintenta hasta MAX_RETRIES veces si el LLM devuelve JSON inválido.
    En caso de fallo persistente, retorna un nodo de error con el texto crudo.
    """
    if mode == "curriculum":
        prompt = _CURRICULUM_PROMPT.format(fragment=fragment)
        model_class: type[BaseModel] = CurriculumNode
    else:
        prompt = _DOCUMENT_PROMPT.format(fragment=fragment)
        model_class = DocumentNode

    last_error: Exception | None = None
    for _ in range(MAX_RETRIES + 1):
        try:
            return client.complete(prompt, model_class)  # type: ignore[return-value]
        except Exception as e:
            last_error = e

    # Fallback: nodo de error con texto crudo para revisión manual
    if mode == "curriculum":
        return CurriculumNode(tipo="otro", texto=fragment)
    return DocumentNode(tipo="error", texto=fragment)
