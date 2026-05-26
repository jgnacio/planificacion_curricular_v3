import os
from functools import cached_property

from dotenv import load_dotenv
from google.adk.agents import Agent, LlmAgent, SequentialAgent
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.genai import Client, types as genai_types
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
OPEN_NOTEBOOK_NOTEBOOK_ID = os.getenv("OPEN_NOTEBOOK_NOTEBOOK_ID", "notebook:4blvxvmp0bb4cud5r004")
OPEN_NOTEBOOK_MODEL = os.getenv("OPEN_NOTEBOOK_MODEL", "model:7zoi10k3sca4qvqacud4")

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
    # En prod (Agent Platform) se usa AI_STUDIO_API_KEY para no interferir con VertexAiSessionService
    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("AI_STUDIO_API_KEY")):
        raise ValueError(
            "Configurá GOOGLE_API_KEY (dev) o GOOGLE_GENAI_USE_VERTEXAI=1 (prod)."
        )

if not INTERNAL_API_URL:
    raise ValueError(
        "INTERNAL_API_URL no está configurada en el entorno. "
        "Agregala al archivo .env antes de iniciar la aplicación."
    )

# ==========================================
# LLM — Google AI Studio (bypass Vertex AI Publisher Models)
# El ADK template en Agent Platform fuerza GOOGLE_GENAI_USE_VERTEXAI=1,
# pero el proyecto no tiene acceso a Publisher Models de Vertex AI.
# Subclasear Gemini y override api_client fuerza AI Studio sin importar el env.
# ==========================================

class _GeminiAIStudio(Gemini):
    """Gemini que siempre usa Google AI Studio (AI_STUDIO_API_KEY), ignorando el backend de Vertex AI.

    Usamos AI_STUDIO_API_KEY en vez de GOOGLE_API_KEY para evitar que VertexAiSessionService
    la tome como express_mode_api_key y rompa la gestión de sesiones de Agent Platform.
    """
    @cached_property
    def api_client(self) -> Client:
        key = os.getenv("AI_STUDIO_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
        # vertexai=False fuerza Google AI Studio aunque GOOGLE_GENAI_USE_VERTEXAI=1
        return Client(api_key=key, vertexai=False)


# ==========================================
# HERRAMIENTAS — API HTTP (planificaciones y alumnos)
# ==========================================

def _internal_headers(user_id: str) -> dict:
    return {"X-Internal-Key": INTERNAL_API_KEY, "Content-Type": "application/json"}


def listar_alumnos(tool_context: ToolContext, nivel: str = "", grado: str = "", group_id: str = "") -> dict:
    """
    Lista los alumnos registrados. Filtra opcionalmente por nivel, grado y/o group_id.
    Usá esta herramienta antes de crear una planificación para conocer el grupo:
    cantidad de alumnos, sus niveles, grados y cualquier nota especial sobre ellos.
    Si ya conocés el grupo específico (porque la docente está trabajando en un grupo),
    pasá el group_id para obtener solo los alumnos de ese grupo.
    """
    user_id = tool_context.state.get("user_id", "")
    params = {"user_id": user_id}
    if nivel:
        params["nivel"] = nivel
    if grado:
        params["grado"] = grado
    if group_id:
        params["group_id"] = group_id
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
    competencias_especificas, criterios_de_logro, meta_aprendizaje, contenido, evaluaciones,
    actividades donde cada actividad tiene la misma estructura que una planificación completa con momentos).
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
            raw_results = list(ddgs.text(consulta, max_results=6))
    except Exception as e:
        return {"status": "error", "error_message": f"Error en la búsqueda DuckDuckGo: {e}"}

    if not raw_results:
        return {"status": "not_found", "message": "No se encontraron resultados para esa consulta."}

    def _fetch_one(item: dict) -> dict | None:
        url = item.get("href", "")
        title = item.get("title", "")
        snippet = item.get("body", "")
        if not url:
            return None
        try:
            with httpx.Client(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url)
                content = _extract_text(resp.text) if resp.status_code == 200 else snippet
        except Exception:
            content = snippet
        return {"titulo": title, "url": url, "contenido": content} if content else None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    fuentes = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_fetch_one, item): item for item in raw_results[:6]}
        for future in as_completed(futures):
            if len(fuentes) >= 3:
                break
            result = future.result()
            if result:
                fuentes.append(result)

    if not fuentes:
        return {"status": "not_found", "message": "No se pudo extraer contenido de los resultados."}

    return {
        "status": "success",
        "consulta": consulta,
        "total_fuentes": len(fuentes),
        "fuentes": fuentes,
    }


