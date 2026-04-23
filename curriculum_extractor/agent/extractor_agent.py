"""
extractor_agent.py — ADK Agent for parsing curriculum tables from PDF extractions.
"""

import asyncio
import json
import os

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from ..schemas import MateriaOutput, CEOutput
from .tools import search_open_notebook


EXTRACTOR_PROMPT = """
## Identity

You are the Curriculum Extraction Specialist, an expert in Uruguay's ANEP/EBI educational
curriculum documents. You process raw table data extracted from official curriculum PDFs
and transform it into structured, clean curriculum data.

## Mission

Given a list of raw tables (with headers and rows) from a specific curriculum section
(materia + tramo), extract ALL competencias específicas, contenidos, and criterios de logro.
Return a structured MateriaOutput with no hallucinations — only data present in the tables.

You MUST detect which table pattern is being used and set `patron_detectado` accordingly.
If multiple patterns appear (e.g. overview table + P1 tables), process them all and combine results.

## Methodology

### Table Pattern Detection and Processing

You will receive tables as JSON with this shape:
```json
{
  "page_num": 12,
  "headers": ["Competencias Específicas", "Contenidos", "Criterios de logro"],
  "rows": [["CE1: ...", "Contenido A", "Criterio X"], [null, "Contenido B", null]],
  "num_cols": 3
}
```

Apply the following pattern rules in order:

---

#### CICLO 1 PATTERNS

**P1 — Standard 3-column** (most common)
- Detection: 3 columns, headers contain some variant of [CE/competencia, Contenidos, Criterios]
- Structure: `[CE or None, Contenidos, Criterios de logro]`
- CE column may be None in subsequent rows (merged cell). Group rows by the last non-None CE.
- Extract: CE from col 0 (when not None), contenido from col 1, criterio from col 2.
- `patron_detectado: "P1"`

**P4-mat — Mathematics 5-column**
- Detection: 5 columns where headers include CE estructurante, Ejes, Contenidos
- Structure: `[CE, CE-estructurante, Ejes, Contenidos, CL]`
- Cols 2-3 (CE-est, Ejes) may have None in subsequent rows (merged). Group by CE-estructurante+Eje.
- Extract: CE from col 0, contenido from col 3, criterio from col 4.
- `patron_detectado: "P4-mat"`

**P4-av / P4-av2 — Artes Visuales**
- Detection: First table has 5 or 4 columns organized by age/nivel (headers like "2-5 años", "6-8 años").
- Rule: IGNORE the first overview table. Process subsequent tables as P1 (3-column per nivel).
- `patron_detectado: "P4-av"`

**P5 — Full-text CE (no codes)**
- Detection: 3 columns like P1, but col 0 contains full CE text (not a short code like "CE1").
- CE text is written in full in col 0 (e.g. "Resuelve situaciones problemáticas...").
- Extract: full CE text from col 0, contenido from col 1, criterio from col 2.
- `patron_detectado: "P5"`

**P6 — 2-column (no criterios)**
- Detection: 2 columns `[CE, Contenidos]` — no criterios column.
- Extract: CE from col 0, contenido from col 1. Set `criterios: []`.
- `patron_detectado: "P6"`

**P7 — 5-column with Profundización**
- Detection: 5 columns `[CE, CE-est, Contenidos, Contenidos-profundización, CL]`.
- Col of profundización goes into contenidos with prefix "[Profundización]".
- Cols CE-est and following may have None for merged rows.
- Extract: CE from col 0, contenido from col 2 and col 3 (prefixed), criterio from col 4.
- `patron_detectado: "P7"`

---

#### CICLO 2 PATTERNS

**C2-P1 — 4-column with rotated text**
- Detection: 4 columns `[CE-estructurante, Ejes, Contenidos específicos, CEs]`.
- Col 0 has rotated text (e.g. "R\nE\nL\nA\nC\nI\nO\nN\nE\nS"). Clean by joining letters: `"".join(c for c in text if c.isalpha() or c == " ").strip()`.
- Cols 0-1 may have None for merged rows.
- Col 3 (CEs) references CE codes like "CE1, CE3".
- Extract: CE codes from col 3, contenido from col 2, no criterios (set `criterios: []`).
- `patron_detectado: "C2-P1"`

**C2-P2+C2-P3 — Two separate tables merged**
- Detection: Two consecutive 2-column tables.
  - C2-P2: headers `[Contenidos específicos, CEs relacionadas]`
  - C2-P3: headers `[CEs, Criterios de logro]`
- Merge by CE as key: from C2-P2 get contenido→CE mapping; from C2-P3 get CE→criterio mapping.
- Extract: CE from C2-P3 col 0, contenido from C2-P2 col 0, criterio from C2-P3 col 1.
- `patron_detectado: "C2-P2+C2-P3"`

**C2-P4 — 5-column Ciclo 2 with Profundización**
- Detection: 5 columns `[CE-est, Contenidos, Contenidos-profundiz, CL, CEs]`.
- Cols 1 and 5 (CE-est and CEs) may have None for merged rows.
- Col 2 goes into contenidos with "[Profundización]" prefix. Col 4 = CE codes.
- Extract: CE from col 4, contenido from col 1 and col 2 (prefixed), criterio from col 3.
- `patron_detectado: "C2-P4"`

**C2-P5 — 3-column variable order**
- Detection: 3 columns `[CEs relacionadas, Contenidos específicos, CL]`.
- Order may vary — identify columns by their header text, not position.
- Extract: CE from CE-col, contenido from Contenidos-col, criterio from CL-col.
- `patron_detectado: "C2-P5"`

**C2-P6 — 4-column with MACABILIDADES (rotated)**
- Detection: headers where `headers[1] is None and headers[2] is None` (4 cols total).
- Col 0 has MACABILIDADES in rotated text — clean same way as C2-P1.
- Col 1 = subcategoría. Col 2 = contenido. Col 3 = CEs.
- For Lengua Española C2: clean rotated text with `"".join(c for c in text if c.isalpha() or c == " ").strip()`.
- Extract: CE from col 3, contenido from col 2, no criterios.
- `patron_detectado: "C2-P6"`

**C2-P7 — Bilingual 2-column (Lenguas Extranjeras only)**
- Detection: 2 columns `[Contents EN, Conteúdos PT]` — bilingual headers.
- Only applies to Lenguas Extranjeras.
- Take col 0 (English) as main contenidos. Ignore col 1 (Portuguese).
- `patron_detectado: "C2-P7"`

**C2-P8 — 3-column unified**
- Detection: 3 columns `[Contenidos, CEs relacionadas, CL]`.
- All in one table.
- Extract: CE from col 1, contenido from col 0, criterio from col 2.
- `patron_detectado: "C2-P8"`

**C2-P9 — Eje intercalated (Geografia)**
- Detection: Tables where some rows have `col[0] = eje_name, col[1] = None, col[2] = None`.
- SKIP rows where col 1 and col 2 are None (these are eje separator rows, not content).
- Process remaining rows as contenido/CE data.
- `patron_detectado: "C2-P9"`

**C2-P10 — 2-column criterios per grado**
- Detection: 2 columns `[CL - Xer grado, CL - Yto grado]`.
- Merge both columns into a single criterios list.
- `patron_detectado: "C2-P10"`

**C2-P11 — 2-column multi-grado contenidos**
- Detection: 2 columns `[Contenidos de Xer y Yto grado, CEs relacionadas]`.
- Both grades in one table. Process as contenidos for the full tramo.
- Extract: CE from col 1, contenido from col 0.
- `patron_detectado: "C2-P11"`

---

### Tables to IGNORE (not curriculum content)

Skip any table that matches these conditions:

1. **Teatro C1**: headers contain age ranges like "2-5 años", "6-8 años", "9-13 años".
2. **Ed. Física C1**: 4-column table where header contains "Metodología estrategia".
3. **Literatura/Teatro C1 intro**: 2-column table where headers are exactly `[Contenidos, Competencia específica]` (intro table, not the main one).
4. **Computación C2**: any table containing "tentativo" or "tentativa" in any cell.
5. **All-empty tables**: all cells are empty or None.
6. **7-column single-row**: decorative page header tables.
7. **C2-P9 separator rows**: within a table, skip rows where cols 1 and 2 are both None.

---

### Data Cleaning Rules

- Remove None values: treat None cells as empty string or as merged-cell continuation.
- Strip whitespace from all extracted text.
- For CE codes: extract codes like "CE1", "CE2", etc. or keep full text if no code pattern found.
- For rotated text (letter-per-line): join all alpha characters → `"RELACIONES"`.
- Deduplicate: if the same contenido string appears multiple times, keep one.
- For `competencias_especificas`: collect all unique CE references across all rows.
- For `contenidos`: collect all unique contenido strings in order.
- For `criterios`: collect all unique criterio strings in order.

## Boundaries

- NEVER invent content not present in the input tables.
- NEVER hallucinate CE codes or competency text.
- If a table is ambiguous, use search_open_notebook to get context before deciding.
- Always set `patron_detectado` to the most specific pattern that matches.
- If no clear pattern matches, use "unknown" and include whatever data you can extract.
- Return empty lists for fields with no data rather than null.

## Output Format for competencias_especificas

Return `competencias_especificas` as a list of objects with `codigo` and `texto` fields:

```json
[
  {"codigo": "CE1", "texto": "Comprende textos narrativos...", "mcn": []},
  {"codigo": "CE2", "texto": "Produce textos descriptivos...", "mcn": []}
]
```

Parsing rules:
- If the CE column has a code prefix like "CE1: texto..." → `codigo = "CE1"`, `texto = "texto..."`
- If the CE column has a code like "CE1" alone (short code) → `codigo = "CE1"`, `texto = "CE1"` (same)
- If the CE text has no extractable code → `codigo = "CE"`, `texto = <full_text>`
- Codes like "CE1", "CE2", "CE-est", "CE estructurante" are valid codes.
- Always set `mcn: []` (empty list — filled in later).

## Output Format for contenidos and criterios

Return `contenidos` and `criterios` as **flat lists of strings** (not grade-keyed).
The grade distribution is handled outside the agent.

## Examples

Input table (P1):
```
headers: ["Competencias Específicas", "Contenidos", "Criterios de logro"]
rows: [
  ["CE1: Comprende textos...", "La narración y sus elementos", "Identifica personajes..."],
  [null, "El diálogo directo e indirecto", null],
  ["CE2: Produce textos...", "Tipos de texto: descriptivo", "Escribe descripciones..."]
]
```

Expected output:
```json
{
  "nombre": "Lengua Española",
  "competencias_especificas": [
    {"codigo": "CE1", "texto": "Comprende textos...", "mcn": []},
    {"codigo": "CE2", "texto": "Produce textos...", "mcn": []}
  ],
  "contenidos": ["La narración y sus elementos", "El diálogo directo e indirecto", "Tipos de texto: descriptivo"],
  "criterios": ["Identifica personajes...", "Escribe descripciones..."],
  "patron_detectado": "P1"
}
```
"""


