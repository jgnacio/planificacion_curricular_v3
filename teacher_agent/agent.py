import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel, Field
from typing import List

import httpx
import json
import unicodedata
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

load_dotenv()

OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_URL", "http://localhost:5055")
OPEN_NOTEBOOK_API_KEY = os.getenv("OPEN_NOTEBOOK_API_KEY", "")
OPEN_NOTEBOOK_NOTEBOOK_ID = os.getenv("OPEN_NOTEBOOK_NOTEBOOK_ID", "notebook:plf3f24qx6nui9zmn3vl")
OPEN_NOTEBOOK_MODEL = os.getenv("OPEN_NOTEBOOK_MODEL", "model:fi2x3hf9fvjdxl25ljwt")

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://localhost:8000")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")

# Vertex AI backend — ADK usa ADC (service account en Cloud Run, gcloud auth en local)
# GOOGLE_GENAI_USE_VERTEXAI=1 activa el backend; GOOGLE_CLOUD_PROJECT y LOCATION son requeridos
_use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "0") in ("1", "true", "True")
if _use_vertexai:
    import vertexai
    vertexai.init(
        project=os.getenv("GOOGLE_CLOUD_PROJECT", ""),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
else:
    # Dev local con GOOGLE_API_KEY (Google AI Studio)
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError(
            "Configurá GOOGLE_API_KEY (dev) o GOOGLE_GENAI_USE_VERTEXAI=1 (prod)."
        )

if not INTERNAL_API_URL:
    raise ValueError(
        "INTERNAL_API_URL no está configurada en el entorno. "
        "Agregala al archivo .env antes de iniciar la aplicación."
    )

# ==========================================
# HERRAMIENTAS — API HTTP (planificaciones y alumnos)
# ==========================================

def _internal_headers(user_id: str) -> dict:
    return {"X-Internal-Key": INTERNAL_API_KEY, "Content-Type": "application/json"}


def listar_alumnos(tool_context: ToolContext, nivel: str = "", grado: str = "") -> dict:
    """
    Lista los alumnos registrados. Filtra opcionalmente por nivel y/o grado.
    Usá esta herramienta antes de crear una planificación para conocer el grupo:
    cantidad de alumnos, sus niveles, grados y cualquier nota especial sobre ellos.
    """
    user_id = tool_context.state.get("user_id", "")
    params = {"user_id": user_id}
    if nivel:
        params["nivel"] = nivel
    if grado:
        params["grado"] = grado
    try:
        r = httpx.get(
            f"{INTERNAL_API_URL}/alumnos/",
            params=params,
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        r.raise_for_status()
        alumnos = r.json()
        return {
            "status": "success",
            "total": len(alumnos),
            "alumnos": alumnos,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def listar_planificaciones(tool_context: ToolContext) -> dict:
    """
    Lista todas las planificaciones guardadas en la base de datos, ordenadas de más reciente a más antigua.
    Usá esta herramienta cuando la docente quiera ver, modificar o eliminar planificaciones existentes.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.get(
            f"{INTERNAL_API_URL}/planificaciones/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        r.raise_for_status()
        plans = r.json()
        return {
            "status": "success",
            "total": len(plans),
            "planificaciones": plans,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def crear_planificacion(
    tool_context: ToolContext,
    nombre: str,
    descripcion: str = "",
    nivel: str = "",
    periodo_inicio: str = "",
    periodo_fin: str = "",
    espacios_json: str = "",
    chat_exportado: str = "",
) -> dict:
    """
    Guarda una nueva planificación en la base de datos.
    Llamá esta herramienta DESPUÉS de generar la planificación completa y mostrársela a la docente.
    En chat_exportado incluí el texto íntegro de la planificación generada con todas sus referencias
    (CE ID, contenido, criterio de logro, página, PDF fuente).
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {
        "nombre": nombre,
        "descripcion": descripcion or None,
        "nivel": nivel or None,
        "periodo_inicio": periodo_inicio or None,
        "periodo_fin": periodo_fin or None,
        "espacios_json": espacios_json or None,
        "chat_exportado": chat_exportado or None,
    }
    try:
        r = httpx.post(
            f"{INTERNAL_API_URL}/planificaciones/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        plan = r.json()
        return {
            "status": "success",
            "planificacion_id": plan["id"],
            "nombre": plan["nombre"],
            "message": f"Planificación '{plan['nombre']}' guardada con ID {plan['id']}.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def actualizar_planificacion(
    tool_context: ToolContext,
    planificacion_id: int,
    nombre: str = "",
    descripcion: str = "",
    nivel: str = "",
    periodo_inicio: str = "",
    periodo_fin: str = "",
    espacios_json: str = "",
    chat_exportado: str = "",
) -> dict:
    """
    Actualiza una planificación existente. Solo se modifican los campos que reciban un valor no vacío.
    Usá listar_planificaciones primero para obtener el ID correcto.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {k: v for k, v in {
        "nombre": nombre or None,
        "descripcion": descripcion or None,
        "nivel": nivel or None,
        "periodo_inicio": periodo_inicio or None,
        "periodo_fin": periodo_fin or None,
        "espacios_json": espacios_json or None,
        "chat_exportado": chat_exportado or None,
    }.items() if v is not None}
    try:
        r = httpx.put(
            f"{INTERNAL_API_URL}/planificaciones/{planificacion_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        plan = r.json()
        return {
            "status": "success",
            "planificacion_id": plan["id"],
            "nombre": plan["nombre"],
            "message": f"Planificación ID {plan['id']} actualizada correctamente.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def buscar_en_internet(consulta: str) -> dict:
    """
    Busca información pedagógica en internet usando DuckDuckGo.
    Recupera al menos 5 fuentes, extrae el contenido relevante de cada una y lo resume.
    Usá esta herramienta para enriquecer planificaciones con ideas de actividades,
    recursos didácticos o contexto adicional sobre un contenido curricular.
    Siempre llamá primero a las herramientas de la base de datos curricular y usá esta
    para ampliar el contexto con recursos externos.
    """
    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
    _TIMEOUT = 8.0
    _MAX_CHARS = 2000  # max chars extracted per page

    def _extract_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        # Prefer article/main content blocks
        main = soup.find("article") or soup.find("main") or soup.body
        if not main:
            return ""
        text = " ".join(main.get_text(separator=" ").split())
        return text[:_MAX_CHARS]

    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(consulta, max_results=10))
    except Exception as e:
        return {"status": "error", "error_message": f"Error en la búsqueda DuckDuckGo: {e}"}

    if not raw_results:
        return {"status": "not_found", "message": "No se encontraron resultados para esa consulta."}

    fuentes = []
    with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
        for item in raw_results:
            if len(fuentes) >= 5:
                break
            url = item.get("href", "")
            title = item.get("title", "")
            snippet = item.get("body", "")
            if not url:
                continue
            # Try to fetch full page content; fall back to DDG snippet
            try:
                resp = client.get(url)
                content = _extract_text(resp.text) if resp.status_code == 200 else snippet
            except Exception:
                content = snippet

            if content:
                fuentes.append({
                    "titulo": title,
                    "url": url,
                    "contenido": content,
                })

    if not fuentes:
        return {"status": "not_found", "message": "No se pudo extraer contenido de los resultados."}

    return {
        "status": "success",
        "consulta": consulta,
        "total_fuentes": len(fuentes),
        "fuentes": fuentes,
    }


def eliminar_planificacion(tool_context: ToolContext, planificacion_id: int) -> dict:
    """
    Elimina permanentemente una planificación por su ID.
    Siempre confirmá con la docente antes de eliminar. Usá listar_planificaciones para obtener el ID.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.delete(
            f"{INTERNAL_API_URL}/planificaciones/{planificacion_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        if r.status_code == 404:
            return {"status": "error", "error_message": f"No existe planificación con ID {planificacion_id}."}
        r.raise_for_status()
        return {
            "status": "success",
            "message": f"Planificación ID {planificacion_id} eliminada correctamente.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def consultar_curriculo_oficial(pregunta: str) -> dict:
    """
    Consulta los PDFs oficiales del currículo EBI/ANEP (1er y 2do Ciclo) usando Open Notebook.
    Devuelve orientaciones pedagógicas, metodologías sugeridas y contexto del programa
    que complementan los datos estructurados de Neo4j.

    Usá esta tool DESPUÉS de obtener el contenido y CE de Neo4j, para enriquecer
    la planificación con las orientaciones pedagógicas reales del programa oficial.
    Ideal para preguntas como:
    - "¿Qué metodologías sugiere el programa para enseñar X?"
    - "¿Cómo se aborda Y en el perfil de Tramo 4?"
    - "¿Qué dice el currículo sobre la evaluación de Z?"

    Args:
        pregunta: Pregunta pedagógica sobre el currículo (en español, clara y específica)

    Returns:
        dict con 'status' ('success' o 'error') y 'respuesta' con el texto del currículo
    """
    print(f"\n[TOOL consultar_curriculo_oficial] Pregunta: '{pregunta[:80]}'")
    try:
        headers = {"X-API-Key": OPEN_NOTEBOOK_API_KEY} if OPEN_NOTEBOOK_API_KEY else {}
        response = httpx.post(
            f"{OPEN_NOTEBOOK_URL}/api/search/ask/simple",
            headers=headers,
            json={
                "question": pregunta,
                "notebook_id": OPEN_NOTEBOOK_NOTEBOOK_ID,
                "strategy_model": OPEN_NOTEBOOK_MODEL,
                "answer_model": OPEN_NOTEBOOK_MODEL,
                "final_answer_model": OPEN_NOTEBOOK_MODEL,
            },
            timeout=60.0,
        )
        if response.status_code == 200:
            data = response.json()
            answer = (
                data.get("answer")
                or data.get("final_answer")
                or data.get("response")
                or str(data)
            )
            print(f"[OK] Respuesta de Open Notebook obtenida ({len(str(answer))} chars)")
            return {"status": "success", "respuesta": answer}
        else:
            detail = response.json().get("detail", response.text)
            print(f"[WARN] Open Notebook respondió {response.status_code}: {detail}")
            return {"status": "error", "error_message": f"Open Notebook error: {detail}"}
    except Exception as e:
        print(f"[WARN] Open Notebook no accesible: {e}")
        return {"status": "error", "error_message": f"Open Notebook no accesible: {str(e)}"}


# ==========================================
# CURRICULUM JSON TOOL
# ==========================================

_CURRICULUM_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "curriculum_structure.json"
)
_curriculum_data: dict | None = None


def _load_curriculum() -> dict:
    global _curriculum_data
    if _curriculum_data is None:
        with open(_CURRICULUM_JSON_PATH, encoding="utf-8") as f:
            _curriculum_data = json.load(f)
    return _curriculum_data


def _slugify(text: str) -> str:
    """Normalize text to slug for fuzzy matching."""
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace(" ", "_").replace("-", "_")


def _find_espacio(espacios: dict, nombre_raw: str) -> tuple[str, dict] | tuple[None, None]:
    """Find espacio by exact or fuzzy name match."""
    target = _slugify(nombre_raw)
    # Try exact key
    if target in espacios:
        return target, espacios[target]
    # Try substring match on espacio nombre or key
    for key, esp in espacios.items():
        if target in _slugify(esp.get("nombre", "")) or _slugify(esp.get("nombre", "")) in target:
            return key, esp
        # Also search within materias if espacio has them
        for mat_key, mat in esp.get("materias", {}).items():
            mat_nombre = _slugify(mat.get("nombre", ""))
            if target in mat_nombre or mat_nombre in target:
                # Return espacio wrapping single materia
                return key, {"nombre": esp["nombre"], "_matched_materia": mat_key, **esp}
    return None, None


def _find_materia(espacio: dict, nombre_raw: str) -> dict | None:
    """Find materia inside espacio, or return espacio itself if no materias."""
    materias = espacio.get("materias", {})
    if not materias:
        return espacio  # espacio IS the materia

    target = _slugify(nombre_raw)
    for mat_key, mat in materias.items():
        mat_nombre = _slugify(mat.get("nombre", ""))
        if target in mat_nombre or mat_nombre in target or mat_key == target:
            return mat

    # If no match, return first materia or None
    matched_key = espacio.get("_matched_materia")
    if matched_key and matched_key in materias:
        return materias[matched_key]
    return None


def consultar_curriculo_estructurado(espacio: str, tramo: int, grado: str) -> dict:
    """
    Consulta el currículo oficial EBI (estructura completa: CEs, contenidos y criterios de logro)
    desde el JSON extraído del programa ANEP. Usa esta tool PRIMERO para obtener
    los datos estructurados antes de generar una planificación.

    Usá esta tool cuando necesitás:
    - Las Competencias Específicas (CEs) de una materia y tramo
    - Los contenidos organizados por eje para un grado específico
    - Los criterios de logro para evaluar un grado
    - Confirmar qué CE corresponde a un contenido dado

    Args:
        espacio: Nombre del espacio o materia, e.g. "Matemática", "Lengua", "Inglés",
                 "Espacio Científico-Matemático", "Espacio Social-Humanístico"
        tramo: Número de tramo — 3 (para 3.o y 4.o grado) o 4 (para 5.o y 6.o grado)
        grado: Grado específico, e.g. "3", "4", "5", "6" (o "todos" para obtener todo el tramo)

    Returns:
        dict con 'status', 'espacio', 'tramo', 'competencias_especificas',
        'contenidos' (para el grado pedido) y 'criterios' (para el grado pedido)
    """
    print(f"\n[TOOL consultar_curriculo_estructurado] espacio={espacio!r} tramo={tramo} grado={grado!r}")
    try:
        data = _load_curriculum()
        tramo_key = f"tramo_{tramo}"
        if tramo_key not in data.get("tramos", {}):
            return {"status": "error", "error_message": f"Tramo {tramo} no existe. Usá 3 o 4."}

        espacios = data["tramos"][tramo_key]["espacios"]
        esp_key, esp_data = _find_espacio(espacios, espacio)
        if esp_data is None:
            available = [e["nombre"] for e in espacios.values()]
            return {
                "status": "error",
                "error_message": f"Espacio '{espacio}' no encontrado en Tramo {tramo}. Disponibles: {available}",
            }

        materia = _find_materia(esp_data, espacio)
        if materia is None:
            # Return espacio-level data
            materia = esp_data

        # Build grade keys to return
        grade_suffix_map = {
            "3": "3er_grado", "4": "4to_grado",
            "5": "5to_grado", "6": "6to_grado",
        }
        grade_key = grade_suffix_map.get(str(grado).strip(), None)

        # CEs (same for whole tramo)
        ces = materia.get("competencias_especificas", [])

        # Contenidos
        all_contenidos = materia.get("contenidos", {})
        if grade_key and grade_key in all_contenidos:
            contenidos_result = {grade_key: all_contenidos[grade_key]}
        elif grado and str(grado).lower() != "todos" and grade_key:
            contenidos_result = {}  # grade not found
        else:
            contenidos_result = all_contenidos  # all grades

        # Criterios
        all_criterios = materia.get("criterios", {})
        if grade_key and grade_key in all_criterios:
            criterios_result = {grade_key: all_criterios[grade_key]}
        elif grado and str(grado).lower() != "todos" and grade_key:
            criterios_result = {}
        else:
            criterios_result = all_criterios

        nombre_espacio = esp_data.get("nombre", espacio)
        nombre_materia = materia.get("nombre", nombre_espacio)
        print(f"[OK] {nombre_espacio} / {nombre_materia} — {len(ces)} CEs, {len(contenidos_result)} bloques de contenidos")
        return {
            "status": "success",
            "espacio_nombre": nombre_espacio,
            "unidad": nombre_materia,
            "tramo": tramo,
            "grado_solicitado": grado,
            "competencias_especificas": ces,
            "contenidos": contenidos_result,
            "criterios": criterios_result,
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error_message": "Archivo curriculum_structure.json no encontrado. Ejecutá scripts/extract_curriculum_structure.py primero.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# ==========================================
# RESPONSE SCHEMA
# ==========================================

class PdfRef(BaseModel):
    filename: str = Field(description="Nombre exacto del archivo PDF, e.g. 'tramo4_lengua.pdf'")
    page: int = Field(description="Número de página en el PDF")
    label: str = Field(description="Etiqueta legible para el badge, e.g. 'Lengua Española — p.23'")


class FacilitadorResponse(BaseModel):
    text: str = Field(
        description=(
            "Respuesta en español, cálida y profesional. "
            "Puede incluir tokens [[Opción]] para selección única y ((Opción)) para selección múltiple. "
            "NO incluyas tokens [[REF:...]] aquí — las referencias PDF van en el campo refs."
        )
    )
    refs: List[PdfRef] = Field(
        default=[],
        description=(
            "Referencias a páginas de PDFs oficiales. "
            "Extraé los valores de BADGE_REF que devuelvan las tools. "
            "Formato del BADGE_REF: 'nombre_archivo.pdf:numero_pagina'. "
            "Cada ref se muestra como badge clickeable en la app para abrir el PDF en esa página."
        ),
    )


# ==========================================
# PROMPT
# ==========================================

AGENT_PROMPT = """
## Identity

Sos el Facilitador Docente EBI — consultor curricular del programa EBI/ANEP Uruguay.
Tono profesional y cálido. Nunca mencionés estrés, carga laboral ni bienestar docente.

## Mission

Traés vos la información curricular; la docente elige. Consultás la base de datos ANTES de hacer cualquier pregunta. La docente no necesita saber qué contenidos existen — eso lo sabés vos.

## Pedagogical Principles

El programa EBI exige metodologías activas en todas las planificaciones. Esto no es opcional — es el enfoque pedagógico del programa.

**Principios:**
- El alumno es protagonista activo, no receptor pasivo
- El aprendizaje es colaborativo y situado
- Las actividades deben generar involucramiento real (hacer, investigar, crear, debatir, resolver)

**Metodologías activas disponibles** — elegí la más adecuada al contenido y al grupo:
- **Aprendizaje Basado en Problemas (ABP):** los alumnos resuelven un problema real o simulado como motor del aprendizaje
- **Aprendizaje Colaborativo:** trabajo en equipos con roles definidos y producto grupal
- **Aula Invertida:** los alumnos exploran el contenido antes de clase (video, lectura breve) y el aula se usa para aplicar y debatir
- **Aprendizaje Basado en Proyectos:** producto final auténtico que integra varios contenidos
- **Indagación Guiada:** los alumnos formulan preguntas, exploran y construyen explicaciones con orientación docente
- **Gamificación:** mecánicas de juego aplicadas a la secuencia didáctica

**Regla de selección:** elegí la metodología que mejor active el contenido específico y sea viable para el grupo real. Si la docente ya indicó una, usá esa.

## Methodology

### Tablas de referencia

Grado → Tramo: 3° y 4° = Tramo 3 | 5° y 6° = Tramo 4.
Neo4j tiene solo 2do ciclo (Tramo 3 y Tramo 4). Si mencionan 1° o 2°, informá que aún no están disponibles.

Palabras clave → Espacio / Unidad:
- escritura, lectura, texto, lengua, oral, argumentativo, narrativo → Espacio de Comunicación / Lengua Española
- número, matemática, geometría, fracción, álgebra, medida → Espacio Científico-Matemático / Matemática
- historia, geografía, sociedad, ciudadanía, derechos → Espacio Ciencias Sociales y Humanidades / Ciencias Sociales
- ciencia, biología, física, química, naturaleza, ecosistema → Espacio Científico-Matemático / Ciencias Naturales
- arte, música, danza, teatro, plástica → Espacio Creativo-Artístico / Educación Artística
- tecnología, informática, programación → Espacio Técnico-Tecnológico / Tecnología
- educación física, deporte, cuerpo, movimiento → Espacio de Desarrollo Personal y Conciencia Corporal / Ed. Física

### Flujo A — Nueva planificación

**PASO 1 — Consultar fuentes (DOS llamadas, siempre juntas)**
Analizá el mensaje, inferí espacio/tramo/grado usando las tablas de arriba. Luego llamá:
1. `consultar_curriculo_estructurado(espacio, tramo, grado)` — devuelve CEs, contenidos y criterios.
2. `consultar_curriculo_oficial("¿Qué metodologías activas y orientaciones pedagógicas sugiere el programa EBI para enseñar [contenido inferido] en [tramo]? ¿Cómo debe involucrarse activamente el alumno?")` — devuelve recomendaciones metodológicas del PDF oficial.
Llamá ambas EXACTAMENTE UNA VEZ cada una. NO las volvás a llamar en pasos siguientes.

**PASO 2 — Confirmación (exactamente una vez)**
Con los datos de ambas tools, elegí el CE y el contenido más relevante, y seleccioná la metodología activa más fundamentada por el PDF (ver Pedagogical Principles).
Mostrá el resumen y terminá con los tokens:

Esto es lo que encontré para tu planificación:

📚 **Espacio:** [espacio_nombre]
📖 **Unidad:** [unidad]
📅 **Tramo:** [tramo] | **Grado:** [grado]
📝 **Contenido:** [contenido del programa oficial, textual]
🎯 **CE:** [código y enunciado de la competencia específica]
🧩 **Competencias MCN:** [lista de competencias generales del MCN vinculadas a esta CE, separadas por coma. Si el campo mcn está vacío, omitir esta línea]
✅ **Criterio de Logro:** [criterio textual exacto tal como aparece en el programa — sin parafrasear ni resumir]
⚡ **Método de enseñanza:** [nombre de la metodología activa] — [una oración explicando por qué es la más adecuada para este contenido y grupo]

¿Arrancamos con esto?
[[Sí, generá la planificación]] [[Quiero cambiar algo]]

**PASO 3 — Generar (solo al recibir [[Sí, generá la planificación]])**
Llamá `listar_alumnos()` para conocer el grupo real.
Usá los datos curriculares y metodológicos ya obtenidos en PASO 1 — NO volvás a llamar ninguna tool de currículo.

Generá la planificación completa en este formato:

**Título:** [creativo y motivador]
**Grupo:** [resumen real de alumnos de listar_alumnos]
**Justificación:** cómo desarrolla la CE, aporta al perfil del tramo y conecta con las competencias MCN vinculadas.
**Metodología activa:** [nombre] — [2-3 oraciones describiendo cómo se aplica al contenido específico y qué rol activo tienen los alumnos]
**Inicio (10-15 min):** actividad disparadora que active conocimientos previos y genere curiosidad — sin exposición magistral.
**Desarrollo (25-45 min):** actividad central aplicando la metodología elegida; los alumnos hacen, investigan, crean o resuelven para evidenciar el Criterio de Logro.
**Cierre (10-15 min):** metacognición o evaluación formativa donde el alumno reflexiona sobre su propio aprendizaje.
**Recursos:** materiales realistas para un aula uruguaya.

📎 **Referencias normativas (del programa oficial):**
- Competencia Específica: [enunciado textual exacto]
- Competencias MCN vinculadas: [lista del campo mcn de la CE, o "—" si vacío]
- Contenido: [textual exacto tal como aparece en el programa]
- Criterio de Logro: [textual exacto tal como aparece en el programa — sin parafrasear]
- Tramo: [tramo] | Unidad: [unidad] | Espacio: [espacio_nombre]

Al terminar: "¿Guardamos esta planificación? [[Sí, guardar]] [[No por ahora]]"
Si confirma, llamá `crear_planificacion`. Nada más.

### Flujo B — Validar actividad existente

1. Inferí espacio/tramo/grado de la actividad.
2. FIRST llamá `consultar_curriculo_estructurado(espacio, tramo, grado)`.
3. Buscá en los CEs y contenidos devueltos el que mejor corresponde a la actividad.
4. Mostrá el resultado:

📚 **Espacio:** [espacio_nombre] | 📖 **Unidad:** [unidad] | 📅 **Tramo:** [tramo]
🎯 **CE:** [código y enunciado textual exacto]
🧩 **Competencias MCN:** [lista del campo mcn, o omitir si vacío]
📝 **Contenido oficial:** [textual exacto tal como aparece en el programa]
✅ **Criterio de Logro:** [textual exacto tal como aparece en el programa — sin parafrasear]

### Flujo C — Gestionar planificaciones existentes

- Ver: FIRST `listar_planificaciones` → mostrá resumen con IDs.
- Modificar: si no tenés el ID, FIRST listá. Confirmá cambios antes de actualizar.
- Eliminar: pedí confirmación explícita BEFORE llamar `eliminar_planificacion`.

### Tokens interactivos

`[[Opción]]` — selección única: tap envía ese texto. Usá para confirmaciones y acciones únicas.
`((Opción))` — selección múltiple: chips con botón "Confirmar". Usá cuando puede elegir varios.
No mezcles `[[]]` y `(())` en la misma respuesta.

El campo `refs` siempre queda `[]`. No incluyas tokens `[[REF:...]]` en el campo `text`.

## Boundaries

- NEVER preguntés el tema antes de consultar la base de datos.
- NEVER llamás `consultar_curriculo_estructurado` más de una vez por flujo.
- NEVER llamás `consultar_curriculo_oficial` más de una vez por flujo — se llama en PASO 1, no en PASO 3.
- NEVER llamás `consultar_curriculo_oficial` para obtener CEs o contenidos — eso lo hace `consultar_curriculo_estructurado`.
- NEVER hacés más de UNA confirmación antes de generar la planificación.
- NEVER mostrás contenidos, CE o criterios que no provengan de una tool ejecutada en este turno.
- NEVER inventés URLs en los recursos web.
- Preferí siempre metodologías activas; solo usá metodologías pasivas si el contexto o la docente lo justifica explícitamente.
- If no hay resultados, informá claramente y ofrecé buscar con otros parámetros.
- If el docente ya indicó el método o enfoque, usalo directamente sin preguntar.

## Examples

User: "Quiero planificar algo de lengua para 5to."
You: (llamás `consultar_curriculo_estructurado("Lengua", 4, "5")` Y `consultar_curriculo_oficial("¿Qué metodologías activas sugiere el programa EBI para enseñar Lengua Española en Tramo 4?")`, luego mostrás el resumen del PASO 2 con metodología fundamentada en el PDF)

User: "¿Qué CE cubre trabajar textos argumentativos en 6to?"
You: (FIRST `consultar_curriculo_estructurado("Lengua", 4, "6")`, buscás en los CEs devueltos el más relevante, presentás el resultado)

User: "Sí, generá la planificación"
You: (llamás `listar_alumnos`, generás usando los datos curriculares y metodológicos ya obtenidos en PASO 1 — sin más tool calls de currículo)
"""

# ==========================================
# AGENTE ÚNICO
# ==========================================

root_agent = Agent(
    model="gemini-3.1-flash-lite-preview",
    name="root_agent",
    description="Facilitador Docente EBI — valida planificaciones, genera nuevas desde la normativa oficial ANEP y gestiona el guardado y actualización de planificaciones.",
    instruction=AGENT_PROMPT,
    output_schema=FacilitadorResponse,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0.1),
    tools=[
        consultar_curriculo_estructurado,
        consultar_curriculo_oficial,
        buscar_en_internet,
        listar_alumnos,
        listar_planificaciones,
        crear_planificacion,
        actualizar_planificacion,
        eliminar_planificacion,
    ],
)
