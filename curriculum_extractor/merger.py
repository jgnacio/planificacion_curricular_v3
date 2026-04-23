"""
merger.py — Main orchestrator. Reads config, finds sections, extracts tables,
runs ADK agent per materia, and builds CurriculumOutput compatible with teacher_agent.
"""

import json
import yaml
from pathlib import Path

from .section_finder import find_sections, PageRange
from .pdf_reader import extract_tables
from .mcn_extractor import extract_mcn_competencias
from .schemas import CurriculumOutput, TramoJSON, EspacioJSON, MateriaJSON
from .agent import run_extraction


# Maps extractor materia keys → JSON output materia keys (used in curriculum_structure.json)
_MATERIA_KEY_ALIASES: dict[str, str] = {
    "ciencias_ambiente": "ciencias_del_ambiente",
    "ciencias_tierra": "ciencias_de_la_tierra",
    "lenguas_extranjeras": "segundas_lenguas",
    "computacion": "ciencias_computacion",
}

# Maps extractor materia keys → espacio key
_MATERIA_TO_ESPACIO: dict[str, str] = {
    "matematica":           "espacio_cientifico_matematico",
    "fisica_quimica":       "espacio_cientifico_matematico",
    "ciencias_ambiente":    "espacio_cientifico_matematico",
    "ciencias_tierra":      "espacio_cientifico_matematico",
    "lengua_espanola":      "espacio_comunicacion",
    "lenguas_extranjeras":  "espacio_comunicacion",
    "literatura":           "espacio_creativo_artistico",
    "historia":             "espacio_ciencias_sociales",
    "formacion_ciudadania": "espacio_ciencias_sociales",
    "geografia":            "espacio_ciencias_sociales",
    "artes_visuales":       "espacio_creativo_artistico",
    "musica":               "espacio_creativo_artistico",
    "teatro":               "espacio_creativo_artistico",
    "danza":                "espacio_creativo_artistico",
    "conciencia_corporal":  "espacio_creativo_artistico",
    "educacion_fisica":     "espacio_desarrollo_personal",
    "computacion":          "espacio_tecnico_tecnologico",
}

_ESPACIO_NOMBRES: dict[str, str] = {
    "espacio_cientifico_matematico":  "Espacio Científico-Matemático",
    "espacio_comunicacion":           "Espacio de Comunicación",
    "espacio_ciencias_sociales":      "Espacio Ciencias Sociales y Humanidades",
    "espacio_creativo_artistico":     "Espacio Creativo-Artístico",
    "espacio_desarrollo_personal":    "Espacio de Desarrollo Personal y Conciencia Corporal",
    "espacio_tecnico_tecnologico":    "Espacio Técnico-Tecnológico",
}


def _load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_pdf_path(config: dict, ciclo_key: str, base_dir: str) -> str:
    relative = config["pdfs"][ciclo_key]
    return str(Path(base_dir) / relative)


def _materia_key_to_nombre(key: str) -> str:
    mapping = {
        "matematica": "Matemática",
        "lengua_espanola": "Lengua Española",
        "lenguas_extranjeras": "Lenguas Extranjeras",
        "historia": "Historia",
        "geografia": "Geografía",
        "formacion_ciudadania": "Formación para la Ciudadanía",
        "fisica_quimica": "Física y Química",
        "ciencias_ambiente": "Ciencias del Ambiente",
        "ciencias_tierra": "Ciencias de la Tierra",
        "artes_visuales": "Artes Visuales",
        "musica": "Música",
        "literatura": "Literatura",
        "teatro": "Teatro",
        "danza": "Danza",
        "conciencia_corporal": "Conciencia Corporal",
        "educacion_fisica": "Educación Física",
        "computacion": "Computación",
    }
    return mapping.get(key, key.replace("_", " ").title())


