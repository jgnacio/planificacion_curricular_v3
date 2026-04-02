"""
Extractor de texto desde PDFs digitales nativos usando pdfplumber.

Reemplaza ingestion/pdf_parser.py (PyMuPDF/fitz) con una implementación
que respeta el orden de lectura natural y extrae tablas con estructura.
"""
from __future__ import annotations

import pdfplumber


def extract_text_blocks(pdf_path: str) -> list[str]:
    """
    Extrae texto de un PDF digital nativo página por página.

    Returns:
        Lista de bloques de texto, uno por página con contenido.
        Las tablas se convierten a texto plano con separador ' | '.
    """
    blocks: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = _extract_page(page)
            if page_text.strip():
                blocks.append(page_text.strip())

    return blocks


def _extract_page(page) -> str:
    """Extrae texto y tablas de una página, combinándolos en orden."""
    # Bounding boxes de tablas para excluirlas del texto principal
    table_bboxes = [t.bbox for t in page.find_tables()]

    # Texto fuera de tablas
    if table_bboxes:
        non_table_page = page
        for bbox in table_bboxes:
            non_table_page = non_table_page.filter(
                lambda obj, bb=bbox: not _inside(obj, bb)
            )
        text = non_table_page.extract_text(layout=True) or ""
    else:
        text = page.extract_text(layout=True) or ""

    # Tablas como texto plano
    table_parts: list[str] = []
    for table in page.extract_tables():
        rows: list[str] = []
        for row in table:
            cells = [str(c).strip().replace("\n", " ") if c else "" for c in row]
            rows.append(" | ".join(cells))
        if rows:
            table_parts.append("\n".join(rows))

    if table_parts:
        return text + "\n\n" + "\n\n".join(table_parts)
    return text


def _inside(obj: dict, bbox: tuple[float, float, float, float]) -> bool:
    """Retorna True si el objeto está dentro del bounding box."""
    x0, y0, x1, y1 = bbox
    ox0 = obj.get("x0", obj.get("doctop", 0))
    oy0 = obj.get("top", obj.get("y0", 0))
    return ox0 >= x0 and oy0 >= y0 and ox0 <= x1 and oy0 <= y1
