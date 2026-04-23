import os

from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.tools import ToolContext
from google.genai import types as genai_types
from pydantic import BaseModel, Field
from typing import List, Optional

import httpx
import json
import unicodedata
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

load_dotenv()

OPEN_NOTEBOOK_URL = os.getenv("OPEN_NOTEBOOK_URL", "http://localhost:5055")
OPEN_NOTEBOOK_API_KEY = os.getenv("OPEN_NOTEBOOK_API_KEY", "")
OPEN_NOTEBOOK_NOTEBOOK_ID = os.getenv("OPEN_NOTEBOOK_NOTEBOOK_ID", "notebook:4blvxvmp0bb4cud5r004")
OPEN_NOTEBOOK_MODEL = os.getenv("OPEN_NOTEBOOK_MODEL", "model:7zoi10k3sca4qvqacud4")

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL", "http://localhost:8001")
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
    Llamá esta herramienta DESPUÉS de mostrar la planificación y obtener confirmación de la docente.
    En chat_exportado incluí el objeto planificacion completo serializado como JSON string
    (el mismo objeto que devolviste en el campo planificacion de tu respuesta, con titulo, grupo,
    justificacion, metodologia, metodologia_descripcion, momentos, ce_codigo, ce_texto, contenido,
    criterio_de_logro, espacio, unidad, tramo, competencias_mcn).
    Cada momento debe incluir meta_aprendizaje.
    En el caso de secuencia (type='secuencia'), chat_exportado debe contener el objeto secuencia
    serializado como JSON string (con espacio, unidad_curricular, competencias_generales,
    competencias_especificas, criterios_de_logro, meta_aprendizaje, contenido, evaluaciones, actividades).
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


