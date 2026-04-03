#!/usr/bin/env python3
"""
Fix MCN competencias in curriculum_structure.json.

Two problems solved in one pass:
1. 86 CEs have empty mcn[] but mention MCN competencies in texto — parse them.
2. Existing mcn[] entries have OCR artifacts — normalize all to canonical names.
"""

import json
import re
import unicodedata
import difflib
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / "data" / "curriculum_structure.json"

# Canonical MCN competency names (ANEP official)
MCN_CANONICAL = [
    "Comunicación",
    "Pensamiento crítico",
    "Pensamiento creativo",
    "Pensamiento científico",
    "Pensamiento computacional",
    "Metacognitiva",
    "Intrapersonal",
    "Ciudadanía local, global y digital",
    "Relación con otros",
    "Iniciativa y orientación a la acción",
]

# Slug of each canonical name for matching
def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Collapse internal spaces (OCR splits words mid-token)
    text = re.sub(r"\s+", " ", text).strip()
    return text

MCN_SLUGS = {_slugify(c): c for c in MCN_CANONICAL}


def _normalize_one(raw: str) -> str | None:
    """Map a raw (possibly OCR-broken) MCN name to a canonical name."""
    raw_clean = re.sub(r"\s+", " ", raw).strip()
    slug = _slugify(raw_clean)

    # 1. Exact slug match
    if slug in MCN_SLUGS:
        return MCN_SLUGS[slug]

    # 2. Close match via difflib (cutoff 0.72 — generous for OCR noise)
    matches = difflib.get_close_matches(slug, MCN_SLUGS.keys(), n=1, cutoff=0.72)
    if matches:
        return MCN_SLUGS[matches[0]]

    # 3. Substring match — canonical slug is fully contained in raw slug or vice versa
    for canon_slug, canon_name in MCN_SLUGS.items():
        if canon_slug in slug or slug in canon_slug:
            return canon_name

    return None  # unrecognized — drop it


def parse_mcn_from_texto(texto: str) -> list[str]:
    """
    Extract MCN competencies from CE texto.
    Pattern: "competencias generales del MCN: X, Y, Z" (to end of string or period)
    OCR may split words with spaces or newlines.
    """
    # Normalize whitespace first (collapse OCR line-break artifacts)
    texto_norm = re.sub(r"[ \t]*\n[ \t]*", " ", texto)
    texto_norm = re.sub(r"\s{2,}", " ", texto_norm)

    # Find the MCN list marker
    match = re.search(
        r"(?:competencias generales del MCN|MCN)\s*[:：]\s*(.+?)(?:\.\s*$|\.$|$)",
        texto_norm,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return []

    raw_list = match.group(1)

    # Split on commas — but "Ciudadanía local, global y digital" has a comma inside
    # Strategy: split on comma, then try to merge adjacent tokens that together match a canonical name
    parts = [p.strip() for p in raw_list.split(",") if p.strip()]

    results = []
    i = 0
    while i < len(parts):
        part = parts[i]
        normalized = _normalize_one(part)
        if normalized:
            if normalized not in results:
                results.append(normalized)
            i += 1
        else:
            # Try merging with next part (handles "Ciudadanía local" + "global y digital")
            if i + 1 < len(parts):
                merged = part + ", " + parts[i + 1]
                normalized_merged = _normalize_one(merged)
                if normalized_merged:
                    if normalized_merged not in results:
                        results.append(normalized_merged)
                    i += 2
                    continue
            # Give up on this token
            i += 1

    return results


def normalize_mcn_list(raw_list: list[str]) -> list[str]:
    """Normalize an existing (populated but OCR-dirty) mcn list."""
    # Some entries are comma-joined inside a single string — split them first
    expanded = []
    for item in raw_list:
        if "." in item:
            # Multiple competencies joined with periods
            expanded.extend([p.strip() for p in item.split(".") if p.strip()])
        else:
            expanded.append(item)

    results = []
    for raw in expanded:
        norm = _normalize_one(raw)
        if norm and norm not in results:
            results.append(norm)
    return results


def fix_ce(ce: dict) -> tuple[list[str], str]:
    """
    Returns (new_mcn_list, action) where action is one of:
    'kept_empty', 'parsed', 'normalized', 'unchanged'
    """
    existing = ce.get("mcn", [])
    texto = ce.get("texto", "")

    if not existing:
        # Try to parse from texto
        parsed = parse_mcn_from_texto(texto)
        return parsed, ("parsed" if parsed else "kept_empty")
    else:
        normalized = normalize_mcn_list(existing)
        if normalized != existing:
            return normalized, "normalized"
        return existing, "unchanged"


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    stats = {"parsed": 0, "normalized": 0, "unchanged": 0, "kept_empty": 0}

    for tramo_key, tramo in data["tramos"].items():
        for esp_key, esp in tramo["espacios"].items():
            for ce in esp.get("competencias_especificas", []):
                new_mcn, action = fix_ce(ce)
                ce["mcn"] = new_mcn
                stats[action] += 1

            for mat_key, mat in esp.get("materias", {}).items():
                for ce in mat.get("competencias_especificas", []):
                    new_mcn, action = fix_ce(ce)
                    ce["mcn"] = new_mcn
                    stats[action] += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(stats.values())
    print(f"Total CEs procesadas: {total}")
    print(f"  Parseadas desde texto:  {stats['parsed']}")
    print(f"  Normalizadas (OCR fix): {stats['normalized']}")
    print(f"  Sin cambios:            {stats['unchanged']}")
    print(f"  Mantenidas vacías:      {stats['kept_empty']}")
    print(f"\nJSON actualizado: {JSON_PATH}")


if __name__ == "__main__":
    main()
