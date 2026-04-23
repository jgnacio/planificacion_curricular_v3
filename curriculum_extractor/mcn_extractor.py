"""
mcn_extractor.py — Extracts the 10 MCN general competencies from prose text
in the first pages of the curriculum PDF.
"""

import re
import pdfplumber


def _clean_text(text: str) -> str:
    """Normalize whitespace in extracted text."""
    # Replace multiple spaces/newlines with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_mcn_competencias(pdf_path: str) -> list[dict]:
    """
    Extracts 10 MCN general competencies from prose text in pages 9-20
    (0-indexed: 8-19).
    Returns list of {codigo, nombre, descripcion} dicts.
    """
    # Collect text from pages 8-19
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_idx in range(8, min(20, total_pages)):
                page = pdf.pages[page_idx]
                text = page.extract_text() or ""
                full_text += "\n" + text
    except Exception as e:
        print(f"[mcn_extractor] Error reading PDF {pdf_path}: {e}")
        return []

    competencias = _parse_competencias(full_text)

    if not competencias:
        print("[mcn_extractor] Warning: no MCN competencies found via primary parser.")
        competencias = _parse_competencias_fallback(full_text)

    print(f"[mcn_extractor] Extracted {len(competencias)} MCN competencies.")
    return competencias


def _parse_competencias(text: str) -> list[dict]:
    """
    Primary parser: looks for numbered competencies like:
      "1. Competencia name\nDescription..."
      or "Competencia 1\nName\nDescription..."
    """
    competencias = []

    # Try pattern: number followed by a competency name on the same line or next
    # Common in ANEP documents: "1. Competencia de comunicación\n..."
    pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,2})[.\)]\s+([^\n]{5,80})\n(.*?)(?=(?:^|\n)\s*\d{1,2}[.\)]|\Z)",
        re.DOTALL | re.MULTILINE,
    )

    for match in pattern.finditer(text):
        num = int(match.group(1))
        if num < 1 or num > 10:
            continue
        nombre = _clean_text(match.group(2))
        descripcion = _clean_text(match.group(3))
        if len(nombre) < 5 or len(descripcion) < 10:
            continue
        competencias.append({
            "codigo": f"MCN{num}",
            "nombre": nombre,
            "descripcion": descripcion[:500],  # cap at 500 chars
        })

    # Deduplicate by codigo, keep first occurrence
    seen: set[str] = set()
    unique = []
    for c in competencias:
        if c["codigo"] not in seen:
            seen.add(c["codigo"])
            unique.append(c)

    return unique[:10]  # at most 10


def _parse_competencias_fallback(text: str) -> list[dict]:
    """
    Fallback parser: looks for "Competencia N" patterns anywhere in the text.
    """
    competencias = []

    pattern = re.compile(
        r"Competencia\s+(\d{1,2})[:\s]+([^\n]{5,100})\n?(.*?)(?=Competencia\s+\d|\Z)",
        re.DOTALL | re.IGNORECASE,
    )

    for match in pattern.finditer(text):
        num = int(match.group(1))
        if num < 1 or num > 10:
            continue
        nombre = _clean_text(match.group(2))
        descripcion = _clean_text(match.group(3))
        competencias.append({
            "codigo": f"MCN{num}",
            "nombre": nombre,
            "descripcion": descripcion[:500],
        })

    seen: set[str] = set()
    unique = []
    for c in competencias:
        if c["codigo"] not in seen:
            seen.add(c["codigo"])
            unique.append(c)

    return unique[:10]
