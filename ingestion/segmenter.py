"""
Segmentador semántico basado en sliding window + edge fusion.

Approach STAR:
1. Divide el texto en ventanas de WINDOW_SIZE caracteres.
2. Pregunta al modelo si el fragmento termina en un límite semántico completo.
3. Si está cortado, fusiona con el inicio de la siguiente ventana y re-evalúa.
"""
from __future__ import annotations

from pydantic import BaseModel

from ingestion.lm_client import LLMBackend

WINDOW_SIZE = 400
MIN_FRAGMENT_LEN = 30

# ── Prompt ────────────────────────────────────────────────────────────────────

_EDGE_PROMPT = """\
You are a text boundary detector for Spanish educational documents.

Given a text fragment, determine if it ends at a complete semantic unit \
(full sentence, complete concept, or end of a list item).

Fragment:
---
{fragment}
---

Reply ONLY with valid JSON. Examples:
{{"complete": true}}   ← fragment ends at a natural boundary
{{"complete": false}}  ← fragment is cut mid-sentence or mid-concept"""


class _EdgeResult(BaseModel):
    complete: bool


# ── Public API ─────────────────────────────────────────────────────────────────

def segment(blocks: list[str], client: LLMBackend) -> list[str]:
    """
    Segmenta una lista de bloques de texto en fragmentos semánticamente completos.

    Args:
        blocks: Bloques de texto, uno por página (output de pdf_extractor).
        client: Backend LLM para detección de bordes (lfm2.5-1.2b en dev).

    Returns:
        Lista de fragmentos semánticamente completos.
    """
    fragments: list[str] = []
    for block in blocks:
        fragments.extend(_slide_block(block, client))
    return fragments


# ── Internals ──────────────────────────────────────────────────────────────────

def _slide_block(text: str, client: LLMBackend) -> list[str]:
    """Aplica sliding window con edge fusion sobre un bloque de texto."""
    if len(text) <= WINDOW_SIZE:
        return [text.strip()] if len(text.strip()) >= MIN_FRAGMENT_LEN else []

    fragments: list[str] = []
    pos = 0

    while pos < len(text):
        end = min(pos + WINDOW_SIZE, len(text))
        fragment = text[pos:end]

        # Último fragmento — siempre completo
        if end == len(text):
            if len(fragment.strip()) >= MIN_FRAGMENT_LEN:
                fragments.append(fragment.strip())
            break

        if _is_complete(fragment, client):
            fragments.append(fragment.strip())
            pos = end
        else:
            # Buscar corte natural dentro de la ventana
            cut = _natural_break(fragment)
            if cut > 0:
                head = fragment[:cut].strip()
                if len(head) >= MIN_FRAGMENT_LEN:
                    fragments.append(head)
                pos = pos + cut
            else:
                # Sin corte natural — avanzar igual para no quedar en loop
                if len(fragment.strip()) >= MIN_FRAGMENT_LEN:
                    fragments.append(fragment.strip())
                pos = end

    return [
        f for f in fragments
        if len(f) >= MIN_FRAGMENT_LEN and len(f.split()) >= 4
    ]


def _is_complete(fragment: str, client: LLMBackend) -> bool:
    """Pregunta al modelo si el fragmento es semánticamente completo."""
    try:
        prompt = _EDGE_PROMPT.format(fragment=fragment)
        result = client.complete(prompt, _EdgeResult)
        return result.complete
    except Exception:
        # Fallback heurístico: termina con signo de puntuación fuerte
        return fragment.rstrip().endswith((".", "!", "?", ":", "\n"))


def _natural_break(text: str) -> int:
    """
    Busca el último punto de corte natural en la segunda mitad del texto.
    Retorna el índice del carácter DESPUÉS del terminador, o 0 si no encuentra.
    """
    half = len(text) // 2
    for terminator in (". ", ".\n", "! ", "!\n", "? ", "?\n", ":\n"):
        idx = text.rfind(terminator, half)
        if idx != -1:
            return idx + len(terminator)
    return 0
