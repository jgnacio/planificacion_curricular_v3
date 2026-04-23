"""
section_finder.py — Reads the TOC from pages 7-9 of a curriculum PDF
and returns page ranges per tramo per materia.
"""

from dataclasses import dataclass, field
import pdfplumber
import re
import unicodedata


@dataclass
class PageRange:
    start: int  # 0-indexed
    end: int    # exclusive


# Mapping from normalized text patterns to materia keys (longest patterns first)
_MATERIA_PATTERNS: list[tuple[str, str]] = [
    ("matematica", "matematica"),
    ("lengua espanola", "lengua_espanola"),
    ("lenguas extranjeras", "lenguas_extranjeras"),
    ("historia", "historia"),
    ("geografia", "geografia"),
    ("formacion para la ciudadania", "formacion_ciudadania"),
    ("formacion ciudadana", "formacion_ciudadania"),
    ("ciudadania", "formacion_ciudadania"),
    ("fisica y quimica", "fisica_quimica"),
    ("fisica quimica", "fisica_quimica"),
    ("ciencias del ambiente", "ciencias_ambiente"),
    ("ciencias de la tierra", "ciencias_tierra"),
    ("artes visuales", "artes_visuales"),
    ("musica", "musica"),
    ("literatura", "literatura"),
    ("teatro", "teatro"),
    ("danza", "danza"),
    ("conciencia y conocimiento corporal", "conciencia_corporal"),
    ("conciencia corporal", "conciencia_corporal"),
    ("educacion fisica", "educacion_fisica"),
    ("computacion", "computacion"),
]

_TRAMO_PATTERNS: list[tuple[str, str]] = [
    ("tramo 1", "tramo_1"),
    ("tramo 2", "tramo_2"),
    ("tramo 3", "tramo_3"),
    ("tramo 4", "tramo_4"),
]