def build_curriculum(
    config_path: str,
    tramos_filter: list[str] | None = None,
) -> CurriculumOutput:
    """
    Main orchestrator. Reads config, finds sections, extracts tables,
    runs ADK agent per materia, builds CurriculumOutput compatible with teacher_agent.
    """
    config = _load_config(config_path)
    base_dir = str(Path(config_path).parent.parent)  # repo root

    all_tramos = config.get("tramos", {})
    if tramos_filter:
        tramos_to_process = {k: v for k, v in all_tramos.items() if k in tramos_filter}
    else:
        tramos_to_process = all_tramos

    materias_list: list[str] = config.get("materias", [])

    # Extract MCN competencies from ciclo1 PDF
    ciclo1_path = _resolve_pdf_path(config, "ciclo1", base_dir)
    print(f"[merger] Extracting MCN competencies from {ciclo1_path}")
    mcn_raw = extract_mcn_competencias(ciclo1_path)

    # Pre-build section maps per ciclo
    print("[merger] Building section maps...")
    section_maps: dict[str, dict[str, dict]] = {}
    for ciclo_key in ("ciclo1", "ciclo2"):
        pdf_path = _resolve_pdf_path(config, ciclo_key, base_dir)
        print(f"[merger] Finding sections in {pdf_path}")
        section_maps[ciclo_key] = find_sections(pdf_path)

    tramos_output: dict[str, TramoJSON] = {}

    for tramo_key, tramo_cfg in tramos_to_process.items():
        label = tramo_cfg["label"]
        ciclo_key = tramo_cfg["ciclo"]
        grados: list[str] = tramo_cfg.get("grados", [])
        pdf_path = _resolve_pdf_path(config, ciclo_key, base_dir)

        all_sections = section_maps[ciclo_key]
        sections = all_sections.get(tramo_key, {})
        if not sections:
            print(f"[merger] No sections found for {tramo_key} in {ciclo_key}, skipping.")
            continue

        print(f"\n[merger] Processing {tramo_key}: {label} ({len(sections)} sections found)")

        # Build nested espacios dict: {espacio_key: {nombre, materias: {}}}
        espacios_build: dict[str, dict] = {}

        for materia_key in materias_list:
            if materia_key not in sections:
                print(f"[merger]   Section not found for {materia_key}, skipping.")
                continue

            print(f"[merger]   Extracting {materia_key}...")
            page_range: PageRange = sections[materia_key]

            tables = extract_tables(pdf_path, page_range.start, page_range.end)
            print(f"[merger]   Found {len(tables)} tables in pages "
                  f"{page_range.start}-{page_range.end}")

            if not tables:
                print(f"[merger]   No tables found for {materia_key}, skipping.")
                continue

            materia_output = run_extraction(tables, materia_key, config)

            # Distribute flat contenidos/criterios to all grade keys
            contenidos_by_grade: dict[str, list[str]] = {
                g: materia_output.contenidos for g in grados
            } if grados else {"all": materia_output.contenidos}

            criterios_by_grade: dict[str, list[str]] = {
                g: materia_output.criterios for g in grados
            } if grados else {"all": materia_output.criterios}

            # Build CE dicts
            ces_dicts = [ce.model_dump() for ce in materia_output.competencias_especificas]

            # Determine espacio key and output materia key
            espacio_key = _MATERIA_TO_ESPACIO.get(materia_key, "espacio_otro")
            output_materia_key = _MATERIA_KEY_ALIASES.get(materia_key, materia_key)

            # Initialize espacio entry if needed
            if espacio_key not in espacios_build:
                espacios_build[espacio_key] = {
                    "nombre": _ESPACIO_NOMBRES.get(espacio_key, espacio_key),
                    "materias": {},
                }

            espacios_build[espacio_key]["materias"][output_materia_key] = MateriaJSON(
                nombre=_materia_key_to_nombre(materia_key),
                competencias_especificas=ces_dicts,
                contenidos=contenidos_by_grade,
                criterios=criterios_by_grade,
            )

            print(f"[merger]   Done: {len(ces_dicts)} CEs, "
                  f"{len(materia_output.contenidos)} contenidos, "
                  f"{len(materia_output.criterios)} criterios "
                  f"[patron: {materia_output.patron_detectado}]")

        # Convert to EspacioJSON objects
        espacios_json: dict[str, EspacioJSON] = {
            esp_key: EspacioJSON(
                nombre=esp_data["nombre"],
                materias=esp_data["materias"],
            )
            for esp_key, esp_data in espacios_build.items()
        }

        tramos_output[tramo_key] = TramoJSON(label=label, espacios=espacios_json)

    metadata = {
        "version": "1.0",
        "source": "ANEP/EBI Curriculum PDFs 2024",
        "competencias_mcn": mcn_raw,
        "tramos_procesados": list(tramos_output.keys()),
    }

    print(f"\n[merger] Build complete. "
          f"{len(tramos_output)} tramos, "
          f"{sum(len(t.espacios) for t in tramos_output.values())} espacios.")

    return CurriculumOutput(metadata=metadata, tramos=tramos_output)


def write_output(curriculum: CurriculumOutput, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(curriculum.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"[merger] Written to {output_path}")
