#!/usr/bin/env python3
"""
Verifica que el texto extraído en los checkpoints JSON coincide literalmente
con el contenido del PDF fuente.
"""

import json
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF


BASE_DIR = Path("/home/jgnacio/Documents/Bit-A/planificacion_curricular_v3")
PDF_PATH = BASE_DIR / "pdfs" / "Compilación Programas 2do Ciclo.pdf"
CHECKPOINTS_DIR = BASE_DIR / "data" / "checkpoints"

FILES_TO_CHECK = [
    {
        "json": "tramo_4_espacio_cient_fico_matem_tico_matem_tica.json",
        "pages": (44, 56),  # 1-indexed, inclusive
        "label": "Matemática",
    },
    {
        "json": "tramo_4_espacio_cient_fico_matem_tico_f_sica_qu_mica.json",
        "pages": (67, 75),
        "label": "Física-Química",
    },
    {
        "json": "tramo_4_espacio_cient_fico_matem_tico_ciencias_del_ambiente_biolog_a_.json",
        "pages": (84, 88),
        "label": "Ciencias del Ambiente / Biología",
    },
]

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """Normaliza para búsqueda: minúsculas, sin tildes, colapsa espacios."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pdf_text(pdf: fitz.Document, page_start: int, page_end: int) -> tuple[str, str]:
    """Devuelve (raw_text, normalized_text) para el rango de páginas (1-indexed)."""
    raw_parts = []
    for page_num in range(page_start - 1, page_end):  # fitz es 0-indexed
        page = pdf[page_num]
        raw_parts.append(page.get_text())
    raw = "\n".join(raw_parts)
    return raw, normalize(raw)


def check_verbatim(text: str, pdf_raw: str, pdf_norm: str, label: str, path: str) -> dict:
    """
    Verifica si `text` aparece en el PDF.
    Retorna un dict con status y detalles.
    """
    if not text or not text.strip():
        return {"status": "skip", "reason": "vacío"}

    # 1) Búsqueda literal exacta
    if text in pdf_raw:
        return {"status": "ok"}

    # 2) Búsqueda normalizada (sin tildes, minúsculas, espacios colapsados)
    text_norm = normalize(text)
    if text_norm in pdf_norm:
        return {"status": "minor_variation", "detail": "diferencia de tildes/case/espacios"}

    # 3) Búsqueda por fragmentos (para textos largos con posibles saltos de línea)
    # Dividimos en frases de ≥15 chars y buscamos la mayoría
    sentences = [s.strip() for s in re.split(r"[.\n]", text) if len(s.strip()) >= 15]
    if sentences:
        found_count = sum(1 for s in sentences if normalize(s) in pdf_norm)
        ratio = found_count / len(sentences)
        if ratio >= 0.8:
            return {"status": "minor_variation", "detail": f"mayormente presente ({found_count}/{len(sentences)} frases)"}
        elif ratio >= 0.4:
            return {"status": "hallucination", "detail": f"solo {found_count}/{len(sentences)} frases encontradas", "text_sample": text[:120]}
        else:
            return {"status": "hallucination", "detail": "no encontrado en el PDF", "text_sample": text[:120]}

    # Texto corto no encontrado
    return {"status": "hallucination", "detail": "no encontrado en el PDF", "text_sample": text[:120]}


# ──────────────────────────────────────────────────────────────
# Verificación de un checkpoint
# ──────────────────────────────────────────────────────────────

SYMBOLS = {"ok": "✅", "minor_variation": "⚠️ ", "hallucination": "❌", "skip": "–"}

def verify_checkpoint(entry: dict, pdf: fitz.Document) -> None:
    label = entry["label"]
    json_path = CHECKPOINTS_DIR / entry["json"]
    page_start, page_end = entry["pages"]

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"  JSON: {entry['json']}")
    print(f"  PDF páginas: {page_start}–{page_end}")
    print(f"{'='*70}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    pdf_raw, pdf_norm = extract_pdf_text(pdf, page_start, page_end)

    total = 0
    counts = {"ok": 0, "minor_variation": 0, "hallucination": 0, "skip": 0}

    def check(text: str, field_path: str):
        nonlocal total
        result = check_verbatim(text, pdf_raw, pdf_norm, label, field_path)
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1
        if status != "ok":
            sym = SYMBOLS.get(status, "?")
            detail = result.get("detail", "")
            sample = result.get("text_sample", "")
            print(f"  {sym} [{field_path}]")
            if detail:
                print(f"      {detail}")
            if sample:
                print(f"      Texto: «{sample}»")
        if status != "skip":
            total += 1

    # ── Competencias específicas ──────────────────────────────
    for i, ce in enumerate(data.get("competencias_especificas", [])):
        codigo = ce.get("codigo", f"CE{i+1}")
        check(ce.get("descripcion", ""), f"CE[{codigo}].descripcion")
        for mcn in ce.get("contribuye_a_mcn", []):
            check(mcn, f"CE[{codigo}].contribuye_a_mcn → {mcn}")

    # ── Ejes ─────────────────────────────────────────────────
    for eje in data.get("ejes", []):
        eje_nombre = eje.get("nombre", "?")
        check(eje_nombre, f"eje.nombre → {eje_nombre[:40]}")
        for cont in eje.get("contenidos", []):
            cont_desc = cont.get("descripcion", "")
            check(cont_desc, f"  contenido.descripcion → {cont_desc[:50]}")
            for cr in cont.get("criterios_de_logro", []):
                check(cr.get("descripcion", ""), f"    criterio → {cr.get('descripcion','')[:50]}")
            for cr_rel in cont.get("competencias_relacionadas", []):
                check(cr_rel, f"    comp_relacionada → {cr_rel}")

    # ── Resumen ───────────────────────────────────────────────
    ok = counts["ok"]
    warn = counts["minor_variation"]
    bad = counts["hallucination"]
    checked = ok + warn + bad
    fidelity = round((ok + warn * 0.5) / checked * 100, 1) if checked else 0

    print(f"\n  {'─'*50}")
    print(f"  Resumen:")
    print(f"    ✅ Correctos:          {ok}/{checked}")
    print(f"    ⚠️  Variaciones menores: {warn}/{checked}")
    print(f"    ❌ Alucinaciones:       {bad}/{checked}")
    print(f"    Fidelidad estimada:    {fidelity}%")

    return counts, checked


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print(f"PDF: {PDF_PATH}")
    pdf = fitz.open(str(PDF_PATH))
    print(f"Páginas totales en el PDF: {pdf.page_count}")

    all_counts = {}
    for entry in FILES_TO_CHECK:
        counts, checked = verify_checkpoint(entry, pdf)
        all_counts[entry["label"]] = (counts, checked)

    print(f"\n{'='*70}")
    print("  RESUMEN GLOBAL")
    print(f"{'='*70}")
    total_ok = total_warn = total_bad = total_checked = 0
    for label, (counts, checked) in all_counts.items():
        ok = counts["ok"]
        warn = counts["minor_variation"]
        bad = counts["hallucination"]
        fidelity = round((ok + warn * 0.5) / checked * 100, 1) if checked else 0
        print(f"  {label:<40} ✅{ok} ⚠️ {warn} ❌{bad}  →  {fidelity}%")
        total_ok += ok
        total_warn += warn
        total_bad += bad
        total_checked += checked

    global_fidelity = round((total_ok + total_warn * 0.5) / total_checked * 100, 1) if total_checked else 0
    print(f"\n  Total: ✅{total_ok} ⚠️ {total_warn} ❌{total_bad}  →  Fidelidad global: {global_fidelity}%")


if __name__ == "__main__":
    main()