def create_activity(
    tool_context: ToolContext,
    title: str,
    content: str,
    project_id: str = None,
    sequence_id: str = None,
    group_id: str = None,
) -> dict:
    """
    Guarda una nueva actividad/planificación en la base de datos.
    El parámetro content debe contener el objeto JSON completo de la planificación o secuencia como string.
    Si se proveen group_id y project_id, la asocia al proyecto integrador indicado.
    Si además se provee sequence_id, la asocia a la secuencia dentro del proyecto.
    Si no se proveen IDs jerárquicos, guarda la actividad sin jerarquía.
    Usá esta herramienta después de mostrar la planificación y obtener confirmación de la docente.
    Los IDs son UUIDs (strings), no números enteros.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {
        "title": title,
        "raw_content": content,
    }

    # Elegir endpoint según contexto jerárquico
    if group_id and project_id and sequence_id:
        url = f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/sequences/{sequence_id}/activities/"
    elif group_id and project_id:
        url = f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/activities/"
    else:
        url = f"{INTERNAL_API_URL}/activities/"

    try:
        r = httpx.post(
            url,
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        activity = r.json()
        return {
            "status": "success",
            "activity_id": activity.get("id"),
            "title": activity.get("title"),
            "message": f"Actividad '{activity.get('title')}' guardada con ID {activity.get('id')}.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def create_sequence(
    tool_context: ToolContext,
    group_id: str,
    project_id: str,
    name: str,
    learning_goal: str = None,
    order: int = 0,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """
    Crea una nueva secuencia de actividades dentro de un proyecto integrador.
    Retorna el sequence_id que debés usar para asociar cada actividad con create_activity.
    Llamá esta herramienta PRIMERO al guardar una secuencia, ANTES de crear las actividades individuales.
    Los IDs son UUIDs (strings), no números enteros.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {
        "name": name,
        "project_id": project_id,
        "learning_goal": learning_goal,
        "order": order,
        "start_date": start_date,
        "end_date": end_date,
    }
    try:
        r = httpx.post(
            f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/sequences/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        seq = r.json()
        return {
            "status": "success",
            "sequence_id": seq.get("id"),
            "name": seq.get("name"),
            "message": f"Secuencia '{seq.get('name')}' creada con ID {seq.get('id')}. Ahora creá cada actividad con create_activity usando este sequence_id.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def list_activities(
    tool_context: ToolContext,
    group_id: str = None,
    project_id: str = None,
    sequence_id: str = None,
) -> dict:
    """
    Lista las actividades de un proyecto integrador o secuencia.
    Requiere group_id y project_id (UUIDs). Si además se provee sequence_id, filtra por secuencia.
    Si no tenés los IDs, usá list_groups primero para obtenerlos.
    Los IDs son UUIDs (strings), no números enteros.
    """
    user_id = tool_context.state.get("user_id", "")

    if not group_id or not project_id:
        return {
            "status": "error",
            "error_message": (
                "Se requieren group_id y project_id para listar actividades. "
                "Usá list_groups para obtener los grupos y list_projects para obtener los proyectos."
            ),
        }

    try:
        if sequence_id:
            url = f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/sequences/{sequence_id}/activities/"
        else:
            url = f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/activities/"

        r = httpx.get(
            url,
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        r.raise_for_status()
        activities = r.json()
        return {
            "status": "success",
            "total": len(activities),
            "activities": activities,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# Alias para compatibilidad con sesiones ADK existentes
def listar_planificaciones(tool_context: ToolContext) -> dict:
    """
    Lista todas las planificaciones guardadas en la base de datos, ordenadas de más reciente a más antigua.
    Usá esta herramienta cuando la docente quiera ver, modificar o eliminar planificaciones existentes.
    """
    return list_activities(tool_context)


def update_activity(
    tool_context: ToolContext,
    activity_id: str,
    title: str = None,
    content: str = None,
    project_id: str = None,
    sequence_id: str = None,
) -> dict:
    """
    Actualiza una actividad existente. Solo se modifican los campos que reciban un valor.
    Usá list_activities primero para obtener el ID correcto.
    Los IDs son UUIDs (strings), no números enteros.
    """
    user_id = tool_context.state.get("user_id", "")
    payload = {k: v for k, v in {
        "title": title,
        "raw_content": content,
        "project_id": project_id,
        "sequence_id": sequence_id,
    }.items() if v is not None}
    try:
        r = httpx.patch(
            f"{INTERNAL_API_URL}/activities/{activity_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            json=payload,
            timeout=10.0,
        )
        r.raise_for_status()
        activity = r.json()
        return {
            "status": "success",
            "activity_id": activity.get("id"),
            "title": activity.get("title"),
            "message": f"Actividad ID {activity.get('id')} actualizada correctamente.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# Alias para compatibilidad con sesiones ADK existentes
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
    # Mapeamos los campos legacy al nuevo esquema
    return update_activity(
        tool_context,
        activity_id=planificacion_id,
        title=nombre or None,
        content=chat_exportado or None,
    )


def delete_activity(tool_context: ToolContext, activity_id: str) -> dict:
    """
    Elimina permanentemente una actividad por su ID (UUID string).
    Siempre confirmá con la docente antes de eliminar. Usá list_activities para obtener el ID.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.delete(
            f"{INTERNAL_API_URL}/activities/{activity_id}",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        if r.status_code == 404:
            return {"status": "error", "error_message": f"No existe actividad con ID {activity_id}."}
        r.raise_for_status()
        return {
            "status": "success",
            "message": f"Actividad ID {activity_id} eliminada correctamente.",
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# Alias para compatibilidad con sesiones ADK existentes
def eliminar_planificacion(tool_context: ToolContext, planificacion_id: int) -> dict:
    """
    Elimina permanentemente una planificación por su ID.
    Siempre confirmá con la docente antes de eliminar. Usá listar_planificaciones para obtener el ID.
    """
    return delete_activity(tool_context, activity_id=planificacion_id)


def list_groups(tool_context: ToolContext) -> dict:
    """
    Lista los grupos del docente. Usá esta herramienta cuando la docente pregunta
    por sus grupos o quiere crear/ver actividades dentro de un grupo específico.
    Devuelve el listado con IDs que luego se usan en list_projects.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.get(
            f"{INTERNAL_API_URL}/groups/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        r.raise_for_status()
        groups = r.json()
        return {
            "status": "success",
            "total": len(groups),
            "groups": groups,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def list_projects(tool_context: ToolContext, group_id: str) -> dict:
    """
    Lista los proyectos integradores de un grupo. Usá esta herramienta cuando la docente
    quiere ver o trabajar con proyectos integradores de un grupo específico.
    Requiere el group_id (UUID string) que podés obtener con list_groups.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        r = httpx.get(
            f"{INTERNAL_API_URL}/groups/{group_id}/projects/",
            params={"user_id": user_id},
            headers=_internal_headers(user_id),
            timeout=10.0,
        )
        r.raise_for_status()
        projects = r.json()
        return {
            "status": "success",
            "total": len(projects),
            "projects": projects,
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
        espacio: Nombre de la materia o unidad curricular específica, e.g. "Lengua Española",
                 "Matemática", "Ciencias Naturales", "Historia", "Inglés".
                 NUNCA pasar el nombre del espacio ("Espacio de Comunicación", etc.) — siempre la materia.
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
            sub_materias = esp_data.get("materias", {})
            if sub_materias:
                # Merge all sub-materias: combine CEs, contenidos and criterios
                merged_ces = []
                merged_contenidos: dict = {}
                merged_criterios: dict = {}
                for mat in sub_materias.values():
                    merged_ces.extend(mat.get("competencias_especificas", []))
                    for gk, items in mat.get("contenidos", {}).items():
                        merged_contenidos.setdefault(gk, [])
                        merged_contenidos[gk].extend(items if isinstance(items, list) else [items])
                    for gk, items in mat.get("criterios", {}).items():
                        merged_criterios.setdefault(gk, [])
                        merged_criterios[gk].extend(items if isinstance(items, list) else [items])
                materia = {
                    "nombre": esp_data.get("nombre", espacio),
                    "competencias_especificas": merged_ces,
                    "contenidos": merged_contenidos,
                    "criterios": merged_criterios,
                }
            else:
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


class CurriculumMatch(BaseModel):
    espacio: str = Field(default="", description="Nombre del espacio curricular, e.g. 'Espacio de Comunicación'. Extraé de espacio_nombre en el resultado de consultar_curriculo_estructurado.")
    unidad: str = Field(default="", description="Nombre de la unidad o materia, e.g. 'Lengua Española'. Extraé del campo unidad en el resultado de consultar_curriculo_estructurado.")
    tramo: int = Field(default=0, description="Número de tramo (3 o 4). Extraé del campo tramo en el resultado de consultar_curriculo_estructurado.")
    grado: str = Field(default="", description="Grado específico, e.g. '5'. Extraé del campo grado_solicitado en el resultado de consultar_curriculo_estructurado.")
    contenido: str = Field(default="", description="Contenido del programa oficial, textual exacto. Elegí el más relevante del array contenidos devuelto por la tool.")
    ce_codigo: str = Field(default="", description="Código de la CE más relevante, e.g. 'CE9'. Extraé del campo codigo dentro de competencias_especificas.")
    ce_texto: str = Field(default="", description="Enunciado completo de la CE elegida. Extraé del campo descripcion dentro de competencias_especificas.")
    competencias_mcn: List[str] = Field(default=[], description="Competencias MCN vinculadas. Extraé del campo mcn de la CE elegida. Lista vacía si no hay.")
    criterio_de_logro: str = Field(default="", description="Criterio de logro textual exacto del programa. Elegí el más relevante del array criterios devuelto por la tool.")
    meta_aprendizaje: str = Field(default="", description="Meta de aprendizaje en plural y presente, e.g. 'Los estudiantes...' NUNCA 'Objetivo'")
    metodo_ensenanza: str = Field(default="", description="Nombre de la metodología activa que elegiste para esta planificación.")
    metodo_justificacion: str = Field(default="", description="Una oración explicando por qué esta metodología es la más adecuada para este contenido y grupo.")


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


class SecuenciaTable(BaseModel):
    espacio: str = Field(default="", description="Nombre del espacio curricular (e.g. 'Comunicación')")
    unidad_curricular: str = Field(default="", description="Nombre de la unidad curricular (e.g. 'Lengua Española')")
    competencias_generales: List[str] = Field(default=[], description="Lista de competencias generales MCN")
    competencias_especificas: List[str] = Field(default=[], description="Lista de CEs con código y enunciado")
    criterios_de_logro: List[str] = Field(default=[], description="Lista de criterios de logro")
    meta_aprendizaje: str = Field(default="", description="Meta de aprendizaje global de toda la secuencia, en presente plural")
    contenido: str = Field(default="", description="Contenido textual del programa para este espacio")
    evaluaciones: str = Field(default="", description="Criterios e instrumentos de evaluación (puede quedar vacío)")
    actividades: List[PlanificacionTable] = Field(default=[], description="Lista de actividades de la secuencia. Cada una tiene la misma estructura que una planificación completa con momentos: Inicio, Desarrollo y Cierre.")


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
    curriculum_match: CurriculumMatch = Field(
        default_factory=CurriculumMatch,
        description="Datos estructurados del match curricular. Obligatorio cuando type='curriculum_match'. Dejá todos los campos vacíos en los demás casos."
    )
    planificacion: PlanificacionTable = Field(
        default_factory=PlanificacionTable,
        description="Planificación estructurada en tabla. Obligatorio cuando type='planificacion'. Dejá todos los campos vacíos en los demás casos."
    )
    secuencia: SecuenciaTable = Field(
        default_factory=SecuenciaTable,
        description="Secuencia de actividades estructurada. Obligatorio cuando type='secuencia'. Dejá todos los campos vacíos en los demás casos."
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

**PASO 1 — Consultar fuentes**
Analizá el mensaje, inferí espacio/tramo/grado usando las tablas de arriba. Luego llamá:
1. `consultar_curriculo_estructurado(espacio, tramo, grado)` — el argumento `espacio` debe ser la **Unidad** (lado derecho del mapa de palabras clave), NO el nombre del espacio. Ejemplos: "Lengua Española", "Matemática", "Ciencias Naturales". Nunca usar "Espacio de Comunicación" ni ningún otro nombre de espacio como argumento.
Llamá esta tool EXACTAMENTE UNA VEZ. NO la volvás a llamar en pasos siguientes.

**PASO 2 — Confirmación curricular (exactamente una vez)**
Con los datos de la tool, elegí el CE y el contenido más relevante, y seleccioná la metodología activa más adecuada para el contexto.

CRÍTICO: El campo `curriculum_match` es un objeto que VOS construís extrayendo campos puntuales de los resultados de las tools. NO es el output crudo de ninguna tool. Debés mapear así:
- `espacio` ← `espacio_nombre` del resultado de `consultar_curriculo_estructurado`
- `unidad` ← `unidad` del resultado de `consultar_curriculo_estructurado`
- `tramo` ← `tramo` del resultado de `consultar_curriculo_estructurado`
- `grado` ← `grado_solicitado` del resultado de `consultar_curriculo_estructurado`
- `contenido` ← el string del contenido más relevante, dentro de `contenidos` → `5to_grado` (o el grado correspondiente)
- `ce_codigo` ← `codigo` de la CE más relevante dentro de `competencias_especificas`
- `ce_texto` ← `descripcion` de esa misma CE
- `competencias_mcn` ← `mcn` de esa misma CE (lista de strings, o lista vacía)
- `criterio_de_logro` ← el string del criterio más relevante, dentro de `criterios` → `5to_grado`
- `metodo_ensenanza` ← nombre de la metodología activa que elegiste (NO de la tool)
- `metodo_justificacion` ← una oración tuya justificando la elección

Devolvé:
- `type: "curriculum_match"`
- `curriculum_match`: objeto con los campos mapeados como se indica arriba
- `text`: mensaje cálido preguntando la temática. Por ejemplo: "Encontré el contenido ideal para esta planificación. ¿Con qué temática o contexto querés que trabajemos la actividad? Puede ser algo de la realidad de tus alumnos, una época del año, un proyecto en curso... lo que vos tengas en mente. [[Quiero cambiar algo]]"

**PASO 2b — Recibir temática**
Cuando la docente responde con la temática (cualquier texto que no sea "Quiero cambiar algo"):
- Guardá mentalmente esa temática para usarla en PASO 3 al contextualizar las actividades.
- Pasá inmediatamente a PASO 3.
Si dice "Quiero cambiar algo", preguntá qué quiere cambiar y ajustá (devolvé `type: "message"`).

**PASO 3 — Generar planificación (al recibir la temática de PASO 2b)**
Llamá `listar_alumnos()` para conocer el grupo real. Si la conversación tiene un `group_id` en el contexto (porque la docente está trabajando dentro de un grupo específico), pasalo como `listar_alumnos(group_id=<group_id>)` para obtener solo los alumnos de ese grupo.
Usá los datos curriculares y metodológicos ya obtenidos en PASO 1 — NO volvás a llamar ninguna tool de currículo.
Contextualizá todas las actividades usando la temática que indicó la docente.

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

Al recibir [[Sí, guardar]]: llamá `create_activity(title=<titulo_de_la_planificacion>, content=<json_string_completo_del_objeto_planificacion>)`. Nada más.

### Flujo B — Validar actividad existente

1. Inferí espacio/tramo/grado de la actividad.
2. FIRST llamá `consultar_curriculo_estructurado(espacio, tramo, grado)`.
3. Buscá en los CEs y contenidos devueltos el que mejor corresponde a la actividad.
4. Devolvé `type: "curriculum_match"` con el objeto `curriculum_match` poblado y en `text` un mensaje indicando si la actividad se alinea o no.

### Flujo C — Gestionar actividades

- Ver: FIRST `list_groups` → la docente elige un grupo → `list_projects` → la docente elige un proyecto → `list_activities(group_id, project_id)` → mostrá resumen con IDs.
- Si ya tenés el group_id y project_id en contexto, saltá directo a `list_activities`.
- Modificar: si no tenés el ID de la actividad, FIRST listá. Confirmá cambios antes de actualizar con `update_activity(activity_id=<uuid>)`.
- Eliminar: pedí confirmación explícita BEFORE llamar `delete_activity(activity_id=<uuid>)`.
- Todos los IDs (group_id, project_id, sequence_id, activity_id) son UUIDs string, nunca números enteros.

### Flujo D — Secuencia de actividades

Cuando la docente pida explícitamente una **secuencia de actividades**:

1. Primero, si la conversación ya tiene un `group_id` en el contexto (porque se está trabajando dentro de un grupo específico), llamá `listar_alumnos(group_id=<group_id>)` para conocer los alumnos del grupo y contextualizar mejor las actividades.
2. Llamá `consultar_curriculo_estructurado()` para obtener el contenido curricular.
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
        "titulo": "El misterio de la anécdota",
        "grupo": "Grupo de 5.to grado (Colegio 01)",
        "justificacion": "Esta actividad introduce la lectura inferencial desde un texto narrativo cercano al contexto escolar, activando conocimientos previos antes de avanzar hacia textos más complejos.",
        "metodologia": "Lectura compartida y andamiada",
        "metodologia_descripcion": "La docente guía la lectura párrafo a párrafo, modelando el proceso inferencial con preguntas. Los estudiantes responden primero en voz alta y luego de forma escrita individual.",
        "momentos": [
          {
            "momento": "Inicio",
            "duracion": "5 min",
            "meta_aprendizaje": "Activar conocimientos previos sobre el texto narrativo y sus características.",
            "actividad": "Se presenta el texto 'Un recreo inolvidable' y se indaga sobre su tipo y estructura con preguntas inferenciales: ¿Qué tipo de texto será? ¿Qué elementos del texto me muestran eso?",
            "rol_docente": "Presenta el texto, lanza las preguntas disparadoras y registra las hipótesis en el pizarrón.",
            "recursos": "Texto impreso 'Un recreo inolvidable', pizarrón y marcadores."
          },
          {
            "momento": "Desarrollo",
            "duracion": "25 min",
            "meta_aprendizaje": "Identificar información literal (quién, dónde, cuándo) a través del subrayado guiado.",
            "actividad": "Lectura individual y colectiva párrafo a párrafo, analizando la información que cada uno aporta. A medida que los estudiantes extraen información, se guía con preguntas de información literal: ¿Dónde sucedió? ¿Qué sucedió? ¿Cómo lograron resolverlo?",
            "rol_docente": "Facilita la lectura compartida, hace preguntas orientadoras y apoya a los estudiantes que requieren andamiaje.",
            "recursos": "Texto impreso, lápices de colores para subrayado."
          },
          {
            "momento": "Cierre",
            "duracion": "10 min",
            "meta_aprendizaje": "Responder preguntas de información explícita e inferencial demostrando comprensión del texto.",
            "actividad": "Los alumnos subrayan información relevante y responden una pregunta de información explícita y una de inferencia textual en sus cuadernos.",
            "rol_docente": "Circula revisando las respuestas y ofrece retroalimentación oral.",
            "recursos": "Cuadernos de los estudiantes."
          }
        ],
        "ce_codigo": "CE1",
        "ce_texto": "Narra, expone, describe, argumenta, explica, dialoga a través de la incorporación de vocabulario específico.",
        "contenido": "Las estrategias discursivas. La construcción de sentido: el vínculo entre párrafos.",
        "criterio_de_logro": "Responde correctamente preguntas de información explícita e inferencial sobre el texto leído.",
        "espacio": "Comunicación",
        "unidad": "Lengua Española",
        "tramo": 4,
        "competencias_mcn": ["Comunicación", "Pensamiento crítico"]
      }
    ]
  }
}
```

Al recibir [[Sí, guardar]]:
1. Si no tenés `group_id` y `project_id` en el contexto de la conversación, llamá `list_groups()` y luego `list_projects(group_id)` para obtenerlos. Elegí el que corresponda al contexto.
2. Llamá `create_sequence(group_id=<group_id>, project_id=<project_id>, name=<unidad_curricular>, learning_goal=<meta_aprendizaje>)`. Guardá el `sequence_id` retornado.
3. Para CADA actividad del array `actividades`, llamá `create_activity(title=<titulo>, content=<JSON de esa actividad como string>, group_id=<group_id>, project_id=<project_id>, sequence_id=<sequence_id>)`.
4. Una vez guardadas todas, confirmá cuántas actividades se crearon exitosamente.

### Tokens interactivos

`[[Opción]]` — selección única: tap envía ese texto. Usá para confirmaciones y acciones únicas.
`((Opción))` — selección múltiple: chips con botón "Confirmar". Usá cuando puede elegir varios.
No mezcles `[[]]` y `(())` en la misma respuesta.

El campo `refs` siempre queda `[]`. No incluyas tokens `[[REF:...]]` en el campo `text`.

## Boundaries

- NEVER preguntés el tema antes de consultar la base de datos.
- NEVER llamás `consultar_curriculo_estructurado` más de una vez por flujo.
- NEVER hacés más de UNA confirmación antes de pedir la temática.
- NEVER mostrás contenidos, CE o criterios que no provengan de una tool ejecutada en este turno.
- NEVER inventés URLs en los recursos web.
- NEVER devolvés `type="curriculum_match"` sin poblar el campo `curriculum_match`.
- NEVER devolvés `type="planificacion"` sin poblar el campo `planificacion`.
- NEVER devolvés `type="secuencia"` sin poblar el campo `secuencia`.
- ALWAYS devolvés `type="message"` para cualquier respuesta que no sea curriculum_match, planificacion ni secuencia.
- Preferí siempre metodologías activas; solo usá metodologías pasivas si el contexto o la docente lo justifica explícitamente.
- If no hay resultados, informá claramente y ofrecé buscar con otros parámetros.
- If el docente ya indicó el método o enfoque, usalo directamente sin preguntar.

## Examples

User: "Quiero planificar algo de lengua para 5to."
You: (llamás `consultar_curriculo_estructurado("Lengua", 4, "5")`, luego devolvés type="curriculum_match" con el objeto poblado y en text preguntás la temática)

User: "¿Qué CE cubre trabajar textos argumentativos en 6to?"
You: (FIRST `consultar_curriculo_estructurado("Lengua", 4, "6")`, buscás el CE más relevante, devolvés type="curriculum_match" con el objeto poblado)

User: (responde con temática, e.g. "con animales de la selva")
You: (llamás `listar_alumnos`, generás la planificación contextualizada con esa temática, devolvés type="planificacion" con la tabla completa)
"""

# ==========================================
# AGENTE ÚNICO
# ==========================================

root_agent = Agent(
    model=_GeminiAIStudio(model="gemini-3.5-flash"),
    name="root_agent",
    description="Facilitador Docente EBI — valida planificaciones, genera nuevas desde la normativa oficial ANEP y gestiona el guardado y actualización de planificaciones.",
    instruction=AGENT_PROMPT,
    output_schema=FacilitadorResponse,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0.1),
    tools=[
        # Herramientas de currículo y búsqueda
        consultar_curriculo_estructurado,
        buscar_en_internet,
        consultar_curriculo_oficial,
        # Alumnos
        listar_alumnos,
        # Jerarquía EBI
        list_groups,
        list_projects,
        list_activities,
        create_sequence,
        create_activity,
        update_activity,
        delete_activity,
    ],
)
