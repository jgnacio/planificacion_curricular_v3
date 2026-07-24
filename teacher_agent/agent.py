import asyncio
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

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_API_URL = "https://api.tavily.com/search"

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


async def obtener_informe_nee(tool_context: ToolContext, alumno_id: int) -> dict:
    """
    Obtiene el informe NEE más reciente de un alumno (diagnóstico y recomendaciones del especialista).
    Llamá esta herramienta cuando estés generando una planificación y algún alumno del grupo
    tenga necesidades educativas especiales registradas. Usá el diagnóstico y las recomendaciones
    para adaptar las estrategias de la planificación de forma natural y pedagógica.
    NO uses esta herramienta si el alumno no tiene informes NEE.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{INTERNAL_API_URL}/alumnos/{alumno_id}/informes",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
            )
        r.raise_for_status()
        informes = r.json()
        if not informes:
            return {"status": "sin_nee", "message": "Este alumno no tiene informes NEE registrados."}
        ultimo = informes[0]
        return {
            "status": "success",
            "alumno_id": alumno_id,
            "diagnostico": (ultimo.get("diagnostico") or "")[:1000],
            "recomendaciones_especialista": (ultimo.get("recomendaciones_especialista") or "")[:1000],
            "fecha": ultimo.get("updated_at") or ultimo.get("created_at"),
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


async def listar_alumnos(tool_context: ToolContext, nivel: str = "", grado: str = "", group_id: str = "") -> dict:
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{INTERNAL_API_URL}/alumnos/",
                params=params,
                headers=_internal_headers(user_id),
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


async def crear_planificacion(
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{INTERNAL_API_URL}/planificaciones/",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
                json=payload,
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


async def buscar_en_internet(tool_context: ToolContext, consulta: str) -> dict:
    """
    Busca información pedagógica en internet usando Tavily.
    Recupera fuentes relevantes con su contenido ya extraído y las resume.
    Usá esta herramienta para enriquecer planificaciones con ideas de actividades,
    recursos didácticos o contexto adicional sobre un contenido curricular.
    Siempre llamá primero a las herramientas de la base de datos curricular y usá esta
    para ampliar el contexto con recursos externos.
    Se puede usar UNA sola vez por turno: si ya la llamaste, seguí con lo que ya tenés
    en vez de refinar la consulta y volver a llamarla.
    La consulta debe ser lenguaje natural (ej: "actividades de ecosistemas para quinto
    grado escuela uruguaya"), NO una cadena de términos entre comillas — Tavily hace
    búsqueda híbrida (semántica + keyword) y las comillas fuerzan matching literal,
    lo que empobrece los resultados.
    """
    _TIMEOUT = 10.0
    _MAX_CHARS = 3000
    _MIN_SCORE = 0.2  # descarta resultados de relevancia marginal según el score de Tavily

    if tool_context.state.get("temp:web_search_used"):
        return {
            "status": "error",
            "error_message": "Ya se hizo una búsqueda web en este turno. No la repitas: continuá con las fuentes ya obtenidas o generá el contenido sin fuentes externas adicionales.",
        }
    tool_context.state["temp:web_search_used"] = True

    if not TAVILY_API_KEY:
        return {"status": "error", "error_message": "TAVILY_API_KEY no configurada."}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                TAVILY_API_URL,
                headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
                json={
                    "query": consulta,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
        if r.status_code == 401:
            return {"status": "error", "error_message": "TAVILY_API_KEY inválida o vencida."}
        if r.status_code in (432, 433):
            return {"status": "error", "error_message": "Se agotaron los créditos/límite del plan de Tavily."}
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"status": "error", "error_message": f"Error en la búsqueda Tavily: {e}"}

    resultados = [item for item in data.get("results", []) if item.get("score", 0) >= _MIN_SCORE]
    if not resultados:
        return {"status": "not_found", "message": "No se encontraron resultados suficientemente relevantes para esa consulta."}

    fuentes = [
        {
            "titulo": item.get("title", ""),
            "url": item.get("url", ""),
            "contenido": (item.get("content") or "")[:_MAX_CHARS],
        }
        for item in resultados
    ]

    return {
        "status": "success",
        "consulta": consulta,
        "total_fuentes": len(fuentes),
        "fuentes": fuentes,
    }


async def create_activity(
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                url,
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
                json=payload,
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


async def create_sequence(
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{INTERNAL_API_URL}/groups/{group_id}/projects/{project_id}/sequences/",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
                json=payload,
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


async def list_activities(
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

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
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
async def listar_planificaciones(tool_context: ToolContext) -> dict:
    """
    Lista todas las planificaciones guardadas en la base de datos, ordenadas de más reciente a más antigua.
    Usá esta herramienta cuando la docente quiera ver, modificar o eliminar planificaciones existentes.
    """
    return await list_activities(tool_context)


async def update_activity(
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.patch(
                f"{INTERNAL_API_URL}/activities/{activity_id}",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
                json=payload,
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
async def actualizar_planificacion(
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
    return await update_activity(
        tool_context,
        activity_id=planificacion_id,
        title=nombre or None,
        content=chat_exportado or None,
    )


async def delete_activity(tool_context: ToolContext, activity_id: str) -> dict:
    """
    Elimina permanentemente una actividad por su ID (UUID string).
    Siempre confirmá con la docente antes de eliminar. Usá list_activities para obtener el ID.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.delete(
                f"{INTERNAL_API_URL}/activities/{activity_id}",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
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
async def eliminar_planificacion(tool_context: ToolContext, planificacion_id: int) -> dict:
    """
    Elimina permanentemente una planificación por su ID.
    Siempre confirmá con la docente antes de eliminar. Usá listar_planificaciones para obtener el ID.
    """
    return await delete_activity(tool_context, activity_id=planificacion_id)


async def list_groups(tool_context: ToolContext) -> dict:
    """
    Lista los grupos del docente. Usá esta herramienta cuando la docente pregunta
    por sus grupos o quiere crear/ver actividades dentro de un grupo específico.
    Devuelve el listado con IDs que luego se usan en list_projects.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{INTERNAL_API_URL}/groups/",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
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


async def list_projects(tool_context: ToolContext, group_id: str) -> dict:
    """
    Lista los proyectos integradores de un grupo. Usá esta herramienta cuando la docente
    quiere ver o trabajar con proyectos integradores de un grupo específico.
    Requiere el group_id (UUID string) que podés obtener con list_groups.
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{INTERNAL_API_URL}/groups/{group_id}/projects/",
                params={"user_id": user_id},
                headers=_internal_headers(user_id),
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


async def consultar_curriculo_oficial(tool_context: ToolContext, pregunta: str) -> dict:
    """
    Consulta los PDFs oficiales del currículo EBI/ANEP (1er y 2do Ciclo) indexados en
    Vertex AI Search. Devuelve orientaciones pedagógicas, metodologías sugeridas y
    contexto del programa que complementan los datos estructurados de la base curricular.

    Usá esta tool DESPUÉS de consultar la herramienta de currículo estructurado, para
    enriquecer la planificación con las orientaciones pedagógicas reales del programa
    oficial. Ideal para preguntas como:
    - "¿Qué metodologías sugiere el programa para enseñar X?"
    - "¿Cómo se aborda Y en el perfil de Tramo 4?"
    - "¿Qué dice el currículo sobre la evaluación de Z?"

    Cuando cites la respuesta, mencioná siempre la "página N" y el fragmento textual
    (excerpt) de cada fuente devuelta en `fuentes` — nunca afirmes algo del currículo
    oficial sin esa cita.

    Args:
        pregunta: Pregunta pedagógica sobre el currículo (en español, clara y específica)

    Returns:
        dict con 'status' ('success', 'not_found' o 'error'), 'respuesta' (resumen) y
        'fuentes' (lista de {titulo, pagina, extracto, doc_id, ciclo})
    """
    user_id = tool_context.state.get("user_id", "")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{INTERNAL_API_URL}/internal/curriculo/search",
                headers=_internal_headers(user_id),
                json={"consulta": pregunta},
            )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return {"status": "error", "error_message": f"Currículo oficial no accesible: {str(e)}"}

    sources = data.get("sources") or []
    if not sources:
        return {
            "status": "not_found",
            "message": data.get("answer") or "No se encontraron resultados en el currículo oficial para esa consulta.",
        }

    return {
        "status": "success",
        "respuesta": data.get("answer", ""),
        "fuentes": [
            {
                "titulo": s.get("title", ""),
                "pagina": s.get("pageNumber"),
                "extracto": s.get("excerpt", ""),
                "doc_id": s.get("docId", ""),
                "ciclo": s.get("ciclo", ""),
            }
            for s in sources
        ],
    }


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
        tramo: Número de tramo — 1 (Educación Inicial), 2 (1° y 2° grado), 3 (3° y 4° grado), 4 (5° y 6° grado)
        grado: Grado específico — Tramo 1: "3_anios"/"4_anios"/"5_anios"; Tramo 2: "1"/"2"; Tramo 3: "3"/"4"; Tramo 4: "5"/"6" (o "todos" para todo el tramo)

    Returns:
        dict con 'status', 'espacio', 'tramo', 'competencias_especificas',
        'contenidos' (para el grado pedido) y 'criterios' (para el grado pedido)
    """
    print(f"\n[TOOL consultar_curriculo_estructurado] espacio={espacio!r} tramo={tramo} grado={grado!r}")
    try:
        data = _load_curriculum()
        tramo_key = f"tramo_{tramo}"
        if tramo_key not in data.get("tramos", {}):
            return {"status": "error", "error_message": f"Tramo {tramo} no existe. Usá 1, 2, 3 o 4."}

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
                # Sin esto se apilan las CEs de todas las materias del espacio y el
                # modelo elige a ciegas: cada CE queda etiquetada con su materia y se
                # deduplica por (codigo, texto), porque varias materias repiten CEs.
                seen_ces: set[tuple[str, str]] = set()
                merged_contenidos: dict = {}
                merged_criterios: dict = {}
                for mat in sub_materias.values():
                    mat_nombre = mat.get("nombre", "")
                    for ce in mat.get("competencias_especificas", []):
                        clave = (ce.get("codigo", ""), ce.get("texto", ""))
                        if clave in seen_ces:
                            continue
                        seen_ces.add(clave)
                        merged_ces.append({**ce, "materia": mat_nombre})
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
            "1": "1er_grado", "2": "2do_grado",
            "3": "3er_grado", "4": "4to_grado",
            "5": "5to_grado", "6": "6to_grado",
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
    doc_id: str = Field(description="Copiá TEXTUAL el campo `doc_id` de la fuente devuelta por consultar_curriculo_oficial. Nunca lo inventes.")
    page: int = Field(description="Copiá el campo `pagina` de esa misma fuente.")
    ciclo: str = Field(default="", description="Copiá el campo `ciclo` de esa misma fuente, e.g. '2do Ciclo'.")
    label: str = Field(description="Etiqueta del badge: ciclo y página, e.g. '2do Ciclo — p.9'.")
    excerpt: str = Field(default="", description="Copiá TEXTUAL el campo `extracto` de esa misma fuente. El visor lo usa para resaltar el pasaje dentro de la página.")


class CurriculumMatch(BaseModel):
    espacio: str = Field(default="", description="Nombre del espacio curricular, e.g. 'Espacio de Comunicación'. Extraé de espacio_nombre en el resultado de consultar_curriculo_estructurado.")
    unidad: str = Field(default="", description="Nombre de la unidad o materia, e.g. 'Lengua Española'. Extraé del campo unidad en el resultado de consultar_curriculo_estructurado.")
    tramo: int = Field(default=0, description="Número de tramo (3 o 4). Extraé del campo tramo en el resultado de consultar_curriculo_estructurado.")
    grado: str = Field(default="", description="Grado específico, e.g. '5'. Extraé del campo grado_solicitado en el resultado de consultar_curriculo_estructurado.")
    contenido: str = Field(default="", description="Contenido del programa oficial, textual exacto. Elegí el más relevante del array contenidos devuelto por la tool.")
    ce_codigo: str = Field(default="", description="Código de la CE más relevante, e.g. 'CE9'. Extraé del campo codigo dentro de competencias_especificas.")
    ce_texto: str = Field(default="", description="Enunciado completo de la CE elegida, copiado TEXTUAL del campo `texto` dentro de competencias_especificas. Nunca lo parafrasees ni lo resumas.")
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
    refs: List["PdfRef"] = Field(default=[], description="Citas al currículo oficial que respaldan esta planificación. Una por cada fuente de consultar_curriculo_oficial que hayas usado. [] si no consultaste el currículo oficial.")


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
    refs: List["PdfRef"] = Field(default=[], description="Citas al currículo oficial que respaldan la secuencia completa. Una por cada fuente de consultar_curriculo_oficial que hayas usado. [] si no consultaste el currículo oficial.")


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

Grado → Tramo:
- Educación Inicial (3, 4, 5 años) = Tramo 1
- 1° y 2° grado = Tramo 2
- 3° y 4° grado = Tramo 3
- 5° y 6° grado = Tramo 4

Argumentos de grado para `consultar_curriculo_estructurado`:
- Tramo 1: "3_anios", "4_anios", "5_anios" (o "todos" para ver todo el tramo)
- Tramo 2: "1", "2" (o "todos")
- Tramo 3: "3", "4" (o "todos")
- Tramo 4: "5", "6" (o "todos")

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
2. `consultar_curriculo_oficial(pregunta)` — UNA sola vez. Devuelve las páginas del PDF oficial que respaldan la planificación. Guardá las `fuentes` que uses: en PASO 3 se convierten en `refs`.
   Pasá 2 a 4 palabras del CONTENIDO, no una pregunta. La búsqueda es sobre los PDFs del programa: cada término extra restringe el resultado, y las palabras que no aparecen en el texto (grado, ciclo, "orientaciones", "programa") lo vacían.
   Bien: `"relaciones tróficas ecosistemas"`, `"fracciones equivalentes"`, `"lectura inferencial"`.
   Mal: `"¿Qué orientaciones da el programa para enseñar fracciones en quinto grado?"`.

**PASO 2 — Confirmación curricular (exactamente una vez)**
Con los datos de la tool, elegí el CE y el contenido más relevante, y seleccioná la metodología activa más adecuada para el contexto.

CRÍTICO: El campo `curriculum_match` es un objeto que VOS construís extrayendo campos puntuales de los resultados de las tools. NO es el output crudo de ninguna tool. Debés mapear así:
- `espacio` ← `espacio_nombre` del resultado de `consultar_curriculo_estructurado`
- `unidad` ← `unidad` del resultado de `consultar_curriculo_estructurado`
- `tramo` ← `tramo` del resultado de `consultar_curriculo_estructurado`
- `grado` ← `grado_solicitado` del resultado de `consultar_curriculo_estructurado`
- `contenido` ← el string del contenido más relevante, dentro de `contenidos` → `5to_grado` (o el grado correspondiente)
- `ce_codigo` ← `codigo` de la CE más relevante dentro de `competencias_especificas`
- `ce_texto` ← `texto` de esa misma CE, copiado TEXTUAL y COMPLETO. El campo se llama `texto` (no `descripcion`). Nunca lo reescribas, resumas ni completes de memoria: si no está en el resultado de la tool, no lo pongas.
- `competencias_mcn` ← `mcn` de esa misma CE (lista de strings, o lista vacía)

Para elegir la CE más relevante: cada CE trae `codigo`, `texto` y a veces `materia`. Cuando el espacio agrupa varias materias, las CEs vienen etiquetadas con `materia` — elegí una cuya `materia` coincida con la `unidad` que estás planificando. Las CEs son del tramo completo, no del grado: aseguráte de que la que elegís se corresponda con el `contenido` y el `criterio_de_logro` del grado solicitado.
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

Luego, para CADA alumno del grupo, revisá si el objeto alumno tiene informes NEE asociados. Si `listar_alumnos` devuelve alumnos con campo `tiene_nee: true` o si la docente mencionó que hay alumnos con necesidades especiales, llamá `obtener_informe_nee(alumno_id=<id>)` para cada uno. Incorporá el diagnóstico y las recomendaciones del especialista en la planificación de forma natural: adaptá las consignas, los materiales, los tiempos y el rol docente según las indicaciones del especialista. No menciones explícitamente el diagnóstico en el texto de la planificación — simplemente reflejá las adaptaciones como parte del diseño pedagógico.

Usá los datos curriculares y metodológicos ya obtenidos en PASO 1 — NO volvás a llamar ninguna tool de currículo.
Contextualizá todas las actividades usando la temática que indicó la docente.
Llená `planificacion.refs` con las fuentes que devolvió `consultar_curriculo_oficial` en PASO 1 (ver "Citas al currículo oficial").

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
  "competencias_mcn": ["Comunicación", "Metacognitiva"],
  "refs": [
    {
      "doc_id": "compilacion-programas-2do-ciclo",
      "page": 9,
      "ciclo": "2do Ciclo",
      "label": "2do Ciclo — p.9",
      "excerpt": "Fragmento textual del programa devuelto por la tool"
    }
  ]
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

1. Primero, si la conversación ya tiene un `group_id` en el contexto (porque se está trabajando dentro de un grupo específico), llamá `listar_alumnos(group_id=<group_id>)` para conocer los alumnos del grupo y contextualizar mejor las actividades. Si algún alumno tiene NEE registradas, llamá `obtener_informe_nee(alumno_id=<id>)` para incorporar las adaptaciones a lo largo de toda la secuencia.
2. Llamá `consultar_curriculo_estructurado()` para obtener el contenido curricular.
3. Llamá `consultar_curriculo_oficial()` UNA vez, con 2 a 4 palabras del contenido (no una pregunta; ver PASO 1 del Flujo A). Sus `fuentes` son las citas de la secuencia.
4. Generá entre 3 y 6 actividades numeradas con plan detallado en bullets.
5. Respondé con `type: "secuencia"` y el objeto `secuencia` completo, con `secuencia.refs` poblado a partir de las fuentes del paso 3.

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
        "competencias_mcn": ["Comunicación", "Pensamiento crítico"],
        "refs": [
          {
            "doc_id": "compilacion-programas-2do-ciclo",
            "page": 41,
            "ciclo": "2do Ciclo",
            "label": "2do Ciclo — p.41",
            "excerpt": "Fragmento textual del programa que respalda esta actividad"
          }
        ]
      }
    ],
    "refs": [
      {
        "doc_id": "compilacion-programas-2do-ciclo",
        "page": 9,
        "ciclo": "2do Ciclo",
        "label": "2do Ciclo — p.9",
        "excerpt": "Fragmento textual del programa que respalda la secuencia"
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

### Citas al currículo oficial (`refs`)

Cada vez que uses `consultar_curriculo_oficial`, TODA fuente devuelta en `fuentes` que hayas
aprovechado se convierte en una entrada de `refs`. Mapeá campo a campo, sin inventar nada:

- `doc_id` ← `doc_id` de la fuente (textual)
- `page` ← `pagina` de la fuente
- `ciclo` ← `ciclo` de la fuente
- `excerpt` ← `extracto` de la fuente (textual, sin recortar)
- `label` ← el ciclo, un guion largo y la página abreviada, e.g. `2do Ciclo — p.9`. Si `ciclo` viene vacío, usá el `titulo` en su lugar.

NOTA: no escribas nombres de variable entre llaves en tus respuestas de texto; las llaves con un identificador adentro se interpretan como estado de sesión.

Dónde va `refs` según el tipo de respuesta:
- `type='planificacion'` → dentro de `planificacion.refs`
- `type='secuencia'` → dentro de `secuencia.refs`
- `type='message'` → en el `refs` de primer nivel

Reglas:
- Si no llamaste a `consultar_curriculo_oficial`, `refs` queda `[]`. Nunca fabriques una cita.
- Una fuente sin `doc_id` o sin `pagina` NO se incluye: sin eso el visor no puede abrir el PDF.
- No repitas la misma combinación `doc_id` + `page`.
- No incluyas tokens `[[REF:...]]` en el campo `text`: las citas viajan sólo por `refs`.

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
    model=_GeminiAIStudio(model="gemini-3.5-flash-lite"),
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
        # Alumnos y NEE
        listar_alumnos,
        obtener_informe_nee,
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
