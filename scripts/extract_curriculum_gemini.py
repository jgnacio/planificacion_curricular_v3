"""
Extractor de currículo EBI/ANEP usando Gemini 3.1 Pro en Vertex AI.

Arquitectura:
1. Parsea el TOC del PDF para obtener rangos de páginas exactos por unidad/tramo.
2. Extrae SOLO las páginas del tramo para cada unidad (5-20 págs por llamada).
3. Agrupa los resultados por espacio y genera el JSON final.

Uso:
    python scripts/extract_curriculum_gemini.py
    python scripts/extract_curriculum_gemini.py --tramo "Tramo 4"
    python scripts/extract_curriculum_gemini.py --ciclo "2do Ciclo" --tramo "Tramo 4"
"""

import os
import re
import json
import time
import argparse
from pathlib import Path
from dataclasses import dataclass, field
import fitz  # PyMuPDF
from google import genai
from google.genai import types

# ── Configuración ─────────────────────────────────────────────────────────────

MODEL      = "gemini-3.1-pro-preview"
OUTPUT_DIR = Path("data")
API_KEY    = os.environ.get("GOOGLE_CLOUD_API_KEY")

PDFS = {
    "1er Ciclo": "pdfs/Compilación Programas 1er Ciclo - 2024.pdf",
    "2do Ciclo": "pdfs/Compilación Programas 2do Ciclo.pdf",
}

TRAMOS = {
    "1er Ciclo": {
        "Tramo 1": ["3 años", "4 años", "5 años"],
        "Tramo 2": ["1°", "2°"],
    },
    "2do Ciclo": {
        "Tramo 3": ["3°", "4°"],
        "Tramo 4": ["5°", "6°"],
    },
}

# Variantes de cómo aparece "Tramo N" en el TOC
TRAMO_PATTERNS = {
    "Tramo 1": re.compile(r"tramo\s*1", re.I),
    "Tramo 2": re.compile(r"tramo\s*2", re.I),
    "Tramo 3": re.compile(r"tramo\s*3", re.I),
    "Tramo 4": re.compile(r"tramo\s*4", re.I),
}

# ── Modelos de datos ───────────────────────────────────────────────────────────

@dataclass
class TramoRange:
    start: int   # 0-based
    end:   int   # 0-based, inclusive

@dataclass
class UnidadEntry:
    nombre:  str
    espacio: str
    tramos:  dict = field(default_factory=dict)   # "Tramo N" -> TramoRange


# ── Parseo del TOC ────────────────────────────────────────────────────────────

def _is_espacio(title: str) -> bool:
    return title.lower().startswith("espacio ")

def _is_tramo(title: str) -> bool:
    return bool(re.search(r"tramo\s*\d", title, re.I))

def _is_skip(title: str) -> bool:
    skip = ["referencias", "anexo", "perfiles de tramo", "guía de orientación",
            "contenido", "perfil de egreso"]
    tl = title.lower()
    return any(s in tl for s in skip)


def parse_toc(pdf_path: Path) -> list[UnidadEntry]:
    """
    Lee las primeras páginas del PDF buscando el TOC y construye la lista
    de UnidadEntry con rangos de páginas por tramo.
    """
    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    # Leer las primeras 10 páginas buscando el TOC (suele estar al inicio)
    toc_text = ""
    for i in range(min(10, total_pages)):
        toc_text += doc[i].get_text() + "\n"

    # Extraer entradas con número de página
    pattern = re.compile(r'^(.+?)\.{2,}\s*(\d+)\s*$', re.MULTILINE)
    raw_entries = []
    for m in pattern.finditer(toc_text):
        title = m.group(1).strip().rstrip('.')
        page  = int(m.group(2))
        if not title:
            continue
        raw_entries.append((title, page))

    if not raw_entries:
        print(f"  ⚠️  No se encontró TOC en {pdf_path.name}")
        return []

    # Calcular end_page de cada entrada como start del siguiente - 1
    entries_with_end = []
    for i, (title, start) in enumerate(raw_entries):
        end = raw_entries[i+1][1] - 1 if i + 1 < len(raw_entries) else total_pages - 1
        entries_with_end.append((title, start - 1, end - 1))  # convertir a 0-based

    # Construir UnidadEntry agrupando por espacio
    unidades: list[UnidadEntry] = []
    current_espacio = None
    current_unidad: UnidadEntry | None = None

    for title, start, end in entries_with_end:
        if _is_skip(title):
            current_unidad = None
            continue

        if _is_espacio(title):
            current_espacio = title
            current_unidad = None
            continue

        if _is_tramo(title):
            if current_unidad is None:
                continue
            for tramo_key, pattern in TRAMO_PATTERNS.items():
                if pattern.search(title):
                    current_unidad.tramos[tramo_key] = TramoRange(start=start, end=end)
                    break
            continue

        # Es una unidad curricular
        if current_espacio is None:
            continue
        current_unidad = UnidadEntry(nombre=title, espacio=current_espacio)
        unidades.append(current_unidad)

    return unidades


