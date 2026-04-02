#!/usr/bin/env python3
"""
Deterministic curriculum structure extractor.
Parses EBI 2023 curriculum PDF text from Open Notebook API
and produces a structured JSON file - NO LLM used.
"""

import re
import json
import requests
import logging
import unicodedata
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

API_URL = "http://localhost:5055/api/sources/source:bhkk4eb0in06gd582noc"
OUTPUT_PATH = "/home/jgnacio/Documents/Bit-A/planificacion_curricular_v3/data/curriculum_structure.json"

# ---------------------------------------------------------------------------
# Known materias and the espacio they belong to
# Each entry: (display_name, slug, espacio_slug)
# Lines are multi-line headers in the PDF text — we concatenate them.
# ---------------------------------------------------------------------------
MATERIA_DEFS = [
    # Espacio Científico-Matemático
    ("Matemática", "matematica", "espacio_cientifico_matematico"),
    ("Física Química", "fisica_quimica", "espacio_cientifico_matematico"),
    ("Ciencias del Ambiente (Biología)", "ciencias_del_ambiente", "espacio_cientifico_matematico"),
    ("Ciencias de la Tierra y el Espacio\n(Geología y Astronomía)", "ciencias_de_la_tierra", "espacio_cientifico_matematico"),
    # Espacio de Comunicación
    ("Lengua Española", "lengua_espanola", "espacio_comunicacion"),
    ("Segundas Lenguas y Lenguas\nExtranjeras", "segundas_lenguas", "espacio_comunicacion"),
    # Espacio Ciencias Sociales y Humanidades
    ("Historia", "historia", "espacio_ciencias_sociales"),
    ("Formación para\nla Ciudadanía", "formacion_ciudadania", "espacio_ciencias_sociales"),
    ("Geografía", "geografia", "espacio_ciencias_sociales"),
    # Espacio Creativo-Artístico
    ("Artes Visuales y Plásticas", "artes_visuales", "espacio_creativo_artistico"),
    ("Música", "musica", "espacio_creativo_artistico"),
    ("Literatura", "literatura", "espacio_creativo_artistico"),
    ("Teatro", "teatro", "espacio_creativo_artistico"),
    ("Danza", "danza", "espacio_creativo_artistico"),
    ("Conciencia y Conocimiento\nCorporal", "conciencia_corporal", "espacio_creativo_artistico"),
    # Espacio de Desarrollo Personal y Conciencia Corporal
    ("Educación Física", "educacion_fisica", "espacio_desarrollo_personal"),
    # Espacio Técnico-Tecnológico
    ("Ciencias de la Computación y\nTecnología Educativa", "ciencias_computacion", "espacio_tecnico_tecnologico"),
]

ESPACIO_NAMES = {
    "espacio_cientifico_matematico": "Espacio Científico-Matemático",
    "espacio_comunicacion": "Espacio de Comunicación",
    "espacio_ciencias_sociales": "Espacio Ciencias Sociales y Humanidades",
    "espacio_creativo_artistico": "Espacio Creativo-Artístico",
    "espacio_desarrollo_personal": "Espacio de Desarrollo Personal y Conciencia Corporal",
    "espacio_tecnico_tecnologico": "Espacio Técnico-Tecnológico",
}

TRAMO_HEADERS = {
    "tramo_3": "Tramo 3 | Grados 3.o y 4.o",
    "tramo_4": "Tramo 4 | Grados 5.o y 6.o",
}
# OCR variants for Tramo 4 (some pages render "degrees" instead of "o")
TRAMO_4_VARIANTS = {
    "Tramo 4 | Grados 5. degrees y 6. degrees",
    "Tramo 4 | Grados 5.o y 6.o",
}