def _normalize(text: str) -> str:
    """Lowercase + strip accents."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _match_materia(line_norm: str) -> str | None:
    for pattern, key in _MATERIA_PATTERNS:
        if pattern in line_norm:
            return key
    return None


def _match_tramo(line_norm: str) -> str | None:
    for pattern, key in _TRAMO_PATTERNS:
        if pattern in line_norm:
            return key
    return None


def _extract_page_num(line: str) -> int | None:
    m = re.search(r"(\d+)\s*$", line)
    if m:
        return int(m.group(1))
    return None


def find_sections(pdf_path: str) -> dict[str, dict[str, PageRange]]:
    """
    Reads TOC from pages 7-9 (0-indexed: 6-8) and returns
    {tramo_key: {materia_key: PageRange}}.

    The TOC lists materias with their tramo subsections, each with a page number.
    Falls back to hardcoded ranges if the TOC is not parseable.
    """
    # Collect (tramo_key, materia_key, start_page_1indexed) tuples
    entries: list[tuple[str, str, int]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            toc_end = min(10, total_pages)

            current_materia: str | None = None
            current_tramo: str | None = None

            for page_idx in range(6, toc_end):
                page = pdf.pages[page_idx]
                text = page.extract_text() or ""
                for raw_line in text.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    line_norm = _normalize(line)

                    tramo = _match_tramo(line_norm)
                    materia = _match_materia(line_norm)
                    page_num = _extract_page_num(line)

                    if materia and tramo and page_num:
                        # "Matemática Tramo 1 .... 28" — single line
                        entries.append((tramo, materia, page_num))
                        current_materia = materia
                        current_tramo = tramo
                    elif materia and page_num:
                        # "Matemática .... 28" — materia-level entry
                        current_materia = materia
                    elif tramo and page_num and current_materia:
                        # "  Tramo 1 .... 28" — tramo sub-entry under current materia
                        entries.append((tramo, current_materia, page_num))
                        current_tramo = tramo
                    elif materia:
                        current_materia = materia
                        current_tramo = None
                    elif tramo:
                        current_tramo = tramo

    except Exception as e:
        print(f"[section_finder] Warning: could not parse TOC: {e}")

    if not entries:
        print("[section_finder] TOC not found or empty, using hardcoded fallback ranges.")
        return _fallback_ranges()

    # Sort all entries by page number to compute end pages
    entries.sort(key=lambda x: x[2])

    # Build PageRange for each (tramo, materia) entry
    result: dict[str, dict[str, PageRange]] = {}
    for i, (tramo_key, materia_key, start_pdf) in enumerate(entries):
        start_idx = start_pdf - 1  # 0-indexed
        if i + 1 < len(entries):
            end_idx = entries[i + 1][2] - 1  # exclusive, 0-indexed
        else:
            end_idx = start_idx + 25

        if tramo_key not in result:
            result[tramo_key] = {}
        result[tramo_key][materia_key] = PageRange(start=start_idx, end=end_idx)

    total = sum(len(v) for v in result.values())
    print(f"[section_finder] Found {total} sections across {len(result)} tramos from TOC.")
    return result


def _fallback_ranges() -> dict[str, dict[str, PageRange]]:
    """
    Hardcoded fallback page ranges based on the actual PDF scan.
    Values are 0-indexed start, exclusive end.
    """
    ciclo1: dict[str, dict[str, PageRange]] = {
        "tramo_1": {
            "matematica":           PageRange(27, 33),
            "fisica_quimica":       PageRange(40, 44),
            "ciencias_ambiente":    PageRange(56, 62),
            "ciencias_tierra":      PageRange(69, 76),
            "lengua_espanola":      PageRange(93, 119),
            "lenguas_extranjeras":  PageRange(144, 156),
            "historia":             PageRange(183, 193),
            "formacion_ciudadania": PageRange(205, 212),
            "geografia":            PageRange(219, 226),
            "artes_visuales":       PageRange(245, 259),
            "musica":               PageRange(272, 282),
            "literatura":           PageRange(294, 305),
            "teatro":               PageRange(315, 321),
            "danza":                PageRange(330, 334),
            "conciencia_corporal":  PageRange(339, 346),
            "educacion_fisica":     PageRange(368, 381),
            "computacion":          PageRange(412, 417),
        },
        "tramo_2": {
            "matematica":           PageRange(33, 39),
            "fisica_quimica":       PageRange(44, 53),
            "ciencias_ambiente":    PageRange(62, 68),
            "ciencias_tierra":      PageRange(76, 83),
            "lengua_espanola":      PageRange(119, 143),
            "lenguas_extranjeras":  PageRange(156, 171),
            "historia":             PageRange(193, 204),
            "formacion_ciudadania": PageRange(212, 218),
            "geografia":            PageRange(226, 232),
            "artes_visuales":       PageRange(259, 271),
            "musica":               PageRange(282, 293),
            "literatura":           PageRange(305, 314),
            "teatro":               PageRange(321, 329),
            "danza":                PageRange(334, 338),
            "conciencia_corporal":  PageRange(346, 353),
            "educacion_fisica":     PageRange(381, 392),
            "computacion":          PageRange(417, 426),
        },
    }

    ciclo2: dict[str, dict[str, PageRange]] = {
        "tramo_3": {
            "matematica":           PageRange(29, 43),
            "fisica_quimica":       PageRange(57, 66),
            "ciencias_ambiente":    PageRange(78, 83),
            "ciencias_tierra":      PageRange(89, 95),
            "lengua_espanola":      PageRange(109, 124),
            "lenguas_extranjeras":  PageRange(140, 153),
            "historia":             PageRange(177, 190),
            "formacion_ciudadania": PageRange(209, 221),
            "geografia":            PageRange(234, 252),
            "artes_visuales":       PageRange(287, 300),
            "musica":               PageRange(313, 323),
            "literatura":           PageRange(334, 343),
            "teatro":               PageRange(353, 362),
            "danza":                PageRange(371, 377),
            "conciencia_corporal":  PageRange(384, 391),
            "educacion_fisica":     PageRange(412, 422),
            "computacion":          PageRange(452, 459),
        },
        "tramo_4": {
            "matematica":           PageRange(43, 56),
            "fisica_quimica":       PageRange(66, 75),
            "ciencias_ambiente":    PageRange(83, 88),
            "ciencias_tierra":      PageRange(95, 101),
            "lengua_espanola":      PageRange(124, 139),
            "lenguas_extranjeras":  PageRange(153, 166),
            "historia":             PageRange(190, 208),
            "formacion_ciudadania": PageRange(221, 233),
            "geografia":            PageRange(252, 272),
            "artes_visuales":       PageRange(300, 312),
            "musica":               PageRange(323, 333),
            "literatura":           PageRange(343, 352),
            "teatro":               PageRange(362, 370),
            "danza":                PageRange(377, 383),
            "conciencia_corporal":  PageRange(391, 398),
            "educacion_fisica":     PageRange(422, 432),
            "computacion":          PageRange(459, 467),
        },
    }

    # Return the union — caller selects by tramo_key
    return {**ciclo1, **ciclo2}