# ── Utilidades PDF ────────────────────────────────────────────────────────────

def slice_pdf(pdf_path: Path, start: int, end: int) -> bytes:
    """Extrae páginas [start, end] (0-based) y devuelve bytes."""
    src = fitz.open(str(pdf_path))
    dst = fitz.open()
    dst.insert_pdf(src, from_page=start, to_page=end)
    data = dst.tobytes()
    src.close()
    dst.close()
    return data


# ── Prompt ────────────────────────────────────────────────────────────────────

def build_unidad_prompt(ciclo: str, tramo: str, grados: list[str],
                         espacio: str, unidad: str) -> str:
    grados_str = " y ".join(grados)
    return f"""Sos un extractor de datos. Tu única tarea es transcribir fielmente el contenido de este PDF a JSON.

CONTEXTO: Este PDF contiene las páginas del programa EBI/ANEP Uruguay para:
Ciclo: {ciclo} | Tramo: {tramo} | Grados: {grados_str}
Espacio: {espacio} | Unidad Curricular: {unidad}

═══════════════════════════════════════
REGLA ABSOLUTA — ANTI-ALUCINACIÓN
═══════════════════════════════════════
SOLO podés incluir texto que esté literalmente en el PDF.
Si no encontrás un dato → array vacío [].
Si no podés leer una celda → string vacío "".
NUNCA completes, inferías ni inventes datos faltantes.
Antes de escribir cada campo, verificá que podés señalar exactamente dónde está en el PDF.

═══════════════════════════════════════
CÓMO LEER EL DOCUMENTO
═══════════════════════════════════════

PASO 1 — Encontrá las COMPETENCIAS ESPECÍFICAS (CE1, CE2...CE10):
Son párrafos numerados que aparecen ANTES de las tablas.
Cada uno tiene: código (CE1), descripción larga, y lista de competencias generales MCN.
Copiá el texto COMPLETO de cada CE, sin resumir.

PASO 2 — Identificá el FORMATO de la tabla (mirá los encabezados de columna):
• Formato A: "Contenidos" | "CE" → los códigos CE van en competencias_relacionadas
• Formato B: "Competencias Específicas" | "Contenidos" | "Criterios de logro"
• Formato C: igual que B pero cada criterio termina con el código: (CE1), (CE2)
• Formato D: "Contenidos específicos" | "Contenidos para la profundización..." → DOS columnas de contenido

PASO 3 — Encontrá los EJES (subtítulos dentro de la tabla que agrupan contenidos):
Son filas o celdas que contienen solo un título: "NUMERACIÓN NATURAL", "ORALIDAD", "GEOMETRÍA".
IMPORTANTE: algunos ejes están escritos en VERTICAL (letras apiladas). Reconstruilos como palabra completa.
Si no hay ejes visibles, usá un único eje con nombre "General".

PASO 4 — CELDAS FUSIONADAS:
Si una celda de CE (ej: "CE1, CE2, CE7") abarca múltiples filas de contenidos,
copiá esos códigos en TODOS los contenidos que cubre esa celda.

PASO 5 — GRADOS ESPECÍFICOS:
Si hay tablas separadas para cada grado (ej: "5.to grado"), indicá el grado.
Si aplica a todos los grados del tramo, ponelos todos: {json.dumps(grados, ensure_ascii=False)}.

PASO 6 — COLUMNAS DE PROFUNDIZACIÓN (Formato D):
Si la tabla tiene una columna separada llamada "Profundización", "Contenidos para la profundización"
o similar, NO la concatenes con el contenido principal.
Creá una entrada SEPARADA con tipo="profundizacion" para cada celda de esa columna,
en el mismo eje que el contenido principal al que corresponde.

PASO 7 — CRITERIOS DE LOGRO (siempre a nivel de unidad, nunca dentro de contenidos):
Los criterios de logro van en el campo `criterios_de_logro` de la UNIDAD CURRICULAR, no dentro de cada contenido.
Pueden aparecer en el PDF de dos formas:
  a) Dentro de la misma tabla de contenidos (una columna "Criterios de logro")
  b) En una tabla separada después de la tabla de contenidos

En ambos casos, extraelos y ponelos en la lista `criterios_de_logro` de la unidad.
Cada criterio tiene: descripcion (texto literal), ce_evaluada (código CE si está indicado), grado (si aplica).
Si un criterio tiene múltiples ítems con bullets (•), creá una entrada por ítem.
NUNCA crees un pseudo-contenido con nombre "Criterios de logro de X grado".

PASO 8 — CONCEPTOS CLAVE:
Si hay una fila final con términos sueltos (ej: "caudillismo, emancipación..."),
creá un contenido con tipo="conceptos_clave" y competencias_relacionadas=[].

═══════════════════════════════════════
JSON DE SALIDA — schema exacto
═══════════════════════════════════════

{{
  "nombre": "{unidad}",
  "competencias_especificas": [
    {{
      "codigo": "CE1",
      "descripcion": "Texto literal completo de la CE tal como aparece en el PDF.",
      "contribuye_a_mcn": ["Nombre competencia MCN 1", "Nombre competencia MCN 2"]
    }}
  ],
  "criterios_de_logro": [
    {{
      "descripcion": "Texto literal del criterio de logro.",
      "ce_evaluada": "CE1",
      "grado": ["5°"]
    }}
  ],
  "ejes": [
    {{
      "nombre": "NOMBRE DEL EJE EN MAYÚSCULAS",
      "contenidos": [
        {{
          "descripcion": "Texto literal del contenido.",
          "tipo": "contenido | profundizacion | conceptos_clave",
          "grado": {json.dumps(grados, ensure_ascii=False)},
          "competencias_relacionadas": ["CE1", "CE2"]
        }}
      ]
    }}
  ]
}}

Devolvé SOLO el JSON. Sin texto antes ni después. Sin bloques de código markdown.
Si no encontrás datos para algún campo, usá [] — nunca inventes."""