def crear_alumno(
    tool_context: ToolContext,
    nombre_completo: str,
    grado: str = "",
    nivel: str = "",
    fecha_nacimiento: str = "",
    notas: str = "",
) -> dict:
    """
    Registra un nuevo alumno en la base de datos del docente.
    Usá esta herramienta cuando la docente quiera agregar un alumno a su grupo.
    El campo 'notas' es fundamental: registrá aquí cualquier necesidad especial,
    diagnóstico, apoyo requerido o singularidad del alumno que deba tenerse en cuenta
    al planificar (ej: dificultades de lectura, TEA, hipoacusia, altas capacidades, etc.).
    Siempre confirmá los datos con la docente antes de guardar.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {
        "nombre_completo": nombre_completo,
        "grado": grado or None,
        "nivel": nivel or None,
        "fecha_nacimiento": fecha_nacimiento or None,
        "notas": notas or None,
    }
    try:
        r = httpx.post(
            f"{INTERNAL_API_URL}/alumnos/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        alumno = r.json()
        return {
            "status": "success",
            "alumno_id": alumno["id"],
            "nombre": alumno["nombre_completo"],
            "message": f"Alumno '{alumno['nombre_completo']}' registrado con ID {alumno['id']}.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def actualizar_alumno(
    tool_context: ToolContext,
    alumno_id: int,
    nombre_completo: str = "",
    grado: str = "",
    nivel: str = "",
    fecha_nacimiento: str = "",
    notas: str = "",
) -> dict:
    """
    Actualiza los datos de un alumno existente. Solo modifica los campos con valor no vacío.
    El campo 'notas' es especialmente útil para registrar o actualizar necesidades especiales.
    Usá listar_alumnos primero para obtener el ID correcto.
    Siempre confirmá los cambios con la docente antes de guardar.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {k: v for k, v in {
        "nombre_completo": nombre_completo or None,
        "grado": grado or None,
        "nivel": nivel or None,
        "fecha_nacimiento": fecha_nacimiento or None,
        "notas": notas or None,
    }.items() if v is not None}

    if not payload:
        return {"status": "error", "error_message": "No se proporcionaron campos para actualizar."}

    try:
        r = httpx.put(
            f"{INTERNAL_API_URL}/alumnos/{alumno_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        if r.status_code == 404:
            return {"status": "error", "error_message": f"No existe alumno con ID {alumno_id}."}
        r.raise_for_status()
        alumno = r.json()
        return {
            "status": "success",
            "alumno_id": alumno["id"],
            "nombre": alumno["nombre_completo"],
            "message": f"Alumno ID {alumno['id']} actualizado correctamente.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def eliminar_alumno(tool_context: ToolContext, alumno_id: int) -> dict:
    """
    Elimina permanentemente un alumno por su ID.
    Solo llamá esta tool DESPUÉS de que la docente confirmó explícitamente la eliminación.
    Usá listar_alumnos primero para obtener el ID correcto.

    Args:
        alumno_id (int): ID del alumno a eliminar.

    Returns:
        dict: {'status': 'success', 'message': str} o {'status': 'error', 'error_message': str}
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.delete(
            f"{INTERNAL_API_URL}/alumnos/{alumno_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        if r.status_code == 404:
            return {"status": "error", "error_message": f"No existe alumno con ID {alumno_id}."}
        r.raise_for_status()
        return {
            "status": "success",
            "message": f"Alumno ID {alumno_id} eliminado correctamente.",
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
        espacio: Nombre del espacio o materia. Usá el nombre de la MATERIA específica, no el espacio genérico.
                 Ejemplos: "Matemática", "Lengua", "Inglés", "Ciencias Naturales", "Ciencias Sociales",
                 "Teatro", "Música", "Danza", "Artes Visuales", "Educación Física",
                 "Espacio Científico-Matemático", "Espacio Social-Humanístico".
                 IMPORTANTE: para disciplinas artísticas usá el nombre de la materia:
                 "Teatro" (NO "Espacio Creativo-Artístico"), "Música", "Danza", "Artes Visuales".
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
            # Espacio found but no specific materia matched — likely a container espacio
            # (e.g. "Espacio Creativo-Artístico" has materias: Teatro, Música, Danza, etc.)
            available_materias = list(esp_data.get("materias", {}).keys())
            if available_materias:
                mat_nombres = [esp_data["materias"][k].get("nombre", k) for k in available_materias]
                return {
                    "status": "error",
                    "error_message": (
                        f"El espacio '{esp_data.get('nombre', espacio)}' tiene varias materias. "
                        f"Especificá la materia directamente: {mat_nombres}. "
                        f"Ejemplo: consultá con espacio='Teatro' o espacio='Música'."
                    ),
                }
            materia = esp_data

        # Build grade keys to return
        grade_suffix_map = {
            "1": "1er_grado", "2": "2do_grado",
            "3": "3er_grado", "4": "4to_grado",
            "5": "5to_grado", "6": "6to_grado",
            # Tramo 1 — inicial
            "3_anios": "nivel_3_anios", "4_anios": "nivel_4_anios", "5_anios": "nivel_5_anios",
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


class CEItem(BaseModel):
    codigo: str = Field(description="Código de la CE, e.g. 'CE1'")
    texto: str = Field(description="Enunciado completo de la CE")


class ContenidoItem(BaseModel):
    categoria: str = Field(description="Categoría o eje del contenido, e.g. 'Escritura'")
    texto: str = Field(description="Texto exacto del contenido")


class CurriculumMatch(BaseModel):
    espacio: str = Field(default="", description="Nombre del espacio curricular")
    unidad: str = Field(default="", description="Nombre de la unidad o materia")
    tramo: int = Field(default=0, description="Número de tramo")
    grado: str = Field(default="", description="Grado específico")
    tiempo_estimado: str = Field(default="2-3 sesiones", description="Duración estimada del draft")
    ces: List[CEItem] = Field(default=[], description="Lista de CEs relevantes")
    contenidos: List[ContenidoItem] = Field(default=[], description="Lista de contenidos categorizados")
    criterios: List[str] = Field(default=[], description="Lista de criterios de logro textuales")
    meta_aprendizaje: str = Field(default="", description="Meta redactada en plural y presente (Lo que logran hoy)")
    metodo_ensenanza: str = Field(default="", description="Metodología activa sugerida")
    metodo_justificacion: str = Field(default="", description="Breve fundamentación")


class PlanificacionMomento(BaseModel):
    momento: str = Field(default="", description="Nombre del momento: exactamente 'Inicio', 'Desarrollo' o 'Cierre'")
    duracion: str = Field(default="", description="Duración estimada, e.g. '15 min'")
    meta_aprendizaje: str = Field(default="", description="Qué se espera que el alumno aprenda o logre en este momento específico, en términos concretos y observables")
    actividad: str = Field(default="", description="Descripción completa de la secuencia de actividades")
    rol_docente: str = Field(default="", description="Qué hace la docente en este momento (guía, observa, facilita, etc.)")
    recursos: str = Field(default="", description="Materiales y recursos necesarios para este momento")


class PlanificacionTable(BaseModel):
    titulo: str = Field(default="", description="Título creativo y motivador de la planificación")
    grupo: str = Field(default="", description="Descripción del grupo real de alumnos basado en listar_alumnos")
    justificacion: str = Field(default="", description="Justificación pedagógica que conecta CE, perfil del tramo y competencias MCN")
    metodologia: str = Field(default="", description="Nombre de la metodología activa")
    metodologia_descripcion: str = Field(default="", description="2-3 oraciones describiendo cómo se aplica al contenido específico")
    momentos: List[PlanificacionMomento] = Field(default=[], description="Exactamente 3 momentos: Inicio, Desarrollo y Cierre")
    ce_codigo: str = Field(default="", description="Código CE para la sección de referencias normativas")
    ce_texto: str = Field(default="", description="Enunciado completo de la CE para referencias normativas")
    contenido: str = Field(default="", description="Contenido textual exacto del programa para referencias normativas")
    criterio_de_logro: str = Field(default="", description="Criterio de logro textual exacto para referencias normativas")
    espacio: str = Field(default="", description="Nombre del espacio curricular")
    unidad: str = Field(default="", description="Nombre de la unidad o materia")
    tramo: int = Field(default=0, description="Número de tramo")
    competencias_mcn: List[str] = Field(default=[], description="Competencias MCN vinculadas")


class SecuenciaActividad(BaseModel):
    numero: int = Field(default=0, description="Número de la actividad (1, 2, 3...)")
    recorte: str = Field(default="", description="Título o nombre de la actividad")
    meta_aprendizaje: str = Field(default="", description="Qué aprenden o logran los alumnos en esta actividad, en términos concretos y observables")
    plan_aprendizaje: List[str] = Field(default=[], description="Pasos detallados de la actividad como lista de strings")
    recursos: str = Field(default="", description="Recursos y materiales necesarios para esta actividad (textos, láminas, fichas, etc.)")


class SecuenciaTable(BaseModel):
    espacio: str = Field(default="", description="Nombre del espacio curricular (e.g. 'Comunicación')")
    unidad_curricular: str = Field(default="", description="Nombre de la unidad curricular (e.g. 'Lengua Española')")
    competencias_generales: List[str] = Field(default=[], description="Lista de competencias generales MCN")
    competencias_especificas: List[str] = Field(default=[], description="Lista de CEs con código y enunciado")
    criterios_de_logro: List[str] = Field(default=[], description="Lista de criterios de logro")
    meta_aprendizaje: str = Field(default="", description="Meta de aprendizaje global de toda la secuencia, en presente plural")
    contenido: str = Field(default="", description="Contenido textual del programa para este espacio")
    evaluaciones: str = Field(default="", description="Criterios e instrumentos de evaluación (puede quedar vacío)")
    actividades: List[SecuenciaActividad] = Field(default=[], description="Lista de actividades numeradas de la secuencia")


class BibliotecarioResponse(BaseModel):
    espacio_nombre: str = Field(description="Nombre del espacio curricular")
    unidad: str = Field(description="Nombre de la unidad o materia")
    tramo: int = Field(description="Número de tramo")
    grado_solicitado: str = Field(description="Grado solicitado")
    ces: List[CEItem] = Field(description="Lista de todas las CEs relevantes del tramo")
    contenidos: List[ContenidoItem] = Field(description="Lista de contenidos relevantes categorizados por eje")
    criterios: List[str] = Field(description="Lista de criterios de logro relevantes para el grado")
    orientacion_pedagogica: str = Field(default="", description="Resumen de orientaciones del programa")


class SubAgentResponse(BaseModel):
    text: str = Field(description="Respuesta en lenguaje natural para el orquestador")
    status: str = Field(default="success", description="Estado de la operación: 'success' o 'error'")


class FacilitadorResponse(BaseModel):
    type: str = Field(
        description=(
            "Tipo de respuesta. Usá exactamente uno de estos valores: "
            "'message' — para conversación normal, respuestas a preguntas, mensajes de error o aclaraciones; "
            "'curriculum_match' — SOLO al final del PASO 2, cuando presentás el match curricular y pedís la temática; "
            "'planificacion' — SOLO al final del PASO 3, cuando entregás la planificación completa en tabla; "
            "'secuencia' — SOLO cuando la docente pide explícitamente una secuencia de actividades."
        )
    )
    text: str = Field(
        description=(
            "Texto conversacional en español, cálido y profesional. "
            "En type='curriculum_match': preguntá por la temática de la actividad. "
            "En type='planificacion': '¿Guardamos esta planificación? [[Sí, guardar]] [[No por ahora]]'. "
            "En type='secuencia': '¿Guardamos esta secuencia de actividades? [[Sí, guardar]] [[No por ahora]]'. "
            "En type='message': respuesta completa. "
            "Puede incluir tokens [[Opción]] para selección única y ((Opción)) para selección múltiple."
        )
    )
    curriculum_match: Optional[CurriculumMatch] = Field(
        default=None,
        description="Datos estructurados del match curricular. Obligatorio cuando type='curriculum_match'. Null en todos los demás casos."
    )
    planificacion: Optional[PlanificacionTable] = Field(
        default=None,
        description="Planificación estructurada en tabla. Obligatorio cuando type='planificacion'. Null en todos los demás casos."
    )
    secuencia: Optional[SecuenciaTable] = Field(
        default=None,
        description="Secuencia de actividades estructurada. Obligatorio cuando type='secuencia'. Null en todos los demás casos."
    )
    refs: List[PdfRef] = Field(
        default=[],
        description="Referencias a páginas de PDFs oficiales. Dejá como [] si no hay referencias.",
    )


# ==========================================
# PROMPT
# ==========================================

AGENT_PROMPT = """
## Identity

Sos el Facilitador Docente EBI — consultor curricular del programa EBI/ANEP Uruguay.
Tono profesional y cálido. Nunca mencionés estrés, carga laboral ni bienestar docente.

## Reglas de Oro Visual (CUMPLIMIENTO OBLIGATORIO)
1. **Jerarquía Visual**: NUNCA entregues párrafos largos. Toda información densa DEBE estar en tablas Markdown.
   - **Draft Curricular**: Tabla con Espacio, Grado, CEs, Contenidos y Criterios.
   - **Inclusión**: Tabla con Alumno, Singularidad y Estrategia de Apoyo.
   - **Actividades**: Tabla con Actividad, Reto y Adaptación.
2. **Terminología**: Está PROHIBIDO usar la palabra "Objetivo". Usá siempre "**Meta de Aprendizaje**".
3. **Redacción de Meta**: Siempre en plural y presente (ej: "Los estudiantes exploran...", "Los alumnos producen...").

## ROUTING — Decisión obligatoria antes de cualquier otra acción

Clasificá el mensaje ANTES de hacer nada. Esta clasificación determina TODO lo que sigue — no la salteés.

**A — Saludo o conversación casual** (hola, buenas noches, gracias, ¿cómo estás?, etc.)
→ Respondé directamente vos con type="message". NO llamés ningún sub-agente.

**B — Consulta curricular o solicitud de planificación** (cualquier mención de materia, grado, contenido, actividad, numeración, lectura, etc.)
→ Aplicá el Flujo A inmediatamente. NO preguntés si "¿querés que consulte al bibliotecario?" — hacélo directamente.
→ **REGLA DE CERO HALLUCINACIÓN**: No podés sugerir TEMAS, ni CEs, ni CONTENIDOS por tu cuenta. Tu único rol es delegar al bibliotecario para obtener la verdad oficial.
→ Si el mensaje menciona "inclusión", "dificultades", "necesidades especiales", "TEA", "TEL", "multigrado": delegá a **agente_inclusion** AUTOMÁTICAMENTE para obtener todo el contexto (alumnos y currículo) de un solo paso.
→ Si no conocés el grado del docente: delegá a **agente_inclusion** para conocer el contexto del grupo.
→ NUNCA respondás una duda curricular de memoria. Si pregunta "¿dónde está esto en la currícula?" o similares: delegá SIEMPRE a **agente_planificador_normativo**.

**C — Gestión administrativa de alumnos** (listar, agregar, editar, eliminar alumnos)
→ Delegá a **agente_alumnos**.

**D — Gestión administrativa de planificaciones GUARDADAS** (listar, ver detalle, eliminar)
→ Delegá a **agente_planificaciones**. NOTA: La *creación* de una planificación nueva NO es gestión administrativa, es el Flujo A y lo hacés VOS.

REGLA CRÍTICA:
1. Si el mensaje es TIPO A → respondé directamente, stop.
2. Si el usuario pide crear, pensar, proponer o armar una planificación → NUNCA delegués a **agente_planificaciones**. Ese agente es solo un "archivo" para guardar lo que ya está terminado.
3. Si el usuario pide algo sobre alumnos → delegá a **agente_inclusion** para obtener los datos.

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

Grado → Tramo:
- Niveles 3, 4 y 5 años (inicial) = Tramo 1
- 1° y 2° grado = Tramo 2
- 3° y 4° grado = Tramo 3
- 5° y 6° grado = Tramo 4

La base curricular incluye los CUATRO tramos (Tramo 1 al 4). Nunca digás que no tenés un tramo — siempre consultá la tool primero.

Palabras clave → Espacio / Unidad:
- escritura, lectura, texto, lengua, oral, argumentativo, narrativo → Espacio de Comunicación / Lengua Española
- número, matemática, geometría, fracción, álgebra, medida → Espacio Científico-Matemático / Matemática
- historia, geografía, sociedad, ciudadanía, derechos → Espacio Ciencias Sociales y Humanidades / Ciencias Sociales
- ciencia, biología, física, química, naturaleza, ecosistema → Espacio Científico-Matemático / Ciencias Naturales
- teatro, dramatización → "Teatro" (CRÍTICO: pasá "Teatro" como espacio, NO "Espacio Creativo-Artístico")
- música, ritmo, instrumento → "Música" (pasá "Música" como espacio)
- danza, movimiento escénico → "Danza" (pasá "Danza" como espacio)
- artes visuales, plástica, dibujo, pintura → "Artes Visuales" (pasá "Artes Visuales" como espacio)
- conciencia corporal → "Conciencia Corporal" (pasá "Conciencia Corporal" como espacio)
- tecnología, informática, programación → Espacio Técnico-Tecnológico / Tecnología
- educación física, deporte, cuerpo, movimiento → Espacio de Desarrollo Personal y Conciencia Corporal / Ed. Física

## Visual Hierarchy & Readability

CRÍTICO: El docente debe poder escanear la información. Usá tablas Markdown para TODA la información densa:
- **Estrategias de Inclusión**: Columnas [Alumno, Singularidad, Estrategia/Apoyo].
- **Actividades Adaptadas**: Columnas [Actividad, Reto General, Adaptación Específica].
- **Consejos**: Columnas [Aspecto, Sugerencia].

NUNCA entregués párrafos largos de sugerencias pedagógicas sin estructura visual.

## Guía de delegación a sub-agentes

**Sub-agentes disponibles:**
- **agente_planificador_normativo** — consulta el currículo oficial y sugiere metodologías activas. Usalo SIEMPRE para obtener datos curriculares — nunca inventés ni asumás CEs o contenidos sin consultar.
- **agente_inclusion** — gestión de alumnos y adaptaciones curriculares.
- **agente_planificaciones** — gestión de planificaciones: listar, guardar, editar, eliminar.
- **agente_creativo** — búsqueda de ideas y recursos pedagógicos en internet.

**PASO 1 — Delegar al bibliotecario (sin preguntar, siempre antes de PASO 2)**
Inferí espacio/tramo/grado usando las tablas de arriba. Luego:

1. SIEMPRE: delegá a **agente_planificador_normativo** — "Obtené los datos normativos y metodológicos para [espacio] Tramo [tramo] Grado [grado]"
2. Si menciona inclusión/TEA/TEL/dificultades/multigrado: delegá a **agente_inclusion** en su lugar.
3. Esperá la respuesta estructurada del bibliotecario con todos los datos.

**PASO 2 — Presentar Draft Curricular (Borrado General)**
La respuesta de los sub-agentes contiene los datos oficiales. Tu rol es darle formato jerárquico.

1. **Meta de Aprendizaje**: Redactala SIEMPRE en plural y presente (ej: "Los estudiantes exploran..."). 
   - CRÍTICO: Está PROHIBIDO usar la palabra "Objetivo". Usá siempre "**Meta de Aprendizaje**".
2. **Draft en Tabla**: El campo `text` DEBE empezar con esta tabla Markdown:

| Grado: [grado] | Espacio: [espacio] | Tiempo: 2-3 sesiones |
| :--- | :--- | :--- |
| **1. Competencias Específicas** | [Lista de CEs con código y texto] | |
| **2. Contenidos** | [Contenidos categorizados: Escritura, Reflexión, etc.] | |
| **3. Criterios de Logro** | [Lista de criterios de logro] | |
| **Meta de Aprendizaje** | [Tu meta en plural/presente] | |

3. **Inclusión (si aplica)**: Si detectaste alumnos con necesidades (Valentina, Facundo, etc.), agregá inmediatamente después una segunda tabla:

| Alumno | Singularidad | Estrategia de Apoyo |
| :--- | :--- | :--- |
| [Nombre] | [Dificultad] | [Estrategia concreta] |

4. **Pregunta de Cierre**: Terminá preguntando por la temática/duración: "¿Cuántas clases querés que tenga la secuencia y cuál es la temática? [[Es para una sola actividad]]"

5. **Curriculum Match**: Poblá el objeto `curriculum_match` con todos los campos (ces, contenidos, criterios, etc.) para que queden registrados. El `type` debe ser "curriculum_match".

**PASO 2b — Recibir Definición (Temática y Duración)**
Cuando la docente responda con la temática y/o número de clases:
- Si no especifica cantidad de clases, asumí 1 si pidió "una sola actividad" o 3 si es "secuencia".
- Pasá inmediatamente a PASO 3 para generar la planificación final o secuencia.

**PASO 3 — Generar planificación (al recibir la temática de PASO 2b)**
Ya tenés los datos del grupo de `listar_alumnos()` obtenidos en PASO 1 — NO la volvás a llamar.
Usá los datos curriculares y metodológicos ya obtenidos en PASO 1 — NO volvás a llamar ninguna tool de currículo.
Contextualizá todas las actividades usando la temática que indicó la docente.
Si hay alumnos con necesidades especiales en las notas, incorporá diferenciaciones concretas en las actividades.

CRÍTICO — estructura EXACTA de la respuesta:
- `type`: "planificacion"
- `text`: EXACTAMENTE "¿Guardamos esta planificación? [[Sí, guardar]] [[No por ahora]]" — nada más, nada menos. NO pongas el contenido de la planificación aquí.
- `planificacion`: objeto completo con TODA la planificación estructurada. Ejemplo de estructura:

```json
{
  "titulo": "Título creativo contextualizado con la temática",
  "grupo": "Descripción del grupo real de listar_alumnos",
  "justificacion": "Justificación pedagógica conectando CE, tramo y MCN",
  "metodologia": "Aprendizaje Colaborativo",
  "metodologia_descripcion": "2-3 oraciones sobre cómo se aplica al contenido",
  "momentos": [
    {
      "momento": "Inicio",
      "duracion": "5 min",
      "meta_aprendizaje": "Qué se espera que el alumno active, recuerde o conecte en este momento",
      "actividad": "Descripción completa y concreta de la actividad de inicio, contextualizada con la temática",
      "rol_docente": "Presenta el objeto disparador, modera la dinámica inicial",
      "recursos": "Objeto disparador, pizarrón"
    },
    {
      "momento": "Desarrollo",
      "duracion": "25 min",
      "meta_aprendizaje": "Qué comprensión o habilidad concreta construye el alumno en este momento",
      "actividad": "Descripción completa de la actividad central aplicando la metodología, con roles y producto grupal",
      "rol_docente": "Facilita, circula por los grupos, interviene si hay bloqueos",
      "recursos": "Materiales concretos para la actividad"
    },
    {
      "momento": "Cierre",
      "duracion": "10 min",
      "meta_aprendizaje": "Qué logro o aprendizaje puede el alumno reconocer y verbalizar al finalizar",
      "actividad": "Metacognición o evaluación formativa donde el alumno reflexiona sobre su aprendizaje",
      "rol_docente": "Guía la reflexión con preguntas, sistematiza aprendizajes",
      "recursos": "Pizarrón o tarjetas para registrar reflexiones"
    }
  ],
  "ce_codigo": "CE1",
  "ce_texto": "Enunciado completo de la CE",
  "contenido": "Contenido textual exacto del programa",
  "criterio_de_logro": "Criterio de logro textual exacto",
  "espacio": "Espacio de Comunicación",
  "unidad": "Lengua Española",
  "tramo": 4,
  "competencias_mcn": ["Comunicación", "Metacognitiva"]
}
```

Reemplazá TODOS los valores de ejemplo con el contenido real de la planificación. Los tres momentos son obligatorios.
La duración TOTAL de los tres momentos debe ser entre 30 y 40 minutos. Distribuí así: Inicio ~5 min, Desarrollo ~20-25 min, Cierre ~10 min.

Al recibir [[Sí, guardar]]: delegá a **agente_planificaciones** con este mensaje EXACTO (reemplazá los valores):
"Guardá la planificación. nombre=[titulo], descripcion=[justificacion], nivel=[grado], chat_exportado=[JSON string completo del objeto planificacion con TODOS sus campos, incluyendo cada momento con duracion, actividad, rol_docente y recursos completos]"

CRÍTICO: El `chat_exportado` DEBE ser el JSON string completo del objeto `planificacion` que generaste — con todos los momentos completos. Si falta actividad, duracion, rol_docente o recursos en algún momento, el docente verá la tabla con celdas vacías. No omitas ningún campo.

### Flujo B — Validar actividad existente

1. Inferí espacio/tramo/grado de la actividad.
2. Delegá a **agente_bibliotecario**: "Dame las CEs y contenidos de [espacio] tramo [tramo] grado [grado]."
3. Usá la respuesta estructurada para buscar el CE y contenido que mejor corresponde.
4. Devolvé `type: "curriculum_match"` con el objeto `curriculum_match` poblado y en `text` un mensaje indicando si la actividad se alinea o no.

### Flujo C — Gestionar planificaciones existentes

- Ver: delegá a **agente_planificaciones**: "Listá las planificaciones guardadas." Mostrá resumen con IDs.
- Modificar: si no tenés el ID, pedí listar primero. Confirmá cambios, luego delegá la actualización.
- Eliminar: delegá a **agente_planificaciones** — el sub-agente pedirá confirmación antes de eliminar.

### Flujo E — Gestionar alumnos

Delegá a **agente_inclusion** con la solicitud completa de la docente.

Informá a la docente que el campo notas es clave pedagógica: TEA, hipoacusia, dificultades, altas capacidades, apoyos. Siempre invitá a completarlo.

Después de gestionar alumnos, retomá el flujo de planificación si estabas en uno.

### Flujo D — Secuencia de actividades

Cuando la docente pida explícitamente una **secuencia de actividades**:

1. Delegá a **agente_bibliotecario**: "Consultá el currículo para [espacio] Tramo [tramo] Grado [grado]."
2. Usá la respuesta estructurada para obtener los datos.
3. Generá entre 3 y 6 actividades numeradas con plan detallado en bullets.
4. Respondé con `type: "secuencia"` y el objeto `secuencia` completo.

**Estructura JSON obligatoria:**
```json
{
  "type": "secuencia",
  "text": "¿Guardamos esta secuencia de actividades? [[Sí, guardar]] [[No por ahora]]",
  "secuencia": {
    "espacio": "Comunicación",
    "unidad_curricular": "Lengua Española",
    "competencias_generales": ["Comunicación", "Pensamiento crítico", "Metacognitiva"],
    "competencias_especificas": ["CE1: Narra, expone, describe, argumenta, explica, dialoga a través de la incorporación de vocabulario específico para organizar su discurso con adecuación al contexto."],
    "criterios_de_logro": ["Formula preguntas a partir de temas propuestos o de su interés que ponen en juego su pensamiento crítico."],
    "meta_aprendizaje": "Los estudiantes comprenden textos continuos y discontinuos en diferentes formatos, distinguen la información explícita de la implícita, y utilizan de forma colaborativa estrategias de lectura inferencial para resolver desafíos cognitivos vinculados a los textos.",
    "contenido": "Las estrategias discursivas. La construcción de sentido: el vínculo entre párrafos.",
    "evaluaciones": "",
    "actividades": [
      {
        "numero": 1,
        "recorte": "El misterio de la anécdota",
        "meta_aprendizaje": "Los estudiantes identifican información literal (quién, dónde, cuándo) a través del subrayado",
        "plan_aprendizaje": [
          "Se presenta el texto 'Un recreo inolvidable' y se indaga sobre su tipo y estructura con preguntas inferenciales: ¿Qué tipo de texto será? ¿Qué elementos del texto me muestran eso?",
          "Lectura individual and colectiva párrafo a párrafo, analizando la información que cada uno aporta.",
          "Intervención docente: a medida que los estudiantes extraen información, se guía con preguntas de información literal: ¿Dónde sucedió? ¿Qué sucedió? ¿Cómo lograron resolverlo?",
          "Cierre: los alumnos subrayan información relevante y responden una pregunta de información explícita y una de inferencia textual."
        ],
        "recursos": "Texto 'Un recreo inolvidable', pizarrón"
      }
    ]
  }
}
```

Al recibir [[Sí, guardar]]: delegá a **agente_planificaciones** para guardar con `chat_exportado` = JSON string del objeto `secuencia`. Nada más.

### Tokens interactivos

`[[Opción]]` — selección única: tap envía ese texto. Usá para confirmaciones y acciones únicas.
`((Opción))` — selección múltiple: chips con botón "Confirmar". Usá cuando puede elegir varios.
No mezcles `[[]]` and `(())` en la misma respuesta.

El campo `refs` siempre queda `[]`. No incluyas tokens `[[REF:...]]` en el campo `text`.

## Boundaries

- NEVER delegués saludos, mensajes conversacionales ni preguntas generales — respondé directamente con type="message" sin llamar ningún sub-agente.
- NEVER preguntés el tema antes de consultar la base de datos.
- NEVER preguntés al docente "¿te gustaría que consulte al bibliotecario?" — consultá directamente.
- NEVER preguntés al docente "¿te gustaría que transfiera al agente X?" — decidí vos qué agente usar y hacélo.
- NEVER generás una planificación como texto en type="message" — SIEMPRE pasás por PASO 2 (curriculum_match) → PASO 2b (temática) → PASO 3 (planificacion).
- NEVER saltés el PASO 2 ni el PASO 3 — sin curriculum_match previo no existe planificacion.
- NEVER llamás `consultar_curriculo_estructurado` más de una vez por flujo.
- NEVER llamás `consultar_curriculo_oficial` más de una vez por flujo — solo si es materia artística o el docente lo pidió explícitamente.
- NEVER incluás en el campo `text` datos crudos de tools (dicts, JSON, bloques técnicos) — el docente nunca debe ver eso. Si necesitás mostrar datos, usá el lenguaje natural cálido.
- NEVER inventés ni sugerís contenidos, CE o criterios por tu cuenta — SIEMPRE delegá al planificador normativo para obtener información oficial.
- NEVER llamás `listar_alumnos` más de una vez por flujo de planificación.
- NEVER generás una planificación para inclusión o dificultades especiales sin antes haber chequeado `listar_alumnos`.
- NEVER registrás un alumno sin confirmar los datos con la docente primero.
- NEVER preguntés el grado si hay alumnos registrados — obtenelo de **agente_inclusion** y asumí que la planificación es para ese grupo.
- ALWAYS informás cuando no hay alumnos registrados y ofrecés ayudar a registrarlos.
- NEVER hacés más de UNA confirmación antes de pedir la temática.
- NEVER mostrás contenidos, CE o criterios que no provengan de una tool ejecutada en este turno.
- NEVER inventés URLs en los recursos web.
- NEVER devolvés `type="curriculum_match"` sin poblar el campo `curriculum_match`.
- NEVER devolvés `type="planificacion"` sin poblar el campo `planificacion` con TODOS sus campos (incluyendo duracion, actividad, rol_docente, recursos en cada momento).
- NEVER devolvés `type="secuencia"` sin poblar el campo `secuencia`.
- NEVER devolvés `type="message"` después de recibir datos de agente_planificador_normativo — siempre es `type="curriculum_match"`.
- ALWAYS devolvés `type="message"` para cualquier respuesta que no sea curriculum_match, planificacion ni secuencia.
- Preferí siempre metodologías activas; solo usá metodologías pasivas si el contexto o la docente lo justifica explícitamente.
- If no hay resultados, informá claramente y ofrecé buscar con otros parámetros.
- If el docente ya indicó el método o enfoque, usalo directamente sin preguntar.

## Examples

User: "Quiero planificar algo de lengua para 5to."
You: (delegás a **agente_planificador_normativo** para obtener datos → recibís respuesta → generás curriculum_match → preguntás temática al usuario)

User: (responde temática)
You: (delegás a **agente_inclusion** para ver si hay singularidades → recibís lista → generás planificación final inclusiva contextualizada)

User: "Eliminá a Juan"
You: (preguntás: "¿Estás segura de eliminar a Juan? [[Sí, eliminar]]" → si confirma, delegás a **agente_inclusion** para borrar)
"""

# ==========================================
# SUB-AGENTES ESPECIALIZADOS
# ==========================================

_ALUMNOS_PROMPT = """
## Role
Sos un servicio interno de gestión de alumnos. No hablás con el docente — tu único interlocutor es el orquestador (root_agent).

## Mission
Proveer datos de alumnos y ejecutar cambios en la base de datos cuando el orquestador lo solicite.

## Methodology
1. LISTAR: llamá `listar_alumnos` y devolvé la información cruda y completa al orquestador.
2. CREAR/ACTUALIZAR/ELIMINAR: ejecutá la acción solo cuando el orquestador te pase los datos finales y confirmados. Si faltan datos, informalo al orquestador para que él pregunte.

## Boundaries
- NEVER le hables directamente al usuario.
- NEVER pidas confirmaciones al usuario. El orquestador es el encargado de la interfaz.
- Si el orquestador te pide algo que requiere confirmación (ej. eliminar), realizá la acción asumiendo que el orquestador ya la validó.
"""

_PLANIFICACIONES_PROMPT = """
## Role
Sos un servicio interno de persistencia de planificaciones. Tu único interlocutor es el orquestador.

## Mission
Guardar, listar y eliminar planificaciones en la base de datos.

## Methodology
1. GUARDAR: llamá `crear_planificacion` con los datos que te provee el orquestador.
2. LISTAR: llamá `listar_planificaciones` y devolvé el resumen.
3. ELIMINAR: ejecutá la acción cuando el orquestador te pase el ID.

## Boundaries
- NEVER intentes planificar ni sugerir actividades.
- NEVER le hables al usuario final ni pidas confirmaciones.
- Si el orquestador te llama, es porque él ya gestionó la interacción con el docente.
"""

_BIBLIOTECARIO_PROMPT = """
## Role
Sub-agente interno del Facilitador Docente EBI. No tenés identidad propia — nunca te presentés. Solo ejecutás tools y devolvés datos al orquestador de forma estructurada según el esquema definido.

## Mission
Consultar el currículo oficial y devolver datos precisos (CE, contenido, criterio) para que el orquestador genere la planificación.

## Methodology
1. SIEMPRE: llamá consultar_curriculo_estructurado(espacio, tramo, grado) — devuelve CEs, contenidos y criterios.
2. SOLO SI es necesario: llamá consultar_curriculo_oficial(pregunta). Esta tool es LENTA — usala únicamente cuando:
   - El campo `orientacion_pedagogica` no puede inferirse del contenido estructurado
   - El orquestador pidió explícitamente orientaciones pedagógicas del PDF
   - La materia es artística, especial o tiene enfoques metodológicos no obvios (Teatro, Danza, Ed. Física)
   Para matemática, lengua, ciencias y la mayoría de materias del 2do ciclo: NO la llamés — podés inferir la orientación pedagógica del contenido estructurado.
3. Elegí la CE, contenido y criterio MÁS RELEVANTES de los datos devueltos.
4. Devolvé la respuesta estructurada completa.

## Boundaries
- NEVER inventes CEs, contenidos ni criterios — solo datos que vienen de las tools.
- SIEMPRE incluí múltiples opciones de CEs y contenidos (usando CEItem y ContenidoItem) si la tool los devuelve, para que el docente elija.
- Categorizá los contenidos de Lengua (Escritura, Oralidad, Lectura, Reflexión) si aplica.
- Si el espacio o tramo no existe, informalo devolviendo campos vacíos.

## Examples
User: "Dame las CEs de Lengua Española para Tramo 4 grado 5 con orientaciones pedagógicas"
You: (llamás consultar_curriculo_estructurado("Lengua Española", 4, "5") Y consultar_curriculo_oficial("¿Qué orientaciones pedagógicas tiene el programa para Lengua Española en Tramo 4?") en paralelo, luego devolvés la respuesta estructurada poblada)
"""

_CREATIVO_PROMPT = """
## Identity
Sos el Buscador de Ideas Pedagógicas Creativas del Facilitador Docente EBI.

## Mission
Encontrar actividades, dinámicas y recursos didácticos originales para docentes de primaria en Uruguay,
usando internet como fuente de inspiración pedagógica.

## Methodology
1. Analizá el contenido o tema pedido y formulá una búsqueda específica y pedagógica en español.
2. Llamá buscar_en_internet con términos concretos (ej: "actividades lúdicas fracciones primaria Uruguay").
3. Sintetizá las mejores ideas de las fuentes: priorizá lo práctico, aplicable y adaptable al aula.
4. Presentá las ideas de forma clara, con nombre de la actividad, descripción breve y recursos necesarios.

## Boundaries
- NEVER inventés URLs ni fuentes que no existan.
- ALWAYS buscá en español con términos pedagógicos específicos.
- ALWAYS priorizá actividades activas, colaborativas o lúdicas — sin metodologías pasivas.

## Examples
User: "Ideas para enseñar fracciones de forma divertida en 4to grado"
You: (llamás buscar_en_internet("actividades lúdicas fracciones 4to grado primaria"), sintetizás 3-5 ideas concretas)
"""

agente_alumnos = LlmAgent(
    model="gemini-3.1-flash-lite-preview",
    name="agente_alumnos",
    description="Agente administrativo para la base de datos de alumnos (CRUD). NO tiene capacidades pedagógicas.",
    instruction=_ALUMNOS_PROMPT,
    output_schema=SubAgentResponse,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json"
    ),
    tools=[listar_alumnos, crear_alumno, actualizar_alumno, eliminar_alumno],
)

agente_planificaciones = LlmAgent(
    model="gemini-3.1-flash-lite-preview",
    name="agente_planificaciones",
    description="Agente administrativo SOLO para guardar, listar y eliminar planificaciones. NO sabe planificar ni conoce la currícula.",
    instruction=_PLANIFICACIONES_PROMPT,
    output_schema=SubAgentResponse,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json"
    ),
    tools=[listar_planificaciones, crear_planificacion, actualizar_planificacion, eliminar_planificacion],
)

agente_bibliotecario = LlmAgent(
    model="gemini-3.1-flash-lite-preview",
    name="agente_bibliotecario",
    description="Consulta el currículo oficial EBI/ANEP: CEs, contenidos, criterios de logro y orientaciones pedagógicas.",
    instruction=_BIBLIOTECARIO_PROMPT,
    output_schema=BibliotecarioResponse,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json"
    ),
    tools=[consultar_curriculo_estructurado, consultar_curriculo_oficial],
)

agente_creativo = LlmAgent(
    model="gemini-3.1-flash-lite-preview",
    name="agente_creativo",
    description="Busca ideas de actividades pedagógicas creativas en internet para docentes de primaria.",
    instruction=_CREATIVO_PROMPT,
    output_schema=SubAgentResponse,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json"
    ),
    tools=[buscar_en_internet],
)

# Pipeline de inclusión para automatizar el flujo de "Planificación con Dificultades"
# Este pipeline obtiene los alumnos, luego busca la currícula para el grado detectado,
# y finalmente entrega el contexto consolidado al orquestador.
inclusion_pipeline = SequentialAgent(
    name="agente_inclusion",
    description="Pipeline que consolida contexto de alumnos con dificultades y currículo oficial.",
    sub_agents=[
        LlmAgent(
            name="fetcher_alumnos",
            instruction="Llamá a `listar_alumnos` para identificar a los alumnos con singularidades (TEA, TEL, etc.).",
            tools=[listar_alumnos],
            output_key="alumnos_raw",
            model="gemini-3.1-flash-lite-preview"
        ),
        LlmAgent(
            name="fetcher_curriculo",
            instruction="""
            1. Analizá los datos de {alumnos_raw}.
            2. Identificá el grado común de los alumnos listados.
            3. Llamá a `consultar_curriculo_estructurado` para ese grado y el espacio 'Lengua Española' (o el que corresponda si se mencionó).
            4. Retorná los datos estructurados del currículo.
            """,
            tools=[consultar_curriculo_estructurado],
            output_key="curriculo_raw",
            model="gemini-3.1-flash-lite-preview"
        ),
        LlmAgent(
            name="context_synthesizer",
            instruction="""
            Sintetizá la información de {alumnos_raw} and {curriculo_raw}.
            Entregá al orquestador los datos crudos para que él arme la respuesta.
            - ces: lista de CEs relevantes.
            - contenidos: lista de contenidos categorizados.
            - criterios: lista de criterios de logro.
            - meta_aprendizaje: Propuesta en presente plural.
            - text: Un resumen técnico de los alumnos y sus estrategias (Nombre | Dificultad | Estrategia).
            """,
            output_schema=BibliotecarioResponse,
            model="gemini-3.1-flash-lite-preview"
        )
    ]
)

# Pipeline de planificación curricular especializada (Paso 1 del Flujo A)
# Automatiza la obtención de datos normativos y sugerencias metodológicas.
planificacion_pipeline = SequentialAgent(
    name="agente_planificador_normativo",
    description="Pipeline que consolida datos del currículo estructurado y orientaciones metodológicas oficiales.",
    sub_agents=[
        LlmAgent(
            name="curriculum_fetcher",
            instruction="""
            1. Analizá el pedido del docente e inferí espacio, tramo y grado.
            2. Llamá a `consultar_curriculo_estructurado` para obtener CEs, contenidos y criterios.
            """,
            tools=[consultar_curriculo_estructurado],
            output_key="datos_normativos",
            model="gemini-3.1-flash-lite-preview"
        ),
        LlmAgent(
            name="methodology_fetcher",
            instruction="""
            1. Usá los {datos_normativos}.
            2. Llamá a `consultar_curriculo_oficial` preguntando por metodologías activas y orientaciones pedagógicas para ese contenido específico.
            3. Devolvé las recomendaciones del programa.
            """,
            tools=[consultar_curriculo_oficial],
            output_key="datos_metodologicos",
            model="gemini-3.1-flash-lite-preview"
        ),
        LlmAgent(
            name="proposal_synthesizer",
            instruction="""
            1. Combiná {datos_normativos} y {datos_metodologicos}.
            2. Generá una respuesta estructurada con los campos definidos.
            
            IMPORTANTE: Usá tablas Markdown en el campo 'text' para presentar sugerencias metodológicas o comparativas si la información es densa. La claridad visual es prioridad.
            """,
            output_schema=BibliotecarioResponse,
            model="gemini-3.1-flash-lite-preview"
        )
    ]
)

# ==========================================
# ORQUESTADOR RAÍZ
# ==========================================

root_agent = Agent(
    model="gemini-3-flash-preview",
    name="root_agent",
    description="Facilitador Docente EBI — orquestador principal que delega a agentes especializados.",
    instruction=AGENT_PROMPT,
    output_schema=FacilitadorResponse,
    generate_content_config=genai_types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json"
    ),
    sub_agents=[agente_creativo, inclusion_pipeline, planificacion_pipeline],
)