GRADE_MAP = {
    "3": "3er_grado",
    "4": "4to_grado",
    "5": "5to_grado",
    "6": "6to_grado",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_text() -> str:
    log.info("Fetching curriculum text from API...")
    resp = requests.get(API_URL, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    text = data["full_text"]
    log.info(f"Fetched {len(text):,} chars")
    return text


def fix_hyphenation(lines: list[str]) -> list[str]:
    """Join lines where the previous line ends with a hyphen (PDF line-break artifact)."""
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        while line.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1]
            # Only join if next line is not a new paragraph / header indicator
            if next_line.strip() and not next_line.startswith("CE") and not re.match(r"^\d+$", next_line.strip()):
                line = line[:-1] + next_line
                i += 1
            else:
                break
        result.append(line)
        i += 1
    return result


def is_page_number(line: str) -> bool:
    return bool(re.match(r"^\s*\d{1,3}\s*$", line))


def is_single_letter(line: str) -> bool:
    """Single uppercase letter/accented character = PDF table column artifact."""
    s = line.strip()
    return len(s) == 1 and (s.isupper() or unicodedata.category(s) == "Lu")


def clean_lines(raw_lines: list[str]) -> list[str]:
    """Remove page numbers and single-letter column artifacts."""
    return [l for l in raw_lines if not is_page_number(l) and not is_single_letter(l)]


def slug(text: str) -> str:
    """Convert text to a lowercase underscore slug, stripping accents."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_str.lower()).strip("_")


def join_continuation_lines(lines: list[str], start: int, end: int) -> str:
    """Join a slice of lines into a single string, collapsing whitespace."""
    return " ".join(l.strip() for l in lines[start:end] if l.strip())


# ---------------------------------------------------------------------------
# Finding section boundaries
# ---------------------------------------------------------------------------

def find_materia_sections(lines: list[str]) -> list[dict]:
    """
    Locate the start line index for every materia section header.
    Some headers span 2 lines (e.g., 'Ciencias de la Tierra y el Espacio' + '(Geología y Astronomía)').
    Returns list of {name, slug, espacio_slug, line_idx} sorted by line_idx.
    """
    sections = []

    for display_name, mat_slug, esp_slug in MATERIA_DEFS:
        parts = display_name.split("\n")
        first_part = parts[0].strip()
        second_part = parts[1].strip() if len(parts) > 1 else None

        for i, line in enumerate(lines):
            if line.strip() != first_part:
                continue
            # Check second part if multi-line
            if second_part:
                if i + 1 < len(lines) and lines[i + 1].strip() == second_part:
                    sections.append({
                        "nombre": display_name.replace("\n", " "),
                        "slug": mat_slug,
                        "espacio_slug": esp_slug,
                        "line_idx": i,
                    })
            else:
                # Single-line header — make sure it's not in the table of contents (has '.....' dots)
                if "..." not in line and "." * 5 not in line:
                    sections.append({
                        "nombre": first_part,
                        "slug": mat_slug,
                        "espacio_slug": esp_slug,
                        "line_idx": i,
                    })

    # Sort by first occurrence
    seen_slugs = set()
    unique = []
    for s in sorted(sections, key=lambda x: x["line_idx"]):
        if s["slug"] not in seen_slugs:
            seen_slugs.add(s["slug"])
            unique.append(s)

    log.info(f"Found {len(unique)} materia sections")
    return unique


def is_tramo_line(line: str) -> tuple[str, str] | None:
    """Return (tramo_key, canonical_label) if line is a Tramo header, else None."""
    s = line.strip()
    if s == TRAMO_HEADERS["tramo_3"]:
        return ("tramo_3", TRAMO_HEADERS["tramo_3"])
    if s in TRAMO_4_VARIANTS:
        return ("tramo_4", TRAMO_HEADERS["tramo_4"])
    return None


def find_tramo_boundaries(lines: list[str], start_idx: int, end_idx: int) -> list[dict]:
    """
    Within a materia's range, find Tramo 3 and Tramo 4 sub-sections.
    Returns list of {tramo_key, label, line_idx}.
    """
    found = []
    for i in range(start_idx, end_idx):
        result = is_tramo_line(lines[i])
        if result:
            tramo_key, label = result
            found.append({"tramo_key": tramo_key, "label": label, "line_idx": i})
    return found


# ---------------------------------------------------------------------------
# CE parsing
# ---------------------------------------------------------------------------

def parse_ces(lines: list[str], start_idx: int, end_idx: int) -> list[dict]:
    """
    Parse competencias específicas from the CE header block.
    CE text spans multiple lines; MCN list follows 'Contribuye al desarrollo de las competencias
    generales del MCN:' phrase.
    """
    # Find the CE header within this range
    # Search the FULL range (no artificial +50 limit — it was too restrictive)
    ce_start = None
    for i in range(start_idx, end_idx):
        line = lines[i]
        if "Competencias específicas de la unidad curricular" in line:
            # Skip to line after the header (next 1-2 lines are the title continuation)
            ce_start = i + 1
            while ce_start < end_idx and not re.match(r"CE\d+[\.\s]", lines[ce_start]):
                ce_start += 1
            break

    if ce_start is None:
        log.warning(f"  CE header not found in lines {start_idx}–{end_idx}")
        return []

    # Collect text from ce_start until next major section
    # (any Contenidos section, Tramo header, Criterios, or end)
    ce_end = end_idx
    for i in range(ce_start, end_idx):
        line = lines[i].strip()
        # Stop at any Contenidos section
        if re.match(r"Contenidos (específicos|estructurantes)", line):
            ce_end = i
            break
        # Stop at Criterios section
        if re.match(r"Criterios de logro", line):
            ce_end = i
            break
        # Stop at Tramo headers (both variants, including OCR variants)
        if is_tramo_line(line) is not None:
            ce_end = i
            break

    # Join all CE lines into a single string for regex
    block = " ".join(l.strip() for l in lines[ce_start:ce_end] if l.strip())

    # Extract individual CEs
    ces = []
    # Split on CE1., CE1.1., CE1.2., CE1 (space, no dot), etc.
    # Order matters: try decimal first (CE1.1.), then integer (CE1.) then no-dot (CE1 )
    ce_pattern = re.compile(r"CE(\d+(?:\.\d+)?)[\.:]?\s+")
    matches = list(ce_pattern.finditer(block))

    for j, m in enumerate(matches):
        code = f"CE{m.group(1)}"
        text_start = m.end()
        text_end = matches[j + 1].start() if j + 1 < len(matches) else len(block)
        full_text = block[text_start:text_end].strip()

        # Split on MCN contribution phrase
        mcn_split = re.split(
            r"Contribuye al desarrollo de las competencias generales del MCN[:.]?\s*",
            full_text,
            maxsplit=1,
        )
        ce_texto = mcn_split[0].strip().rstrip(".")
        mcn_list = []
        if len(mcn_split) > 1:
            mcn_raw = mcn_split[1].strip().rstrip(".")
            # Parse MCN items: comma-separated, may end with 'e Intrapersonal' style
            mcn_raw = re.sub(r"\s+", " ", mcn_raw)
            # Fix common hyphenation artifacts that left internal spaces in competencia names
            mcn_raw = re.sub(r"\bPensa miento\b", "Pensamiento", mcn_raw)
            mcn_raw = re.sub(r"\bComu nicación\b", "Comunicación", mcn_raw)
            mcn_raw = re.sub(r"\bIntra personal\b", "Intrapersonal", mcn_raw)
            mcn_raw = re.sub(r"\bMeta cognitiva\b", "Metacognitiva", mcn_raw)
            mcn_raw = re.sub(r"\bCiudadanía lo cal\b", "Ciudadanía local", mcn_raw)
            mcn_raw = re.sub(r"\blo cal\b", "local", mcn_raw)
            mcn_raw = re.sub(r"\bdi gital\b", "digital", mcn_raw)
            # Protect compound names before splitting:
            # "Ciudadanía local, global y digital" → treat as one item
            mcn_raw = re.sub(
                r"Ciudadanía local,\s*global\s*[ye]\s*digital",
                "Ciudadanía local-global-digital",
                mcn_raw
            )
            # Normalize "y X" and "e X" at end
            mcn_raw = re.sub(r"\s+[ye]\s+([A-ZÁÉÍÓÚ])", r", \1", mcn_raw)
            mcn_items = [x.strip().rstrip(".") for x in mcn_raw.split(",") if x.strip()]
            # Restore compound name
            mcn_list = [
                "Ciudadanía local, global y digital" if x == "Ciudadanía local-global-digital" else x
                for x in mcn_items
            ]

        ces.append({
            "codigo": code,
            "texto": ce_texto,
            "mcn": mcn_list,
        })

    return ces


# ---------------------------------------------------------------------------
# Contenidos parsing
# ---------------------------------------------------------------------------

def parse_contenidos_block(lines: list[str], start_idx: int, end_idx: int, grade_num: str) -> dict:
    """
    Parse one grade's contenidos block.
    Two formats exist:
      1. Table with ejes (Matemática-style): vertical letters = eje, then content estructurante + items
      2. Simple list (Física Química-style): content line + CE codes on next lines

    Returns dict matching schema's 'items' list structure.
    """
    grade_key = GRADE_MAP.get(grade_num, f"{grade_num}to_grado")

    # Find the actual data start — skip header lines ('Contenidos estructurantes', 'Ejes', etc.)
    data_start = start_idx
    for i in range(start_idx, min(start_idx + 20, end_idx)):
        line = lines[i].strip()
        if re.match(r"Contenidos específicos de", line):
            data_start = i + 1
            break

    # Skip table header lines and preamble text
    skip_words = {
        "Contenidos estructurantes", "Ejes", "Contenidos específicos",
        "Competencias específicas", "Competencias", "específicas",
        "específicas relacionadas", "Los vínculos", "criterios de logro",
        "jerarquización sin ser excluyentes.", "que se detallan", "entre las competencias",
        "estructurantes", "del tramo", "Contenidos para la", "profundización y",
        "contextualización", "Criterio de logro",
        "competencias específicas de la unidad curricular",
        "Los vínculos que se detallan en la siguiente tabla",
    }
    skip_patterns_cont = [
        r"^Los vínculos",
        r"^criterios de logro responden",
        r"^jerarquización sin ser",
    ]

    # Detect format: if there are single-letter lines before the first '*' item → table format
    # (we already stripped single letters in clean_lines, but check for NÚMERO, FIGURA, etc.)
    # Look for contenido estructurante patterns (UPPERCASE words like NÚMERO, FIGURA, VARIABLE)

    items = []
    current_eje = None
    current_estructurante = None
    current_especificos = []
    current_ces = []

    i = data_start
    while i < end_idx:
        line = lines[i].strip()
        i += 1

        if not line:
            continue
        if is_page_number(line):
            continue
        # Skip header artifacts (exact match or startswith)
        if line in skip_words or any(line.startswith(w) for w in skip_words):
            continue
        # Skip via patterns
        if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns_cont):
            continue

        # CE codes block: one or more CE\d+ lines (also handles "CE1, CE2" on same line)
        if re.match(r"^CE\d+[\d,\s]*$", line) or re.match(r"^CE\d+(?:[,\s]+CE\d+)*$", line):
            # Handle comma-separated CE codes on one line
            ce_codes = re.findall(r"CE\d+(?:\.\d+)?", line)
            current_ces.extend(ce_codes)
            # Collect consecutive CE code lines
            while i < end_idx and re.match(r"^CE\d+", lines[i].strip()):
                next_line = lines[i].strip()
                # Only if it's purely CE codes (no dot indicating CE body text)
                if re.match(r"^CE\d+(?:[,\s]+CE\d+)*\.?\s*$", next_line):
                    current_ces.extend(re.findall(r"CE\d+(?:\.\d+)?", next_line))
                    i += 1
                else:
                    break
            # Save current item group
            if current_estructurante or current_especificos:
                items.append({
                    "eje": current_eje or "",
                    "contenido_estructurante": current_estructurante or "",
                    "especificos": current_especificos[:],
                    "competencias_relacionadas": current_ces[:],
                })
                current_estructurante = None
                current_especificos = []
                current_ces = []
            continue

        # "Contenidos transversales" section marker — stop
        if line.startswith("Contenidos transversales"):
            break

        # Check if it's a bullet item
        if line.startswith("*") or line.startswith("-"):
            text = line.lstrip("*").lstrip("-").strip()
            if text:
                current_especificos.append(text)
            continue

        # Check if this looks like a contenido estructurante (capitalized noun phrase, no leading *)
        # In simple format (Física Química), lines without * are content items followed by CEs
        # Heuristic: if line doesn't match CE\d and not a skip word, treat as estructurante or content
        if re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s\(\),]+$", line) and len(line) > 3:
            # Could be a new contenido estructurante
            # If we have pending specificos with no estructurante, flush as one item
            if current_especificos:
                items.append({
                    "eje": current_eje or "",
                    "contenido_estructurante": current_estructurante or "",
                    "especificos": current_especificos[:],
                    "competencias_relacionadas": current_ces[:],
                })
                current_estructurante = None
                current_especificos = []
                current_ces = []
            current_estructurante = line
        else:
            # General text line — treat as a specific content item
            if line:
                current_especificos.append(line)

    # Flush last pending item
    if current_especificos or current_estructurante:
        items.append({
            "eje": current_eje or "",
            "contenido_estructurante": current_estructurante or "",
            "especificos": current_especificos[:],
            "competencias_relacionadas": current_ces[:],
        })

    label_map = {
        "3": "Contenidos específicos de 3.er grado",
        "4": "Contenidos específicos de 4.to grado",
        "5": "Contenidos específicos de 5.to grado",
        "6": "Contenidos específicos de 6.to grado",
    }

    return {
        "label": label_map.get(grade_num, f"Contenidos específicos de grado {grade_num}"),
        "items": items,
    }


def parse_contenidos(lines: list[str], tramo_start: int, tramo_end: int) -> dict:
    """
    Parse all grade contenidos blocks within a tramo range.
    Returns dict keyed by grade slug.
    """
    result = {}

    # Find all 'Contenidos específicos de X grado' headers in range.
    # Also handles combined headers like:
    #   "Contenidos específicos, criterios de logro de 3.er grado..."
    contenidos_headers = []
    for i in range(tramo_start, tramo_end):
        line = lines[i].strip()
        # Standard: "Contenidos específicos de 3.er grado..."
        m = re.match(r"Contenidos específicos de (\d+)[\.\º]?(?:er|to|.o)? grado", line)
        if m:
            contenidos_headers.append({"grade": m.group(1), "line_idx": i})
            continue
        # Combined: "Contenidos específicos, criterios de logro de 3.er grado..."
        m2 = re.match(r"Contenidos específicos,?\s+criterios? de logro.*?de (\d+)[\.\º]?(?:er|to|.o)? grado", line)
        if m2:
            contenidos_headers.append({"grade": m2.group(1), "line_idx": i})
            continue
        # Split across lines: "Contenidos específicos de" on one line, "de 3.er grado" on next
        m3 = re.match(r"Contenidos específicos de$", line)
        if m3 and i + 1 < tramo_end:
            next_line = lines[i + 1].strip()
            m4 = re.match(r"(\d+)[\.\º]?(?:er|to|.o)? grado", next_line)
            if m4:
                contenidos_headers.append({"grade": m4.group(1), "line_idx": i})

    # Deduplicate — keep first occurrence per grade (some have intro + table header duplicates)
    seen_grades = {}
    unique_headers = []
    for h in contenidos_headers:
        if h["grade"] not in seen_grades:
            seen_grades[h["grade"]] = h
            unique_headers.append(h)

    # For each grade, parse until next grade header or criterios or tramo_end
    criterios_starts = []
    for i in range(tramo_start, tramo_end):
        line = lines[i].strip()
        if re.match(r"Criterios de logro", line):
            criterios_starts.append(i)

    next_boundaries = sorted(
        [h["line_idx"] for h in unique_headers] + criterios_starts + [tramo_end]
    )

    for h in unique_headers:
        grade = h["grade"]
        grade_key = GRADE_MAP.get(grade, f"{grade}to_grado")
        h_start = h["line_idx"]

        # End = next boundary after h_start
        h_end = tramo_end
        for b in next_boundaries:
            if b > h_start:
                h_end = b
                break

        block = parse_contenidos_block(lines, h_start, h_end, grade)
        result[grade_key] = block

    return result


# ---------------------------------------------------------------------------
# Criterios parsing
# ---------------------------------------------------------------------------

def parse_criterios_block(lines: list[str], start_idx: int, end_idx: int, grade_num: str) -> dict:
    """
    Parse criterios de logro for one grade.
    Pattern (Matemática-style):
      * bullet text (criterion for the NEXT CE)
      CE1. short description across multiple lines
      * more bullets
      CE2. ...

    Pattern (simple style like Física Química):
      criterion text lines
      CE1 (or CE1.)
      more criterion text
      CE2
    """
    grade_key = GRADE_MAP.get(grade_num, f"{grade_num}to_grado")

    # Find data start — skip title lines
    data_start = start_idx
    for i in range(start_idx, min(start_idx + 15, end_idx)):
        line = lines[i].strip()
        if re.match(r"Criterios de logro", line):
            data_start = i + 1
            break

    # Skip sub-header artifacts
    skip_patterns = [
        r"^Criterios? de logro",
        r"^Competencias?$",
        r"^Competencias específicas$",
        r"^Competencia específica$",
        r"^específicas?$",
        r"^relacionadas?$",
        r"^Los criterios de logro",
        r"^Todos ellos son válidos",
        r"^válidos para considerar",
        r"^criterios de logro responden",
        r"^Los vínculos",
        r"^Los criterios",
        r"^jerarquización sin ser",
        r"^competencias específicas$",
        r"^de la unidad curricular$",
    ]

    por_competencia = {}
    pending_bullets = []
    current_ce = None

    i = data_start
    while i < end_idx:
        raw_line = lines[i]
        line = raw_line.strip()
        i += 1

        if not line:
            continue
        if is_page_number(line):
            continue

        # Check skip patterns
        should_skip = False
        for pat in skip_patterns:
            if re.match(pat, line, re.IGNORECASE):
                should_skip = True
                break
        if should_skip:
            continue

        # CE marker: "CE1." or "CE1" standalone (could span 2 lines in Matemática)
        ce_match_full = re.match(r"^(CE\d+)\.\s+(.*)", line)  # CE1. texto...
        ce_match_bare = re.match(r"^(CE\d+)$", line)  # CE1 alone

        if ce_match_full:
            # Flush pending bullets to previous CE or as orphans
            if pending_bullets and current_ce:
                por_competencia.setdefault(current_ce, []).extend(pending_bullets)
                pending_bullets = []

            new_ce = ce_match_full.group(1)
            # Assign pending_bullets to this new CE (they were before this CE marker)
            if pending_bullets:
                por_competencia.setdefault(new_ce, []).extend(pending_bullets)
                pending_bullets = []
            current_ce = new_ce

            # Collect multi-line CE description (not bullets, not page numbers, not numbered criteria)
            # These lines are the CE sidebar text — skip until next bullet, CE, or numbered criterion
            while i < end_idx:
                next_line = lines[i].strip()
                if (next_line.startswith("*") or re.match(r"^CE\d+", next_line)
                        or is_page_number(next_line) or not next_line
                        or re.match(r"^\d+\.\s+[A-ZÁÉÍÓÚÑ]", next_line)):
                    break
                i += 1
            continue

        if ce_match_bare:
            # Simple style: CE code alone
            new_ce = ce_match_bare.group(1)
            if pending_bullets:
                por_competencia.setdefault(new_ce, []).extend(pending_bullets)
                pending_bullets = []
            current_ce = new_ce
            continue

        # Bullet item (Matemática-style: * texto)
        if line.startswith("*") or line.startswith("-"):
            text = line.lstrip("*").lstrip("-").strip()
            if text:
                pending_bullets.append(text)
            continue

        # Numbered criterion (Lengua-style: "1. Planifica y expone...")
        # These belong to current_ce (CE was defined before them)
        # Join continuation lines (next lines that don't start a new item)
        num_match = re.match(r"^\d+\.\s+([A-ZÁÉÍÓÚÑ].+)", line)
        if num_match:
            text = num_match.group(1).strip()
            # Join continuation lines (lowercase start = continuation of same sentence)
            while i < end_idx:
                next_line = lines[i].strip()
                if (not next_line or is_page_number(next_line)
                        or re.match(r"^\d+\.\s+", next_line)
                        or re.match(r"^CE\d+", next_line)
                        or re.match(r"^\*", next_line)):
                    break
                # Continuation: starts with lowercase or mid-sentence word
                text = text.rstrip(".") + " " + next_line if not text.endswith(".") else text + " " + next_line
                i += 1
            if text and current_ce:
                por_competencia.setdefault(current_ce, []).append(text.strip())
            continue

        # Non-bullet text line that's not a CE marker — could be a criterion in simple format
        # Only add if it looks like a criterion sentence (starts with uppercase verb)
        if re.match(r"^[A-ZÁÉÍÓÚÑ]", line) and len(line) > 10:
            pending_bullets.append(line)

    # Flush remaining
    if pending_bullets and current_ce:
        por_competencia.setdefault(current_ce, []).extend(pending_bullets)

    label_map = {
        "3": "Criterios de logro para la evaluación de 3.er grado",
        "4": "Criterios de logro para la evaluación de 4.to grado",
        "5": "Criterios de logro para la evaluación de 5.to grado",
        "6": "Criterios de logro para la evaluación de 6.to grado",
    }

    return {
        "label": label_map.get(grade_num, f"Criterios de logro grado {grade_num}"),
        "por_competencia": por_competencia,
    }


def parse_criterios(lines: list[str], tramo_start: int, tramo_end: int) -> dict:
    """
    Parse all grade criterios blocks within a tramo range.
    Returns dict keyed by grade slug.
    """
    result = {}

    # Find all criterios headers in range. Multiple formats:
    #   "Criterios de logro para la evaluación de 3.er grado..."
    #   "Criterios de logro - 3.er grado"
    #   "Contenidos específicos, criterios de logro de 3.er grado..." (combined)
    criterios_headers = []
    for i in range(tramo_start, tramo_end):
        line = lines[i].strip()
        # Standard long form
        m = re.match(r"Criterios de logro para la evaluación de (\d+)[\.\º]?(?:er|to|.o)? grado", line)
        if m:
            criterios_headers.append({"grade": m.group(1), "line_idx": i})
            continue
        # Short form with dash: "Criterios de logro - 3.er grado"
        m2 = re.match(r"Criterio[s]? de logro[s]?\s*[-–]\s*(\d+)[\.\º]?(?:er|to|.o)? grado", line)
        if m2:
            criterios_headers.append({"grade": m2.group(1), "line_idx": i})
            continue
        # Combined contenidos+criterios header
        m3 = re.match(r"Contenidos específicos,?\s+criterios? de logro.*?de (\d+)[\.\º]?(?:er|to|.o)? grado", line)
        if m3:
            criterios_headers.append({"grade": m3.group(1), "line_idx": i})
            continue

    # Deduplicate
    seen_grades = {}
    unique_headers = []
    for h in criterios_headers:
        if h["grade"] not in seen_grades:
            seen_grades[h["grade"]] = h
            unique_headers.append(h)

    # Boundary detection
    all_bounds = sorted([h["line_idx"] for h in unique_headers] + [tramo_end])

    for idx, h in enumerate(unique_headers):
        grade = h["grade"]
        if grade == "?":
            continue
        grade_key = GRADE_MAP.get(grade, f"{grade}to_grado")
        h_start = h["line_idx"]
        h_end = all_bounds[idx + 1] if idx + 1 < len(all_bounds) else tramo_end

        block = parse_criterios_block(lines, h_start, h_end, grade)
        result[grade_key] = block

    return result


# ---------------------------------------------------------------------------
# Main tramo parsing
# ---------------------------------------------------------------------------

def parse_tramo_section(
    lines: list[str],
    tramo_key: str,
    tramo_label: str,
    tramo_start: int,
    tramo_end: int,
    materia_nombre: str,
    materia_slug: str,
) -> dict:
    """
    Parse a single tramo block for a materia.
    Returns the materia data dict for this tramo.
    """
    log.info(f"  Parsing {materia_nombre} / {tramo_label} (lines {tramo_start}–{tramo_end})")

    # Some materias (e.g. Matemática Tramo 4) have the CE section BEFORE the Tramo header.
    # In that case the CE header will be found in the window [tramo_start-80, tramo_start].
    # Try normal range first; if no CEs found, try looking backward.
    ces = parse_ces(lines, tramo_start, tramo_end)
    if not ces:
        # Look backward up to 100 lines before the tramo start
        lookback_start = max(0, tramo_start - 100)
        ces = parse_ces(lines, lookback_start, tramo_start)
        if ces:
            log.info(f"    CEs found by lookback before {tramo_key} header")
    log.info(f"    CEs found: {len(ces)}")

    # Parse contenidos
    contenidos = parse_contenidos(lines, tramo_start, tramo_end)
    log.info(f"    Contenidos grades found: {list(contenidos.keys())}")

    # Parse criterios
    criterios = parse_criterios(lines, tramo_start, tramo_end)
    log.info(f"    Criterios grades found: {list(criterios.keys())}")

    return {
        "nombre": materia_nombre,
        "competencias_especificas": ces,
        "contenidos": contenidos,
        "criterios": criterios,
    }


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def build_structure(lines: list[str]) -> dict:
    """Build the full curriculum structure."""
    materia_sections = find_materia_sections(lines)

    # Build output structure
    tramos_out = {
        "tramo_3": {
            "label": TRAMO_HEADERS["tramo_3"],
            "espacios": {esp: {"nombre": name, "materias": {}} for esp, name in ESPACIO_NAMES.items()},
        },
        "tramo_4": {
            "label": TRAMO_HEADERS["tramo_4"],
            "espacios": {esp: {"nombre": name, "materias": {}} for esp, name in ESPACIO_NAMES.items()},
        },
    }

    for idx, mat in enumerate(materia_sections):
        mat_start = mat["line_idx"]
        mat_end = materia_sections[idx + 1]["line_idx"] if idx + 1 < len(materia_sections) else len(lines)

        log.info(f"Processing materia: {mat['nombre']} (lines {mat_start}–{mat_end})")

        tramo_bounds = find_tramo_boundaries(lines, mat_start, mat_end)

        if not tramo_bounds:
            log.warning(f"  No Tramo headers found for {mat['nombre']}")
            continue

        for t_idx, tramo in enumerate(tramo_bounds):
            t_start = tramo["line_idx"]
            t_key = tramo["tramo_key"]
            t_end = tramo_bounds[t_idx + 1]["line_idx"] if t_idx + 1 < len(tramo_bounds) else mat_end

            materia_data = parse_tramo_section(
                lines,
                t_key,
                tramo["label"],
                t_start,
                t_end,
                mat["nombre"],
                mat["slug"],
            )

            tramos_out[t_key]["espacios"][mat["espacio_slug"]]["materias"][mat["slug"]] = materia_data

    return {
        "tramos": tramos_out,
        "metadata": {
            "source": "source:bhkk4eb0in06gd582noc",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "version": "EBI 2023",
        },
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(structure: dict):
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)

    total_materias = 0
    total_ces = 0
    total_contenidos_items = 0
    total_criterios = 0

    for tramo_key, tramo_data in structure["tramos"].items():
        print(f"\n{tramo_data['label']}")
        for esp_key, esp_data in tramo_data["espacios"].items():
            materias = esp_data.get("materias", {})
            if not materias:
                continue
            print(f"  {esp_data['nombre']}")
            for mat_slug, mat_data in materias.items():
                ces = mat_data.get("competencias_especificas", [])
                cont_items = sum(
                    len(g.get("items", []))
                    for g in mat_data.get("contenidos", {}).values()
                )
                crit_count = sum(
                    sum(len(v) for v in g.get("por_competencia", {}).values())
                    for g in mat_data.get("criterios", {}).values()
                )
                print(f"    {mat_data['nombre']}: {len(ces)} CEs, "
                      f"{cont_items} contenido groups, {crit_count} criterios")
                total_materias += 1
                total_ces += len(ces)
                total_contenidos_items += cont_items
                total_criterios += crit_count

    print(f"\nTOTALS:")
    print(f"  Materias parsed: {total_materias}")
    print(f"  CEs total: {total_ces}")
    print(f"  Contenidos item groups: {total_contenidos_items}")
    print(f"  Criterio bullets total: {total_criterios}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    raw_text = fetch_text()
    raw_lines = raw_text.splitlines()
    log.info(f"Raw lines: {len(raw_lines)}")

    # Step 1: fix hyphenation
    lines = fix_hyphenation(raw_lines)
    log.info(f"Lines after hyphenation fix: {len(lines)}")

    # Step 2: clean (remove page numbers and single-letter column artifacts)
    lines = clean_lines(lines)
    log.info(f"Lines after cleanup: {len(lines)}")

    # Step 3: build structure
    structure = build_structure(lines)

    # Step 4: save
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)

    log.info(f"Saved to {OUTPUT_PATH}")
    print_summary(structure)

    # Validate JSON
    with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
        reloaded = json.load(f)
    log.info("JSON validation: OK")


if __name__ == "__main__":
    main()