# ── Extracción ────────────────────────────────────────────────────────────────

def _call_model(client: genai.Client, pdf_bytes: bytes, prompt: str) -> tuple[str, str]:
    for attempt in range(4):
        try:
            return _call_model_once(client, pdf_bytes, prompt)
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                wait = 30 * (attempt + 1)
                print(f"      ⏳ Rate limit — esperando {wait}s (intento {attempt+1}/4)...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("No debería llegar aquí")


def _call_model_once(client: genai.Client, pdf_bytes: bytes, prompt: str) -> tuple[str, str]:
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    types.Part(text=prompt),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
            max_output_tokens=65536,
        ),
    )
    candidate  = response.candidates[0] if response.candidates else None
    finish_reason = str(candidate.finish_reason) if candidate else "unknown"
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip(), finish_reason


def _parse_json(raw: str, label: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        slug = re.sub(r'[^a-z0-9]+', '_', label.lower())
        debug_path = OUTPUT_DIR / f"debug_{slug}_raw.txt"
        debug_path.write_text(raw, encoding="utf-8")
        print(f"      ❌ JSON inválido en char {e.pos} — guardado en {debug_path}")
        print(f"      ❌ Contexto: ...{raw[max(0,e.pos-60):e.pos+60]}...")
        raise


def extract_unidad(
    client: genai.Client,
    pdf_path: Path,
    ciclo: str,
    tramo_nombre: str,
    grados: list[str],
    unidad: UnidadEntry,
    tramo_range: TramoRange,
) -> dict:
    pdf_bytes = slice_pdf(pdf_path, tramo_range.start, tramo_range.end)
    n_pages = tramo_range.end - tramo_range.start + 1
    print(f"      📄 Páginas {tramo_range.start+1}–{tramo_range.end+1} ({n_pages} págs, {len(pdf_bytes)//1024} KB)")

    prompt = build_unidad_prompt(ciclo, tramo_nombre, grados, unidad.espacio, unidad.nombre)
    raw, finish_reason = _call_model(client, pdf_bytes, prompt)

    status = "⚠️  TRUNCADO" if "MAX_TOKENS" in finish_reason else "✅"
    print(f"      📥 {len(raw):,} chars | {finish_reason} {status}")

    parsed = _parse_json(raw, f"{tramo_nombre}_{unidad.espacio}_{unidad.nombre}")
    # El modelo a veces devuelve [{...}] en lugar de {...}
    if isinstance(parsed, list):
        parsed = parsed[0] if parsed else {}
    return parsed


# ── Main ──────────────────────────────────────────────────────────────────────

def main(only_ciclo: str | None = None, only_tramo: str | None = None):
    OUTPUT_DIR.mkdir(exist_ok=True)

    if API_KEY:
        client = genai.Client(vertexai=True, api_key=API_KEY)
        print(f"Modelo: {MODEL} | Auth: API key\n")
    else:
        raise SystemExit("❌ Falta GOOGLE_CLOUD_API_KEY. Exportá la variable de entorno.")

    results = []
    errors  = []

    for ciclo_nombre, pdf_path_str in PDFS.items():
        if only_ciclo and ciclo_nombre != only_ciclo:
            continue

        pdf_path = Path(pdf_path_str)
        if not pdf_path.exists():
            print(f"❌ No existe {pdf_path}")
            continue

        print(f"📄 {pdf_path.name} ({pdf_path.stat().st_size // 1024 // 1024} MB)")
        print(f"   Parseando TOC...")
        unidades = parse_toc(pdf_path)
        print(f"   {len(unidades)} unidades curriculares encontradas en el TOC\n")

        for tramo_nombre, grados in TRAMOS[ciclo_nombre].items():
            if only_tramo and tramo_nombre != only_tramo:
                continue

            # Filtrar unidades que tienen datos para este tramo
            unidades_del_tramo = [u for u in unidades if tramo_nombre in u.tramos]
            if not unidades_del_tramo:
                print(f"  ⚠️  No hay unidades con páginas para {tramo_nombre}")
                continue

            print(f"  📚 {ciclo_nombre} — {tramo_nombre} ({', '.join(grados)})")
            print(f"     {len(unidades_del_tramo)} unidades a extraer\n")

            # Agrupar unidades por espacio para el JSON final
            espacios_dict: dict[str, list[dict]] = {}
            errores_tramo = []

            # Cargar checkpoints previos (permite retomar si se interrumpió)
            checkpoint_dir = OUTPUT_DIR / "checkpoints"
            checkpoint_dir.mkdir(exist_ok=True)

            def checkpoint_path(u: UnidadEntry) -> Path:
                slug = re.sub(r'[^a-z0-9]+', '_', f"{tramo_nombre}_{u.espacio}_{u.nombre}".lower())
                return checkpoint_dir / f"{slug}.json"

            for i, unidad in enumerate(unidades_del_tramo, 1):
                tramo_range = unidad.tramos[tramo_nombre]
                label = f"[{i}/{len(unidades_del_tramo)}] {unidad.espacio} → {unidad.nombre}"
                cp = checkpoint_path(unidad)

                # Retomar desde checkpoint si existe
                if cp.exists():
                    unidad_data = json.loads(cp.read_text(encoding="utf-8"))
                    espacios_dict.setdefault(unidad.espacio, []).append(unidad_data)
                    print(f"    ⏩ {label} (desde checkpoint)")
                    continue

                print(f"    📤 {label}")
                try:
                    unidad_data = extract_unidad(
                        client, pdf_path, ciclo_nombre, tramo_nombre,
                        grados, unidad, tramo_range,
                    )
                    espacios_dict.setdefault(unidad.espacio, []).append(unidad_data)
                    # Guardar checkpoint inmediatamente
                    cp.write_text(json.dumps(unidad_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"      ✅ {len(unidad_data.get('ejes', []))} ejes | checkpoint guardado")

                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    errores_tramo.append({"unidad": unidad.nombre, "error": str(e)})

                if i < len(unidades_del_tramo):
                    time.sleep(2)

            # Armar el JSON del tramo
            tramo_data = {
                "ciclo": ciclo_nombre,
                "tramo": tramo_nombre,
                "grados": grados,
                "espacios": [
                    {"nombre": esp, "unidades_curriculares": ucs}
                    for esp, ucs in espacios_dict.items()
                ],
            }
            results.append(tramo_data)

            partial_path = OUTPUT_DIR / f"curriculum_{tramo_nombre.lower().replace(' ', '_')}.json"
            partial_path.write_text(json.dumps(tramo_data, ensure_ascii=False, indent=2), encoding="utf-8")

            n_ok  = len(unidades_del_tramo) - len(errores_tramo)
            n_err = len(errores_tramo)
            print(f"\n  ✅ {tramo_nombre} → {partial_path}")
            print(f"     {n_ok} unidades OK | {n_err} errores\n")

            if errores_tramo:
                errors.extend(errores_tramo)

    # JSON final consolidado
    if results:
        final_path = OUTPUT_DIR / "curriculum_extracted.json"
        final_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ JSON consolidado → {final_path}")
        print(f"   Tramos: {len(results)}")

    if errors:
        print(f"\n⚠️  Errores ({len(errors)}):")
        for e in errors:
            print(f"   {e['unidad']}: {e['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extraer currículo EBI/ANEP con Gemini")
    parser.add_argument("--ciclo", help="Procesar solo este ciclo (ej: '2do Ciclo')")
    parser.add_argument("--tramo", help="Procesar solo este tramo (ej: 'Tramo 4')")
    args = parser.parse_args()
    main(only_ciclo=args.ciclo, only_tramo=args.tramo)