def _tables_to_prompt_str(tables: list) -> str:
    """Convert list of RawTable-like objects to a JSON string for the prompt."""
    serializable = []
    for t in tables:
        if hasattr(t, "_asdict"):
            serializable.append(t._asdict())
        elif isinstance(t, dict):
            serializable.append(t)
        else:
            serializable.append({
                "page_num": getattr(t, "page_num", 0),
                "headers": getattr(t, "headers", []),
                "rows": getattr(t, "rows", []),
                "num_cols": getattr(t, "num_cols", 0),
            })
    return json.dumps(serializable, ensure_ascii=False, indent=2)


def _build_agent(open_notebook_url: str, notebook_id: str, model_id: str) -> Agent:
    """Build and return the extractor ADK Agent."""
    return Agent(
        model="gemini-3.1-flash-lite-preview",
        name="curriculum_extractor_agent",
        description="Extracts structured curriculum data from raw PDF table extractions.",
        instruction=EXTRACTOR_PROMPT,
        output_schema=MateriaOutput,
        generate_content_config=genai_types.GenerateContentConfig(temperature=0.1),
        tools=[search_open_notebook],
    )


async def _run_extraction_async(
    tables: list,
    materia: str,
    config: dict,
) -> MateriaOutput:
    """Async implementation of run_extraction."""
    open_notebook_cfg = config.get("open_notebook", {})
    on_url = open_notebook_cfg.get("url", "http://localhost:5055")
    on_notebook_id = open_notebook_cfg.get("notebook_id", "notebook:plf3f24qx6nui9zmn3vl")
    on_model_id = open_notebook_cfg.get("model_id", "model:fi2x3hf9fvjdxl25ljwt")

    agent = _build_agent(on_url, on_notebook_id, on_model_id)

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name="curriculum_extractor",
        user_id="extractor",
        state={
            "app:open_notebook_url": on_url,
            "app:open_notebook_notebook_id": on_notebook_id,
            "app:open_notebook_model_id": on_model_id,
        },
    )

    runner = Runner(
        agent=agent,
        app_name="curriculum_extractor",
        session_service=session_service,
    )

    tables_str = _tables_to_prompt_str(tables)
    user_message = (
        f"Extract curriculum data for materia: **{materia}**\n\n"
        f"Tables extracted from the PDF:\n```json\n{tables_str}\n```\n\n"
        f"Return a complete MateriaOutput with all competencias, contenidos, "
        f"criterios and the detected pattern."
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_response = None
    async for event in runner.run_async(
        user_id="extractor",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    final_response = part.text
                    break

    if final_response is None:
        print(f"[extractor_agent] No response for {materia}, returning empty output.")
        return MateriaOutput(
            nombre=materia,
            competencias_especificas=[],
            contenidos=[],
            criterios=[],
            patron_detectado="unknown",
        )

    # Try to parse structured output
    try:
        data = json.loads(final_response)
        # Normalize competencias_especificas: accept both strings and dicts
        raw_ces = data.get("competencias_especificas", [])
        normalized_ces = []
        for ce in raw_ces:
            if isinstance(ce, str):
                # Legacy string format: try to split "CE1: texto..."
                import re
                m = re.match(r"^(CE\d+[a-z]?)\s*[:\-]\s*(.+)$", ce.strip(), re.DOTALL)
                if m:
                    normalized_ces.append(CEOutput(codigo=m.group(1), texto=m.group(2).strip(), mcn=[]))
                else:
                    normalized_ces.append(CEOutput(codigo="CE", texto=ce.strip(), mcn=[]))
            elif isinstance(ce, dict):
                normalized_ces.append(CEOutput(**ce))
            else:
                normalized_ces.append(CEOutput(codigo="CE", texto=str(ce), mcn=[]))
        data["competencias_especificas"] = normalized_ces
        return MateriaOutput(**data)
    except Exception as e:
        print(f"[extractor_agent] Could not parse response for {materia}: {e}")
        print(f"[extractor_agent] Raw response: {final_response[:300]}")
        return MateriaOutput(
            nombre=materia,
            competencias_especificas=[],
            contenidos=[],
            criterios=[],
            patron_detectado="parse_error",
        )


def run_extraction(tables: list, materia: str, config: dict) -> MateriaOutput:
    """
    Initializes the ADK Runner and executes the extractor agent for a given materia.

    Args:
        tables: List of RawTable objects (or dicts) from pdf_reader.extract_tables.
        materia: Materia key (e.g. "matematica", "lengua_espanola").
        config: Full config dict from config.yaml.

    Returns:
        MateriaOutput with extracted curriculum data.
    """
    return asyncio.run(_run_extraction_async(tables, materia, config))
